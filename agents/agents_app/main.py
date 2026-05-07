"""CLI entry point for the agents ingestion project.

Examples:
    uv run agents ingest-confluence --space-key ENG
    uv run agents ingest-confluence --page-ids 12345,67890
    uv run agents ingest-swagger ./openapi.json
    uv run agents ingest-swagger https://petstore3.swagger.io/api/v3/openapi.json
"""

from __future__ import annotations

# When this file is launched directly (e.g. VSCode "Debug Current File" or
# `python agents_app/main.py`), Python only puts the script's own directory on
# sys.path, so the `agents_app` package itself is not importable. Detect that
# case and prepend the project root so absolute imports keep working.
if __name__ == "__main__" and __package__ in (None, ""):
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argparse

from agents_app.commands import ALL_COMMANDS
from agents_app.config import load_environment


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agents",
        description=(
            "Load documents from Confluence and Swagger/OpenAPI specs "
            "(with Jira and GitHub planned), embed the chunks with OpenAI "
            "and persist them in a local Chroma vector store."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command_module in ALL_COMMANDS:
        command_module.add_arguments(subparsers)
    return parser


def main() -> None:
    load_environment()
    args = build_parser().parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
