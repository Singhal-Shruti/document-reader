"""Agent and retriever tool for asking questions against ingested documents."""

from __future__ import annotations

from langchain.agents import create_agent
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.messages import AIMessage
from langchain_core.tools import BaseTool, tool
from langchain_openai import ChatOpenAI


def format_document(document: Document, index: int) -> str:
    metadata = document.metadata
    source = metadata.get("source", "unknown source")
    title = metadata.get("title")
    source_type = metadata.get("source_type", "doc")
    label = f"{title} ({source})" if title else source
    return f"[{index}] [{source_type}] {label}\n{document.page_content}"


def create_document_search_tool(
    vector_store: Chroma,
    *,
    search_results: int,
) -> BaseTool:
    """Create a tool the agent can call to search ingested documents."""

    @tool
    def search_ingested_documents(query: str) -> str:
        """Search the ingested documents (web pages and Confluence) for context."""
        documents = vector_store.similarity_search(query, k=search_results)

        if not documents:
            return "No relevant ingested documents were found."

        return "\n\n".join(
            format_document(document, index)
            for index, document in enumerate(documents, start=1)
        )

    return search_ingested_documents


def build_agent(llm: ChatOpenAI, document_search_tool: BaseTool):
    system_prompt = (
        "You answer questions using ingested documents from public websites "
        "and Confluence pages. Always call the search_ingested_documents tool "
        "before answering. Base your answer on the tool results. If the tool "
        "does not return relevant context, say that you could not find the "
        "answer in the ingested documents. Cite source URLs when available."
    )
    return create_agent(
        model=llm,
        tools=[document_search_tool],
        system_prompt=system_prompt,
    )


def extract_final_answer(agent_response: dict) -> str:
    messages = agent_response.get("messages", [])
    for message in reversed(messages):
        if isinstance(message, AIMessage) and message.content:
            return str(message.content)
    return str(agent_response)
