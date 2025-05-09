from langchain_core.runnables import RunnableConfig
from typing import Optional, List
from pydantic import BaseModel, Field
from langgraph.prebuilt import create_react_agent
from tools_agent.utils.tools import create_rag_tool
from langchain.chat_models import init_chat_model
from langchain_mcp_adapters.client import MultiServerMCPClient
from tools_agent.utils.token import fetch_tokens

class RagConfig(BaseModel):
    rag_url: Optional[str] = None
    """The URL of the rag server"""
    collection: Optional[str] = None
    """The collection to use for rag"""

class MCPConfig(BaseModel):
    url: Optional[str] = Field(
        default=None,
        optional=True,
    )
    """The URL of the MCP server"""
    tools: Optional[List[str]] = Field(
        default=None,
        optional=True,
    )
    """The tools to make available to the LLM"""

class GraphConfigPydantic(BaseModel):
    model_name: Optional[str] = Field(
        default="anthropic:claude-3-7-sonnet-latest",
        metadata={
            "x_lg_ui_config": {
                "type": "select",
                "default": "anthropic:claude-3-7-sonnet-latest",
                "description": "The model to use in all generations",
                "options": [
                    {
                        "label": "Claude 3.7 Sonnet",
                        "value": "anthropic:claude-3-7-sonnet-latest",
                    },
                    {
                        "label": "Claude 3.5 Sonnet",
                        "value": "anthropic:claude-3-5-sonnet-latest",
                    },
                    {"label": "GPT 4o", "value": "openai:gpt-4o"},
                    {"label": "GPT 4o mini", "value": "openai:gpt-4o-mini"},
                    {"label": "GPT 4.1", "value": "openai:gpt-4.1"},
                ],
            }
        }
    )
    temperature: Optional[float] = Field(
        default=0.7,
        metadata={
            "x_lg_ui_config": {
                "type": "slider",
                "default": 0.7,
                "min": 0,
                "max": 2,
                "step": 0.1,
                "description": "Controls randomness (0 = deterministic, 2 = creative)",
            }
        }
    )
    max_tokens: Optional[int] = Field(
        default=4000,
        metadata={
            "x_lg_ui_config": {
                "type": "number",
                "default": 4000,
                "min": 1,
                "description": "The maximum number of tokens to generate",
            }
        }
    )
    system_prompt: Optional[str] = Field(
        default=None,
        metadata={
            "x_lg_ui_config": {
                "type": "textarea",
                "placeholder": "Enter a system prompt...",
                "description": "The system prompt to use in all generations",
            }
        }
    )
    mcp_config: Optional[MCPConfig] = Field(
        default=None,
        optional=True,
        metadata={
            "x_lg_ui_config": {
                "type": "mcp",
                # Here is where you would set the default tools.
                # "default": {
                #     "tools": ["Math_Divide", "Math_Mod"]
                # }
            }
        }
    )
    rag: Optional[RagConfig] = Field(
        default=None,
        optional=True,
        metadata={
            "x_lg_ui_config": {
                "type": "rag",
                # Here is where you would set the default collection.
                # "default": {
                #     "collections": ["python", "langgraph docs"]
                # }
            }
        }
    )


async def graph2(config: RunnableConfig):
    cfg = GraphConfigPydantic(**config.get("configurable", {}))
    tools = []
    
    # Add RAG tool if configured
    if cfg.rag and cfg.rag.rag_url and cfg.rag.collection:
        rag_tool = create_rag_tool(cfg.rag.rag_url, cfg.rag.collection)
        print("\n\n\n\nFOUND RAG TOOL!!!\n\n\n\n")
        tools.append(rag_tool)
    
    # Add MCP tools if configured
    if cfg.mcp_config and cfg.mcp_config.url:
        mcp_tokens = fetch_tokens(config)
        if not mcp_tokens:
            print("Failed to fetch MCP tokens")
            return
        # Create MCP client and connect to the server
        async with MultiServerMCPClient() as mcp_client:
            # Connect to the server using SSE transport
            await mcp_client.connect_to_server(
                "mcp_server",
                transport="streamable_http",
                url=cfg.mcp_config.url,
                headers={
                    "Authorization": f"Bearer {mcp_tokens['access_token']}"
                }
            )
            
            # Get all tools from the server
            all_mcp_tools = mcp_client.get_tools()
            
            # Filter tools based on the config
            if cfg.mcp_config.tools:
                # Only include tools specified in the config
                filtered_tools = []
                for tool in all_mcp_tools:
                    if tool.name in cfg.mcp_config.tools:
                        filtered_tools.append(tool)
                tools.extend(filtered_tools)
            else:
                # If no specific tools are specified, include all tools
                tools.extend(all_mcp_tools)
    
    # Initialize the model
    model = init_chat_model(cfg.model_name, temperature=cfg.temperature, max_tokens=cfg.max_tokens)
    
    print("RETURNING AGENT")
    return create_react_agent(
        prompt=cfg.system_prompt,
        model=model,
        tools=tools,
        config_schema=GraphConfigPydantic,
    )

graph = create_react_agent(
    model="openai:gpt-4o",
    tools=[],
    config_schema=GraphConfigPydantic,
)