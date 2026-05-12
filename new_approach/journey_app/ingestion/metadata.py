"""Metadata helpers for grouping chunks and producing deterministic IDs."""

from __future__ import annotations

from collections import defaultdict

from langchain_core.documents import Document


UNKNOWN_SOURCE = "unknown"


def sanitize_metadata(metadata: dict) -> dict[str, str | int | float | bool]:
    """Keep only Chroma-compatible primitive metadata values."""
    return {
        key: value
        for key, value in metadata.items()
        if isinstance(value, str | int | float | bool)
    }


def group_by_source(chunks: list[Document]) -> dict[str, list[Document]]:
    grouped: dict[str, list[Document]] = defaultdict(list)
    for chunk in chunks:
        source = chunk.metadata.get("source") or UNKNOWN_SOURCE
        grouped[source].append(chunk)
    return dict(grouped)


def build_chunk_id(source: str, index: int) -> str:
    """Deterministic per-source chunk ID so re-ingest overwrites prior chunks."""
    return f"{source}#chunk-{index}"
