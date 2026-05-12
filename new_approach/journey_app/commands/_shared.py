"""Shared argparse fragments and the post-load ingestion pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path

from langchain_core.documents import Document

from journey_app.clients import build_openai_clients
from journey_app.config import (
    CHROMA_ROOT,
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
    collection_name_for,
    persist_dir_for,
)
from journey_app.ingestion import split_documents, upsert_chunks_for_source


def add_chroma_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--chroma-root",
        type=Path,
        default=CHROMA_ROOT,
        help=(
            "Root directory holding per-source Chroma stores "
            "(<root>/<source>/...)."
        ),
    )


def add_chunk_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE)
    parser.add_argument("--chunk-overlap", type=int, default=DEFAULT_CHUNK_OVERLAP)


def run_ingestion_pipeline(
    args: argparse.Namespace,
    documents: list[Document],
    *,
    source: str,
    source_label: str,
) -> None:
    """Chunk, embed, and store loaded documents in the per-source Chroma."""
    chunks = split_documents(
        documents,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    )
    _, embeddings = build_openai_clients()

    stored_ids = upsert_chunks_for_source(
        source,
        embeddings,
        chunks,
        chroma_root=args.chroma_root,
    )

    print(
        f"[{source}] Loaded {len(documents)} document(s) from {source_label} -> "
        f"split into {len(chunks)} chunk(s) -> "
        f"stored {len(stored_ids)} chunk(s) in collection "
        f"'{collection_name_for(source)}' at "
        f"{persist_dir_for(source, chroma_root=args.chroma_root)}."
    )
