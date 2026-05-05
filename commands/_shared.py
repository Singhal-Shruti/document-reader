"""Shared argparse fragments and the post-load ingestion pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path

from langchain_core.documents import Document

from clients import build_openai_clients
from config import DEFAULT_CHROMA_COLLECTION, DEFAULT_CHROMA_PATH
from ingestion import split_documents, summarize_documents, upsert_chunks


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
    parser.add_argument("--chunk-size", type=int, default=1_000)
    parser.add_argument("--chunk-overlap", type=int, default=150)


def add_summary_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--skip-summary",
        action="store_true",
        help="Only ingest documents; do not call the chat model for a summary.",
    )


def run_ingestion_pipeline(
    args: argparse.Namespace,
    documents: list[Document],
    *,
    source_label: str,
) -> None:
    """Chunk, embed, and store loaded documents; optionally summarize."""
    chunks = split_documents(
        documents,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    )
    llm, embeddings = build_openai_clients()

    stored_ids = upsert_chunks(
        embeddings,
        chunks,
        persist_directory=args.chroma_path,
        collection_name=args.collection_name,
    )

    print(
        f"Loaded {len(documents)} documents from {source_label} "
        f"and stored {len(stored_ids)} chunks in Chroma collection "
        f"'{args.collection_name}' at {args.chroma_path}."
    )

    if not args.skip_summary:
        print("\nSummary:")
        print(summarize_documents(llm, chunks))
