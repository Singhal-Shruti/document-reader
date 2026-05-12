"""Persist chunks in the per-source Chroma store with idempotent upserts."""

from __future__ import annotations

from pathlib import Path

from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

from journey_app.clients import build_vector_store_for_source
from journey_app.ingestion.metadata import (
    build_chunk_id,
    group_by_source,
    sanitize_metadata,
)


def upsert_chunks_for_source(
    source: str,
    embeddings: OpenAIEmbeddings,
    chunks: list[Document],
    *,
    chroma_root: Path,
) -> list[str]:
    """Replace existing chunks per ``source`` doc, then add the new chunks.

    All chunks land in the Chroma collection dedicated to ``source``
    (e.g. ``journey_confluence``). For every distinct ``source``-metadata
    value within those chunks, pre-existing rows are deleted first so
    re-ingesting the same page/spec is idempotent.
    """
    vector_store = build_vector_store_for_source(
        source,
        embeddings,
        chroma_root=chroma_root,
    )

    documents_to_add: list[Document] = []
    ids_to_add: list[str] = []

    for source_doc, source_chunks in group_by_source(chunks).items():
        try:
            vector_store._collection.delete(where={"source": source_doc})
        except Exception:
            # Empty collection on first run; deletion is best-effort.
            pass

        for index, chunk in enumerate(source_chunks):
            documents_to_add.append(
                Document(
                    page_content=chunk.page_content,
                    metadata=sanitize_metadata(chunk.metadata),
                )
            )
            ids_to_add.append(build_chunk_id(source_doc, index))

    if not documents_to_add:
        return []

    return vector_store.add_documents(documents_to_add, ids=ids_to_add)
