"""CLI subcommand modules.

Each module exposes:
- ``COMMAND``: the subcommand name shown to users
- ``add_arguments(subparsers)``: registers the subcommand with argparse
- ``run(args)``: executes the subcommand
"""

from journey_app.commands import ingest_confluence, ingest_swagger, journey

ALL_COMMANDS = (ingest_confluence, ingest_swagger, journey)

__all__ = [
    "ALL_COMMANDS",
    "ingest_confluence",
    "ingest_swagger",
    "journey",
]
