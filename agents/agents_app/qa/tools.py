"""Tools the QA agent can call.

Right now there's a single tool that runs a similarity search against the
Chroma collection populated by the ingestion commands. The tool returns a
formatted, citation-friendly string that the agent can ground its answer on.
"""

from __future__ import annotations

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.tools import BaseTool, tool


def _format_document(document: Document, index: int) -> str:
    """Render one retrieved chunk with its citation header."""
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
    """Create a tool the agent can call to search ingested documents.

    Args:
        vector_store: Chroma collection populated by the ingestion commands.
        search_results: Top-k chunks to return per call.
    """

    @tool
    def search_ingested_documents(query: str) -> str:
        """Search ingested documents (Confluence pages, Swagger endpoints, ...).

        Use this to find evidence before answering any user question.
        Pass a focused natural-language query that captures what the user
        is asking about.
        """
        documents = vector_store.similarity_search(query, k=search_results)

        if not documents:
            return "No relevant ingested documents were found."

        return "\n\n".join(
            _format_document(document, index)
            for index, document in enumerate(documents, start=1)
        )

    return search_ingested_documents
