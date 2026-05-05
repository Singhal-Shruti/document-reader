"""Agent and retriever tool for asking questions against ingested documents."""

from __future__ import annotations

from langchain.agents import create_agent
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.messages import AIMessage
from langchain_core.tools import BaseTool, tool
from langchain_openai import ChatOpenAI


def format_document(document: Document, index: int) -> str:
    source = document.metadata.get("source", "unknown source")
    title = document.metadata.get("title")
    heading = f"[{index}] {title} ({source})" if title else f"[{index}] {source}"
    return f"{heading}\n{document.page_content}"


def create_document_search_tool(
    vector_store: Chroma,
    *,
    search_results: int,
) -> BaseTool:
    """Create a tool the agent can call to search ingested documents."""

    @tool
    def search_ingested_documents(query: str) -> str:
        """Search the ingested website documents for information relevant to a question."""
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
        "You answer questions using the ingested website documents. "
        "Always call the search_ingested_documents tool before answering. "
        "Base your answer on the tool results. If the tool does not return "
        "relevant context, say that you could not find the answer in the "
        "ingested documents. Cite source URLs when they are available."
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
