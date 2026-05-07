"""Shared argparse fragments and the post-load ingestion pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path

from langchain_core.documents import Document

from agents_app.clients import build_openai_clients
from agents_app.config import (
    DEFAULT_CHROMA_COLLECTION,
    DEFAULT_CHROMA_PATH,
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
)
from agents_app.ingestion import split_documents, upsert_chunks


def add_chroma_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--chroma-path",
        type=Path,
        default=Path(DEFAULT_CHROMA_PATH),
        help="Local directory where ChromaDB persists vectors.",
    )
    parser.add_argument(
        "--collection-name",
        default=DEFAULT_CHROMA_COLLECTION,
        help="Chroma collection name.",
    )


def add_chunk_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE)
    parser.add_argument("--chunk-overlap", type=int, default=DEFAULT_CHUNK_OVERLAP)


def run_ingestion_pipeline(
    args: argparse.Namespace,
    documents: list[Document],
    *,
    source_label: str,
) -> None:
    """Chunk, embed, and store loaded documents in Chroma."""
    chunks = split_documents(
        documents,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    )
    _, embeddings = build_openai_clients()

    stored_ids = upsert_chunks(
        embeddings,
        chunks,
        persist_directory=args.chroma_path,
        collection_name=args.collection_name,
    )

    print(
        f"Loaded {len(documents)} document(s) from {source_label} -> "
        f"split into {len(chunks)} chunk(s) -> "
        f"stored {len(stored_ids)} chunk(s) in Chroma collection "
        f"'{args.collection_name}' at {args.chroma_path}."
    )
