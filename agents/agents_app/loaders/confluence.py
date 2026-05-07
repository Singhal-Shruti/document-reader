"""Confluence Cloud loader built on ``langchain_community.ConfluenceLoader``."""

from __future__ import annotations

from langchain_community.document_loaders import ConfluenceLoader
from langchain_core.documents import Document

from agents_app.config import SOURCE_TYPE_CONFLUENCE, require_env_var


def _validate_selectors(
    space_key: str | None,
    page_ids: list[str] | None,
    cql: str | None,
) -> None:
    selectors = [
        name
        for name, value in (
            ("--space-key", space_key),
            ("--page-ids", page_ids),
            ("--cql", cql),
        )
        if value
    ]
    if len(selectors) != 1:
        raise ValueError(
            "Provide exactly one of --space-key, --page-ids, or --cql; "
            f"got: {selectors or 'none'}."
        )


def _ensure_source_metadata(
    documents: list[Document], *, base_url: str
) -> list[Document]:
    """ConfluenceLoader sets a ``source`` URL for pages, but be defensive."""
    for doc in documents:
        doc.metadata.setdefault("source_type", SOURCE_TYPE_CONFLUENCE)
        if not doc.metadata.get("source"):
            page_id = doc.metadata.get("id") or doc.metadata.get("page_id")
            doc.metadata["source"] = (
                f"{base_url.rstrip('/')}/pages/{page_id}"
                if page_id
                else "confluence:unknown"
            )
    return documents


def load_confluence(
    *,
    space_key: str | None = None,
    page_ids: list[str] | None = None,
    cql: str | None = None,
    include_attachments: bool = False,
    limit: int = 50,
    max_pages: int = 1_000,
) -> list[Document]:
    """Fetch Confluence Cloud pages into LangChain documents.

    Exactly one of ``space_key``, ``page_ids``, or ``cql`` must be supplied.
    Credentials are read from ``CONFLUENCE_URL``, ``CONFLUENCE_USERNAME`` and
    ``CONFLUENCE_API_TOKEN`` environment variables.
    """
    _validate_selectors(space_key, page_ids, cql)

    base_url = require_env_var("CONFLUENCE_URL")
    username = require_env_var("CONFLUENCE_USERNAME")
    api_token = require_env_var("CONFLUENCE_API_TOKEN")

    loader = ConfluenceLoader(
        url=base_url,
        username=username,
        api_key=api_token,
        cloud=True,
        space_key=space_key,
        page_ids=page_ids,
        cql=cql,
        include_attachments=include_attachments,
        limit=limit,
        max_pages=max_pages,
        keep_markdown_format=True,
    )

    documents = loader.load()
    if not documents:
        raise RuntimeError("Confluence loader returned no documents.")

    print(f"Confluence: loaded {len(documents)} page(s).")
    return _ensure_source_metadata(documents, base_url=base_url)
