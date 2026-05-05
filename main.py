"""Single CLI entry point for ingesting websites and asking questions.

Examples:
    uv run python main.py ingest https://example.com
    uv run python main.py ask "What does the site say about pricing?"
"""

from __future__ import annotations

import argparse
from pathlib import Path

from dotenv import load_dotenv

from config import (
    DEFAULT_CHROMA_COLLECTION,
    DEFAULT_CHROMA_PATH,
    DEFAULT_SEARCH_RESULTS,
    build_openai_clients,
    build_vector_store,
)
from ingestion import crawl_url, split_document, store_chunks_in_chroma, summarize_document
from qa_agent import (
    build_agent,
    create_document_search_tool,
    extract_final_answer,
)


def add_chroma_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--chroma-path",
        type=Path,
        default=Path(DEFAULT_CHROMA_PATH),
        help="Local directory where ChromaDB persists vectors.",
    )
    parser.add_argument(
        "--collection-name",
        default=DEFAULT_CHROMA_COLLECTION,
        help="Chroma collection name.",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Crawl websites, store embeddings, and ask document-grounded questions."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest_parser = subparsers.add_parser(
        "ingest",
        help="Crawl a URL and store chunks in ChromaDB.",
    )
    ingest_parser.add_argument("url", help="Absolute http(s) URL to crawl and ingest.")
    add_chroma_args(ingest_parser)
    ingest_parser.add_argument("--chunk-size", type=int, default=1_000)
    ingest_parser.add_argument("--chunk-overlap", type=int, default=150)
    ingest_parser.add_argument("--max-depth", type=int, default=5)
    ingest_parser.add_argument("--max-breadth", type=int, default=20)
    ingest_parser.add_argument("--limit", type=int, default=10)
    ingest_parser.add_argument(
        "--instructions",
        help="Optional natural-language instructions to guide the Tavily crawl.",
    )
    ingest_parser.add_argument(
        "--extract-depth",
        choices=["basic", "advanced"],
        default="advanced",
        help="Tavily extraction depth.",
    )
    ingest_parser.add_argument(
        "--skip-summary",
        action="store_true",
        help="Only ingest documents; do not call the chat model for a summary.",
    )

    ask_parser = subparsers.add_parser(
        "ask",
        help="Ask a question using the Chroma retriever tool and LangChain agent.",
    )
    ask_parser.add_argument("question", help="Question to ask about ingested documents.")
    add_chroma_args(ask_parser)
    ask_parser.add_argument(
        "--search-results",
        type=int,
        default=DEFAULT_SEARCH_RESULTS,
        help="Number of relevant chunks the tool returns to the agent.",
    )

    return parser


def run_ingest(args: argparse.Namespace) -> None:
    documents = crawl_url(
        args.url,
        max_depth=args.max_depth,
        max_breadth=args.max_breadth,
        limit=args.limit,
        instructions=args.instructions,
        extract_depth=args.extract_depth,
    )
    chunks = split_document(
        documents,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    )
    llm, embeddings = build_openai_clients()

    stored_ids = store_chunks_in_chroma(
        embeddings,
        chunks,
        persist_directory=args.chroma_path,
        collection_name=args.collection_name,
    )

    print(
        f"Crawled {len(documents)} pages and ingested "
        f"{len(stored_ids)} chunks into Chroma collection "
        f"'{args.collection_name}' at {args.chroma_path}"
    )

    if not args.skip_summary:
        print("\nSummary:")
        print(summarize_document(llm, chunks))


def run_ask(args: argparse.Namespace) -> None:
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


def main() -> None:
    load_dotenv()
    args = build_parser().parse_args()

    if args.command == "ingest":
        run_ingest(args)
    elif args.command == "ask":
        run_ask(args)


if __name__ == "__main__":
    main()
