"""CLI subcommand modules.

Each module exposes:
- ``COMMAND``: the subcommand name shown to users
- ``add_arguments(subparsers)``: registers the subcommand with argparse
- ``run(args)``: executes the subcommand
"""

from agents_app.commands import ask, ingest_confluence, ingest_swagger

ALL_COMMANDS = (ingest_confluence, ingest_swagger, ask)

__all__ = ["ALL_COMMANDS", "ask", "ingest_confluence", "ingest_swagger"]
