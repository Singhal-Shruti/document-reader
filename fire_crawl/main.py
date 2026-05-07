"""Crawl or scrape a website with firecrawl-py and save the results to disk.

Examples:
    uv run python main.py scrape https://example.com
    uv run python main.py crawl https://example.com --limit 25
    uv run python main.py crawl https://docs.example.com \\
        --limit 50 --include-paths "^/api/.*" --output-dir output/docs
    uv run python main.py map https://example.com --limit 100
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

from dotenv import load_dotenv
from firecrawl import Firecrawl
from firecrawl.v2.types import Document


def require_env_var(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise SystemExit(
            f"{name} is not set. Copy .env.example to .env and fill it in."
        )
    return value


def safe_filename(url: str) -> str:
    """Build a stable, human-readable filename from a URL."""
    parsed = urlparse(url)
    raw = (parsed.path or "/").strip("/") or "index"
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", raw)[:120]
    digest = hashlib.sha1(url.encode()).hexdigest()[:8]
    return f"{slug}__{digest}"


def write_document(document: Document, *, url: str, output_dir: Path) -> Path:
    """Save a Firecrawl Document as a .md file plus a sidecar metadata.json."""
    output_dir.mkdir(parents=True, exist_ok=True)
    base = output_dir / safe_filename(url)

    md_path = base.with_suffix(".md")
    md_path.write_text(document.markdown or document.html or "", encoding="utf-8")

    metadata = document.metadata.model_dump() if document.metadata else {}
    metadata["sourceURL"] = url
    base.with_suffix(".metadata.json").write_text(
        json.dumps(metadata, indent=2, default=str), encoding="utf-8"
    )
    return md_path


def resolve_url(document: Document, fallback: str) -> str:
    if document.metadata is not None:
        meta = document.metadata.model_dump()
        for key in ("sourceURL", "url", "source_url"):
            value = meta.get(key)
            if value:
                return str(value)
    return fallback


def output_dir_for(url: str, override: Path | None) -> Path:
    if override is not None:
        return override
    domain = urlparse(url).netloc.replace(":", "_") or "site"
    return Path("output") / domain


def add_crawl_filters(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--include-paths",
        nargs="*",
        metavar="REGEX",
        help="Regex patterns; only paths matching at least one are crawled.",
    )
    parser.add_argument(
        "--exclude-paths",
        nargs="*",
        metavar="REGEX",
        help="Regex patterns; paths matching any are skipped.",
    )


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("url", help="Absolute http(s) URL to start from.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Where to write results. Defaults to output/<domain>.",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Crawl websites with firecrawl-py and save pages to disk."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    scrape_parser = subparsers.add_parser(
        "scrape",
        help="Fetch a single URL and save its markdown.",
    )
    add_common_args(scrape_parser)
    scrape_parser.add_argument(
        "--only-main-content",
        action="store_true",
        help="Strip nav/footer/sidebars (Firecrawl's main-content heuristic).",
    )
    scrape_parser.set_defaults(handler=run_scrape)

    crawl_parser = subparsers.add_parser(
        "crawl",
        help="Recursively crawl a site and save each page's markdown.",
    )
    add_common_args(crawl_parser)
    crawl_parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum total pages to fetch.",
    )
    crawl_parser.add_argument(
        "--max-discovery-depth",
        type=int,
        default=None,
        help="How many link hops deep Firecrawl explores from the seed URL.",
    )
    crawl_parser.add_argument(
        "--allow-subdomains",
        action="store_true",
        help="Follow links to subdomains of the seed URL.",
    )
    crawl_parser.add_argument(
        "--allow-external-links",
        action="store_true",
        help="Follow links to entirely different domains.",
    )
    add_crawl_filters(crawl_parser)
    crawl_parser.set_defaults(handler=run_crawl)

    map_parser = subparsers.add_parser(
        "map",
        help="List the URLs Firecrawl discovers on a site (no scraping).",
    )
    add_common_args(map_parser)
    map_parser.add_argument(
        "--limit",
        type=int,
        default=500,
        help="Maximum URLs to return.",
    )
    map_parser.add_argument(
        "--search",
        help="Optional query to bias which URLs Firecrawl prioritises.",
    )
    map_parser.set_defaults(handler=run_map)

    return parser


def build_client() -> Firecrawl:
    return Firecrawl(api_key=require_env_var("FIRECRAWL_API_KEY"))


def run_scrape(args: argparse.Namespace) -> None:
    client = build_client()
    output_dir = output_dir_for(args.url, args.output_dir)

    document = client.scrape(
        args.url,
        formats=["markdown"],
        only_main_content=args.only_main_content or None,
    )
    md_path = write_document(document, url=args.url, output_dir=output_dir)
    chars = len(document.markdown or "")
    print(f"Saved {chars} chars of markdown to {md_path}")


def _iter_documents(documents: Iterable[Document] | None) -> Iterable[Document]:
    return documents or []


def run_crawl(args: argparse.Namespace) -> None:
    client = build_client()
    output_dir = output_dir_for(args.url, args.output_dir)

    job = client.crawl(
        args.url,
        limit=args.limit,
        max_discovery_depth=args.max_discovery_depth,
        include_paths=args.include_paths,
        exclude_paths=args.exclude_paths,
        allow_subdomains=args.allow_subdomains,
        allow_external_links=args.allow_external_links,
        scrape_options={"formats": ["markdown"], "only_main_content": True},
    )

    if job.status not in {"completed", "scraping"}:
        sys.exit(f"Crawl ended with status={job.status}: {job}")

    saved = 0
    for document in _iter_documents(job.data):
        url = resolve_url(document, fallback=args.url)
        write_document(document, url=url, output_dir=output_dir)
        saved += 1

    print(
        f"Crawl status: {job.status} | pages saved: {saved}/{job.total or saved} "
        f"| credits used: {job.credits_used} | output: {output_dir}"
    )


def run_map(args: argparse.Namespace) -> None:
    client = build_client()
    output_dir = output_dir_for(args.url, args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    result = client.map(args.url, limit=args.limit, search=args.search)
    links = [link.url for link in (result.links or [])]
    map_path = output_dir / "sitemap.txt"
    map_path.write_text("\n".join(links) + "\n", encoding="utf-8")

    print(f"Discovered {len(links)} URLs; written to {map_path}")
    for link in links[:10]:
        print(f"  {link}")
    if len(links) > 10:
        print(f"  ... and {len(links) - 10} more")


def main() -> None:
    load_dotenv()
    args = build_parser().parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
