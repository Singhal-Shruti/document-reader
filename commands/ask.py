"""`ask` subcommand: query ingested documents through the LangChain agent."""

from __future__ import annotations

import argparse

from clients import build_openai_clients, build_vector_store
from commands._shared import add_chroma_args
from config import DEFAULT_SEARCH_RESULTS
from qa_agent import build_agent, create_document_search_tool, extract_final_answer


COMMAND = "ask"


def add_arguments(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        COMMAND,
        help="Ask a question against ingested documents.",
    )
    parser.add_argument("question", help="Question to ask about ingested documents.")
    add_chroma_args(parser)
    parser.add_argument(
        "--search-results",
        type=int,
        default=DEFAULT_SEARCH_RESULTS,
        help="Number of relevant chunks the tool returns to the agent.",
    )
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace) -> None:
    llm, embeddings = build_openai_clients()
    vector_store = build_vector_store(
        embeddings,
        persist_directory=args.chroma_path,
        collection_name=args.collection_name,
    )
    document_search_tool = create_document_search_tool(
        vector_store,
        search_results=args.search_results,
    )
    agent = build_agent(llm, document_search_tool)

    response = agent.invoke(
        {"messages": [{"role": "user", "content": args.question}]}
    )
    print(extract_final_answer(response))
