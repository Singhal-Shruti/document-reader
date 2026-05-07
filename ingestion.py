"""Crawl and ingest URLs with Tavily, LangChain, OpenAI, and ChromaDB."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_tavily import TavilyCrawl
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import require_env_var


def validate_url(url: str) -> str:
    parsed_url = urlparse(url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        raise ValueError("URL must be an absolute http(s) URL.")
    return url


def crawl_url(
    url: str,
    *,
    max_depth: int,
    max_breadth: int,
    limit: int,
    instructions: str | None,
    extract_depth: Literal["basic", "advanced"],
) -> list[Document]:
    """Crawl a URL with Tavily and convert results into LangChain documents."""
    require_env_var("TAVILY_API_KEY")

    crawler = TavilyCrawl(
        max_depth=max_depth,
        max_breadth=max_breadth,
        limit=limit,
        instructions=instructions,
        extract_depth=extract_depth,
    )
    crawl_result = crawler.invoke({"url": validate_url(url)})

    if not isinstance(crawl_result, dict):
        raise RuntimeError(f"Tavily crawl failed: {crawl_result}")

    if error := crawl_result.get("error"):
        raise RuntimeError(f"Tavily crawl failed: {error}")

    documents = []
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
                },
            )
        )
    if not documents:
        raise RuntimeError(f"Tavily returned no crawlable text for URL: {url}")

    return documents


def split_document(
    documents: list[Document],
    *,
    chunk_size: int,
    chunk_overlap: int,
) -> list[Document]:
    """Split documents into smaller chunks for embedding."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    return splitter.split_documents(documents)


def sanitize_metadata(metadata: dict) -> dict[str, str | int | float | bool]:
    """Keep only Chroma-compatible primitive metadata values."""
    return {
        key: value
        for key, value in metadata.items()
        if isinstance(value, str | int | float | bool)
    }


def summarize_document(llm: ChatOpenAI, chunks: list[Document]) -> str:
    """Generate a concise summary from the first few chunks."""
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You summarize ingested documents clearly and concisely.",
            ),
            (
                "human",
                "Summarize this document in 5 bullet points:\n\n{document_text}",
            ),
        ]
    )
    chain = prompt | llm

    document_text = "\n\n".join(chunk.page_content for chunk in chunks[:8])
    response = chain.invoke({"document_text": document_text})
    return str(response.content)


def store_chunks_in_chroma(
    embeddings: OpenAIEmbeddings,
    chunks: list[Document],
    *,
    persist_directory: Path,
    collection_name: str,
) -> list[str]:
    """Store chunks in a persistent local Chroma collection."""
    vector_store = Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=str(persist_directory),
    )
    chroma_documents = [
        Document(
            page_content=chunk.page_content,
            metadata=sanitize_metadata(chunk.metadata),
        )
        for chunk in chunks
    ]
    ids = [str(uuid.uuid4()) for _ in chroma_documents]
    return vector_store.add_documents(chroma_documents, ids=ids)
