from langchain_core.tools import StructuredTool, ToolException
import requests
from mcp import McpError
from pydantic import BaseModel, Field


def wrap_mcp_authenticate_tool(tool: StructuredTool) -> StructuredTool:
    """Wrap the tool coroutine to handle `interaction_required` MCP error.

    Tried to obtain the URL from the error, which the LLM can use to render a link."""

    old_coroutine = tool.coroutine

    async def wrapped_mcp_coroutine(**kwargs):
        try:
            return await old_coroutine(**kwargs)
        except McpError as e:
            if e.error.code == -32003 and e.error.data:
                raise ToolException(
                    f"Requires interaction ({e.error.message}): {e.error.data['url']}"
                )
            raise e

    tool.coroutine = wrapped_mcp_coroutine
    return tool


def create_rag_tool(rag_url: str, collection: str):
    """Create a RAG tool for a specific collection.

    Args:
        rag_url: The base URL for the RAG API server
        collection: The name of the collection to query

    Returns:
        A structured tool that can be used to query the RAG collection
    """
    if rag_url.endswith("/"):
        rag_url = rag_url[:-1]

    collection_endpoint = f"{rag_url}/collections/{collection}"
    try:
        response = requests.get(collection_endpoint)
        response.raise_for_status()
        collection_data = response.json()

        collection_name = collection_data.get("name", collection)

        raw_description = collection_data.get("metadata", {}).get("description")

        if not raw_description:
            collection_description = "Search your collection of documents for results semantically similar to the input query"
        else:
            collection_description = f"Search your collection of documents for results semantically similar to the input query. Collection description: {raw_description}"

        def get_documents(query: str) -> str:
            """Search for documents in the collection based on the query.

            Args:
                query: The search query string

            Returns:
                A formatted string containing all documents in XML-like format
            """
            search_endpoint = f"{rag_url}/collections/{collection}/documents/search"
            payload = {"query": query, "limit": 10}

            try:
                search_response = requests.post(search_endpoint, json=payload)
                search_response.raise_for_status()
                documents = search_response.json()

                formatted_docs = "<all-documents>\n"

                for doc in documents:
                    doc_id = doc.get("id", "unknown")
                    content = doc.get("content", "")
                    formatted_docs += (
                        f'  <document id="{doc_id}">\n    {content}\n  </document>\n'
                    )

                formatted_docs += "</all-documents>"
                return formatted_docs
            except Exception as e:
                return f"<all-documents>\n  <error>{str(e)}</error>\n</all-documents>"

        class SearchArgs(BaseModel):
            query: str = Field(
                description="The search query to find relevant documents"
            )

        return StructuredTool.from_function(
            func=get_documents,
            name=collection_name,
            description=collection_description,
            args_schema=SearchArgs,
            return_direct=True,
        )

    except Exception as e:
        raise Exception(f"Failed to create RAG tool: {str(e)}")
