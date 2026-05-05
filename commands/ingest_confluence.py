"""`ingest-confluence` subcommand: fetch Confluence Cloud pages."""

from __future__ import annotations

import argparse

from commands._shared import (
    add_chroma_args,
    add_chunk_args,
    add_summary_arg,
    run_ingestion_pipeline,
)
from loaders import load_confluence


COMMAND = "ingest-confluence"


def _comma_separated(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def add_arguments(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        COMMAND,
        help="Fetch Confluence Cloud pages and store chunks in ChromaDB.",
    )

    selector = parser.add_mutually_exclusive_group(required=True)
    selector.add_argument(
        "--space-key",
        help="Confluence space key to ingest (e.g. ENG).",
    )
    selector.add_argument(
        "--page-ids",
        type=_comma_separated,
        help="Comma-separated Confluence page IDs to ingest.",
    )
    selector.add_argument(
        "--cql",
        help="Confluence Query Language expression to select pages.",
    )

    parser.add_argument(
        "--include-attachments",
        action="store_true",
        help="Also ingest attached files (PDFs, images, etc.).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Page batch size for Confluence API requests.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=1_000,
        help="Maximum total Confluence pages to load.",
    )

    add_chroma_args(parser)
    add_chunk_args(parser)
    add_summary_arg(parser)
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace) -> None:
    documents = load_confluence(
        space_key=args.space_key,
        page_ids=args.page_ids,
        cql=args.cql,
        include_attachments=args.include_attachments,
        limit=args.limit,
        max_pages=args.max_pages,
    )

    label = (
        args.space_key
        or args.cql
        or (",".join(args.page_ids) if args.page_ids else "Confluence")
    )
    run_ingestion_pipeline(args, documents, source_label=f"Confluence ({label})")
