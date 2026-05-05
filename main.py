"""CLI entry point: build the parser, dispatch to subcommand handlers.

Examples:
    uv run python main.py ingest-web https://example.com
    uv run python main.py ingest-confluence --space-key ENG
    uv run python main.py ask "What does the docs site say about pricing?"
"""

from __future__ import annotations

import argparse

from dotenv import load_dotenv

from commands import ALL_COMMANDS


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Crawl public websites or Confluence Cloud, embed chunks in "
            "ChromaDB, and ask document-grounded questions."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command_module in ALL_COMMANDS:
        command_module.add_arguments(subparsers)
    return parser


def main() -> None:
    load_dotenv()
    args = build_parser().parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
