"""CLI subcommand modules.

Each module exposes:
- `COMMAND`: the subcommand name shown to users
- `add_arguments(subparsers)`: registers the subcommand with argparse
- `run(args)`: executes the subcommand
"""

from commands import ask, ingest_confluence, ingest_web

ALL_COMMANDS = (ingest_web, ingest_confluence, ask)

__all__ = ["ALL_COMMANDS", "ask", "ingest_confluence", "ingest_web"]
