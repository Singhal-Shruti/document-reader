"""Persist chunks in Chroma with idempotent, source-keyed upserts."""

from __future__ import annotations

from pathlib import Path

from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

from agents_app.clients import build_vector_store
from agents_app.ingestion.metadata import (
    build_chunk_id,
    group_by_source,
    sanitize_metadata,
)


def upsert_chunks(
    embeddings: OpenAIEmbeddings,
    chunks: list[Document],
    *,
    persist_directory: Path,
    collection_name: str,
) -> list[str]:
    """Replace existing chunks per source, then add the new chunks.

    For every distinct ``source`` in the incoming chunks we first delete any
    pre-existing rows for that source, then write the new chunks under
    deterministic IDs of the form ``<source>#chunk-<index>``. This makes
    re-ingesting the same Confluence page or Swagger endpoint idempotent.
    """
    vector_store = build_vector_store(
        embeddings,
        persist_directory=persist_directory,
        collection_name=collection_name,
    )

    documents_to_add: list[Document] = []
    ids_to_add: list[str] = []

    for source, source_chunks in group_by_source(chunks).items():
        try:
            vector_store._collection.delete(where={"source": source})
        except Exception:
            # Collection may be empty on first run; deletion is best-effort.
            pass

        for index, chunk in enumerate(source_chunks):
            documents_to_add.append(
                Document(
                    page_content=chunk.page_content,
                    metadata=sanitize_metadata(chunk.metadata),
                )
            )
            ids_to_add.append(build_chunk_id(source, index))

    if not documents_to_add:
        return []

    return vector_store.add_documents(documents_to_add, ids=ids_to_add)
