"""`ingest-web` subcommand: crawl a public site with Tavily."""

from __future__ import annotations

import argparse

from commands._shared import (
    add_chroma_args,
    add_chunk_args,
    add_summary_arg,
    run_ingestion_pipeline,
)
from loaders import crawl_web


COMMAND = "ingest-web"


def add_arguments(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        COMMAND,
        help="Crawl a public URL with Tavily and store chunks in ChromaDB.",
    )
    parser.add_argument("url", help="Absolute http(s) URL to crawl and ingest.")

    add_chroma_args(parser)
    add_chunk_args(parser)

    parser.add_argument("--max-depth", type=int, default=5)
    parser.add_argument("--max-breadth", type=int, default=20)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument(
        "--instructions",
        help="Optional natural-language instructions to guide the Tavily crawl.",
    )
    parser.add_argument(
        "--extract-depth",
        choices=["basic", "advanced"],
        default="advanced",
        help="Tavily extraction depth.",
    )

    add_summary_arg(parser)
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace) -> None:
    documents = crawl_web(
        args.url,
        max_depth=args.max_depth,
        max_breadth=args.max_breadth,
        limit=args.limit,
        instructions=args.instructions,
        extract_depth=args.extract_depth,
    )
    run_ingestion_pipeline(args, documents, source_label=args.url)
