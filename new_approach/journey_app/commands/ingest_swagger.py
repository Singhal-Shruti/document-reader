"""``ingest-swagger`` subcommand: load a Swagger/OpenAPI document."""

from __future__ import annotations

import argparse

from journey_app.commands._shared import (
    add_chroma_args,
    add_chunk_args,
    run_ingestion_pipeline,
)
from journey_app.config import SOURCE_SWAGGER
from journey_app.loaders import load_swagger


COMMAND = "ingest-swagger"


def add_arguments(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        COMMAND,
        help=(
            "Load a Swagger/OpenAPI JSON or YAML spec via the OpenAPI "
            "Toolkit and store endpoint chunks in the Swagger Chroma store."
        ),
    )
    parser.add_argument(
        "source",
        help="Filesystem path or http(s) URL of the Swagger/OpenAPI document.",
    )
    parser.add_argument(
        "--no-dereference",
        dest="dereference",
        action="store_false",
        help="Skip $ref dereferencing (faster, less context per endpoint).",
    )
    parser.add_argument(
        "--no-overview",
        dest="include_overview",
        action="store_false",
        help="Do not emit the API-level overview document.",
    )

    add_chroma_args(parser)
    add_chunk_args(parser)
    parser.set_defaults(handler=run, dereference=True, include_overview=True)


def run(args: argparse.Namespace) -> None:
    documents = load_swagger(
        args.source,
        dereference=args.dereference,
        include_overview=args.include_overview,
    )
    run_ingestion_pipeline(
        args,
        documents,
        source=SOURCE_SWAGGER,
        source_label=f"Swagger ({args.source})",
    )
