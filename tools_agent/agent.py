from langchain_core.runnables import RunnableConfig
from typing import Optional, List
from pydantic import BaseModel, Field
from langgraph.prebuilt import create_react_agent
from tools_agent.utils.tools import create_rag_tool
from langchain.chat_models import init_chat_model
from tools_agent.utils.token import fetch_tokens
from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession
from langchain_core.tools import StructuredTool
from tools_agent.utils.tools import (
    wrap_mcp_authenticate_tool,
    create_langchain_mcp_tool,
)


UNEDITABLE_SYSTEM_PROMPT = "\nIf the tool throws an error requiring authentication, provide the user with a Markdown link to the authentication page and prompt them to authenticate."

DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful assistant that has access to a variety of tools."
)


class RagConfig(BaseModel):
    rag_url: Optional[str] = None
    """The URL of the rag server"""
    collections: Optional[List[str]] = None
    """The collections to use for rag"""


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
    auth_required: Optional[bool] = Field(
        default=False,
        optional=True,
    )
    """Whether the MCP server requires authentication"""


class GraphConfigPydantic(BaseModel):
    model_name: Optional[str] = Field(
        default="openai:gpt-4o",
        metadata={
            "x_oap_ui_config": {
                "type": "select",
                "default": "openai:gpt-4o",
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
                    {
                        "label": "DeepSeek Coder",
                        "value": "deepseek:deepseek-coder",
                    },
                    {
                        "label": "DeepSeek Chat",
                        "value": "deepseek:deepseek-chat",
                    },
                    {
                        "label": "DeepSeek Coder Instruct",
                        "value": "deepseek:deepseek-coder-instruct",
                    },
                    {
                        "label": "Morpheus",
                        "value": "zhipu:glm-4",
                    },
                ],
            }
        },
    )
    temperature: Optional[float] = Field(
        default=0.7,
        metadata={
            "x_oap_ui_config": {
                "type": "slider",
                "default": 0.7,
                "min": 0,
                "max": 2,
                "step": 0.1,
                "description": "Controls randomness (0 = deterministic, 2 = creative)",
            }
        },
    )
    system_prompt: Optional[str] = Field(
        default=DEFAULT_SYSTEM_PROMPT,
        metadata={
            "x_oap_ui_config": {
                "type": "textarea",
                "placeholder": "Enter a system prompt...",
                "description": f"The system prompt to use in all generations. The following prompt will always be included at the end of the system prompt:\n---{UNEDITABLE_SYSTEM_PROMPT}\n---",
                "default": DEFAULT_SYSTEM_PROMPT,
            }
        },
    )
    mcp_config: Optional[MCPConfig] = Field(
        default=None,
        optional=True,
        metadata={
            "x_oap_ui_config": {
                "type": "mcp",
                # Here is where you would set the default tools.
                # "default": {
                #     "tools": ["Math_Divide", "Math_Mod"]
                # }
            }
        },
    )
    rag: Optional[RagConfig] = Field(
        default=None,
        optional=True,
        metadata={
            "x_oap_ui_config": {
                "type": "rag",
                # Here is where you would set the default collection. Use collection IDs
                # "default": {
                #     "collections": [
                #         "fd4fac19-886c-4ac8-8a59-fff37d2b847f",
                #         "659abb76-fdeb-428a-ac8f-03b111183e25",
                #     ]
                # },
            }
        },
    )


async def graph(config: RunnableConfig):
    cfg = GraphConfigPydantic(**config.get("configurable", {}))
    tools = []

    supabase_token = config.get("configurable", {}).get("x-supabase-access-token")
    if cfg.rag and cfg.rag.rag_url and cfg.rag.collections and supabase_token:
        for collection in cfg.rag.collections:
            rag_tool = await create_rag_tool(
                cfg.rag.rag_url, collection, supabase_token
            )
            tools.append(rag_tool)

    if cfg.mcp_config and cfg.mcp_config.auth_required:
        mcp_tokens = await fetch_tokens(config)
    else:
        mcp_tokens = None
    if (
        cfg.mcp_config
        and cfg.mcp_config.url
        and cfg.mcp_config.tools
        and (mcp_tokens or not cfg.mcp_config.auth_required)
    ):
        server_url = cfg.mcp_config.url.rstrip("/") + "/mcp"

        tool_names_to_find = set(cfg.mcp_config.tools)
        fetched_mcp_tools_list: list[StructuredTool] = []
        names_of_tools_added = set()

        # If the tokens are not None, then we need to add the authorization header. otherwise make headers None
        headers = (
            mcp_tokens is not None
            and {"Authorization": f"Bearer {mcp_tokens['access_token']}"}
            or None
        )
        try:
            async with streamablehttp_client(server_url, headers=headers) as streams:
                read_stream, write_stream, _ = streams
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()

                    page_cursor = None

                    while True:
                        tool_list_page = await session.list_tools(cursor=page_cursor)

                        if not tool_list_page or not tool_list_page.tools:
                            break

                        for mcp_tool in tool_list_page.tools:
                            if not tool_names_to_find or (
                                mcp_tool.name in tool_names_to_find
                                and mcp_tool.name not in names_of_tools_added
                            ):
                                langchain_tool = create_langchain_mcp_tool(
                                    mcp_tool, mcp_server_url=server_url, headers=headers
                                )
                                fetched_mcp_tools_list.append(
                                    wrap_mcp_authenticate_tool(langchain_tool)
                                )
                                if tool_names_to_find:
                                    names_of_tools_added.add(mcp_tool.name)

                        page_cursor = tool_list_page.nextCursor

                        if not page_cursor:
                            break
                        if tool_names_to_find and len(names_of_tools_added) == len(
                            tool_names_to_find
                        ):
                            break

                    tools.extend(fetched_mcp_tools_list)
        except Exception as e:
            print(f"Failed to fetch MCP tools: {e}")
            pass

    model = init_chat_model(
        cfg.model_name,
        temperature=cfg.temperature,
        max_tokens=4000,
    )

    return create_react_agent(
        prompt=cfg.system_prompt + UNEDITABLE_SYSTEM_PROMPT,
        model=model,
        tools=tools,
        config_schema=GraphConfigPydantic,
    )
