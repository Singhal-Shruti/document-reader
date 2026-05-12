"""Per-source retrieval tools used by the journey agent.

The journey workflow needs to keep "what is this journey" (gathered from
Confluence/Jira/GitHub) cleanly separated from "which APIs implement it"
(from the Swagger store). Modelling each source as its own tool lets the
agent — and any downstream auditing — see which stores actually
contributed to the answer.
"""

from __future__ import annotations

from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.tools import BaseTool, tool
from langchain_openai import OpenAIEmbeddings

from journey_app.clients import build_vector_store_for_source
from journey_app.config import (
    SOURCE_CONFLUENCE,
    SOURCE_GITHUB,
    SOURCE_JIRA,
    SOURCE_SWAGGER,
)


def _format_context_chunk(document: Document, index: int) -> str:
    metadata = document.metadata
    source = metadata.get("source", "unknown")
    title = metadata.get("title") or source
    source_type = metadata.get("source_type", "doc")
    return f"[{index}] [{source_type}] {title}\nsource: {source}\n{document.page_content}"


def _format_swagger_chunk(document: Document, index: int) -> str:
    metadata = document.metadata
    method = metadata.get("http_method", "")
    route = metadata.get("route", "")
    spec_title = metadata.get("spec_title", "")
    spec_version = metadata.get("spec_version", "")
    source = metadata.get("source", "unknown")
    api_header = (
        f"{method} {route}".strip()
        or metadata.get("title")
        or "API endpoint"
    )
    return (
        f"[{index}] {api_header}\n"
        f"spec: {spec_title} v{spec_version}\n"
        f"source: {source}\n"
        f"{document.page_content}"
    )


def _make_context_search_tool(
    *,
    source: str,
    tool_name: str,
    description: str,
    vector_store: Chroma,
    search_results: int,
) -> BaseTool:
    """Build a tool that runs similarity search against ONE source store."""

    @tool(tool_name, description=description)
    def _search(query: str) -> str:
        documents = vector_store.similarity_search(query, k=search_results)
        if not documents:
            return f"No relevant {source} documents were found."
        return "\n\n".join(
            _format_context_chunk(doc, i)
            for i, doc in enumerate(documents, start=1)
        )

    return _search


def _make_swagger_search_tool(
    *, vector_store: Chroma, search_results: int
) -> BaseTool:
    """Tool dedicated to the Swagger store; renders endpoints API-first."""

    @tool(
        "find_apis_for_capability",
        description=(
            "Search the Swagger / OpenAPI vector store for the API endpoints "
            "that implement a given capability or operation. Input should be "
            "a concise capability name or natural-language description (e.g. "
            "'create a new pet', 'authenticate user', 'fetch order by id'). "
            "Returns one block per matching endpoint with its HTTP method, "
            "route, spec title, and source URL."
        ),
    )
    def _search_swagger(query: str) -> str:
        documents = vector_store.similarity_search(query, k=search_results)
        if not documents:
            return "No matching APIs were found in the Swagger store."
        return "\n\n".join(
            _format_swagger_chunk(doc, i)
            for i, doc in enumerate(documents, start=1)
        )

    return _search_swagger


CONTEXT_TOOL_SPECS: tuple[tuple[str, str, str], ...] = (
    (
        SOURCE_CONFLUENCE,
        "search_confluence_context",
        "Search Confluence pages for context about the user's feature/journey. "
        "Returns chunks of the matching pages with their source URL and title. "
        "Use for product specs, runbooks, design docs, etc.",
    ),
    (
        SOURCE_JIRA,
        "search_jira_context",
        "Search Jira issues/epics for context about the user's feature/journey. "
        "Returns issue summaries and descriptions with their source URL. "
        "Use for requirements, acceptance criteria, bug history.",
    ),
    (
        SOURCE_GITHUB,
        "search_github_context",
        "Search GitHub repositories (READMEs, PR descriptions, code chunks) "
        "for context about the user's feature/journey. Use for code-level "
        "evidence of how a flow is implemented.",
    ),
)


def build_journey_tools(
    embeddings: OpenAIEmbeddings,
    *,
    chroma_root: Path,
    search_results: int,
) -> list[BaseTool]:
    """Build one search tool per context source plus the Swagger lookup tool."""
    tools: list[BaseTool] = []

    for source, tool_name, description in CONTEXT_TOOL_SPECS:
        vector_store = build_vector_store_for_source(
            source, embeddings, chroma_root=chroma_root
        )
        tools.append(
            _make_context_search_tool(
                source=source,
                tool_name=tool_name,
                description=description,
                vector_store=vector_store,
                search_results=search_results,
            )
        )

    swagger_store = build_vector_store_for_source(
        SOURCE_SWAGGER, embeddings, chroma_root=chroma_root
    )
    tools.append(
        _make_swagger_search_tool(
            vector_store=swagger_store, search_results=search_results
        )
    )
    return tools
