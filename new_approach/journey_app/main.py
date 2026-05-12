"""CLI entry point for the journey_app project.

Examples:
    uv run journey ingest-confluence --space-key ENG
    uv run journey ingest-swagger https://petstore3.swagger.io/api/v3/openapi.json
    uv run journey journey "What APIs are involved in onboarding a new user?"
"""

from __future__ import annotations

# When this file is launched directly (e.g. VSCode "Debug Current File" or
# `python journey_app/main.py`), Python only puts the script's own directory
# on sys.path, so the `journey_app` package itself is not importable. Detect
# that case and prepend the project root so absolute imports keep working.
if __name__ == "__main__" and __package__ in (None, ""):
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argparse

from journey_app.commands import ALL_COMMANDS
from journey_app.config import load_environment


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="journey",
        description=(
            "Ingest Confluence/Swagger (and later Jira/GitHub) into per-"
            "source Chroma stores, then ask the journey agent to map a "
            "feature journey to the APIs that implement it."
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
