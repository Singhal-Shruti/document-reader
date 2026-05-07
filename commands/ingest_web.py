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
    parser.add_argument("--max-breadth", type=int, default=200)
    parser.add_argument("--limit", type=int, default=100)
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
    parser.add_argument(
        "--select-paths",
        nargs="*",
        metavar="REGEX",
        help=(
            "Regex patterns matched against URL paths; only matching paths "
            "will be crawled. Example: --select-paths '/v2/.*' '/docs/.*'"
        ),
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
        select_paths=args.select_paths,
    )
    run_ingestion_pipeline(args, documents, source_label=args.url)
