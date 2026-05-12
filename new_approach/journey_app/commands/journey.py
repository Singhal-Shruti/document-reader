"""``journey`` subcommand: ask the agent to map a feature journey to APIs."""

from __future__ import annotations

import argparse

from journey_app.clients import build_openai_clients
from journey_app.commands._shared import add_chroma_args
from journey_app.config import DEFAULT_SEARCH_RESULTS
from journey_app.journey import run_journey


COMMAND = "journey"


def add_arguments(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        COMMAND,
        help=(
            "Ask the agent. For feature/journey questions it gathers "
            "context from Confluence/Jira/GitHub and maps the journey to "
            "APIs in the Swagger store. For general questions it just "
            "returns grounded context from whichever stores have it."
        ),
    )
    parser.add_argument(
        "question",
        help=(
            "Natural-language question. May be a feature/journey query "
            "(\"What APIs are involved in onboarding a new user?\") or a "
            "general one (\"Who attended the recent platform sync?\")."
        ),
    )
    add_chroma_args(parser)
    parser.add_argument(
        "--search-results",
        type=int,
        default=DEFAULT_SEARCH_RESULTS,
        help="Top-k chunks each search tool returns to the agent.",
    )
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace) -> None:
    llm, embeddings = build_openai_clients()
    answer = run_journey(
        args.question,
        llm=llm,
        embeddings=embeddings,
        chroma_root=args.chroma_root,
        search_results=args.search_results,
    )
    print(answer)
