"""Tavily-backed crawler for public websites."""

from __future__ import annotations

from typing import Literal
from urllib.parse import urlparse

from langchain_core.documents import Document
from langchain_tavily import TavilyCrawl

from config import SOURCE_TYPE_WEB, require_env_var


def _validate_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("URL must be an absolute http(s) URL.")
    return url


def crawl_web(
    url: str,
    *,
    max_depth: int,
    max_breadth: int,
    limit: int,
    instructions: str | None,
    extract_depth: Literal["basic", "advanced"],
) -> list[Document]:
    """Crawl a public URL with Tavily and return LangChain documents."""
    require_env_var("TAVILY_API_KEY")

    crawler = TavilyCrawl(
        max_depth=max_depth,
        max_breadth=max_breadth,
        limit=limit,
        instructions=instructions,
        extract_depth=extract_depth,
    )
    crawl_result = crawler.invoke({"url": _validate_url(url)})

    if not isinstance(crawl_result, dict):
        raise RuntimeError(f"Tavily crawl failed: {crawl_result}")
    if error := crawl_result.get("error"):
        raise RuntimeError(f"Tavily crawl failed: {error}")

    documents: list[Document] = []
    for result in crawl_result.get("results", []):
        content = result.get("raw_content") or result.get("content")
        if not content:
            continue
        documents.append(
            Document(
                page_content=content,
                metadata={
                    "source": result.get("url", url),
                    "title": result.get("title"),
                    "source_type": SOURCE_TYPE_WEB,
                },
            )
        )

    if not documents:
        raise RuntimeError(f"Tavily returned no crawlable text for URL: {url}")
    return documents
