"""Shared configuration and client builders for the document reader project."""

from __future__ import annotations

import os
from pathlib import Path

from langchain_chroma import Chroma
from langchain_openai import ChatOpenAI, OpenAIEmbeddings


DEFAULT_CHAT_MODEL = "gpt-4o-mini"
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_CHROMA_COLLECTION = "document_reader"
DEFAULT_CHROMA_PATH = "chroma_db"
DEFAULT_SEARCH_RESULTS = 5


def require_env_var(name: str) -> None:
    if not os.getenv(name):
        raise RuntimeError(
            f"{name} is not set. Export it or add it to a local .env file."
        )


def build_openai_clients() -> tuple[ChatOpenAI, OpenAIEmbeddings]:
    """Create LangChain OpenAI clients using environment configuration."""
    require_env_var("OPENAI_API_KEY")

    chat_model = os.getenv("OPENAI_CHAT_MODEL", DEFAULT_CHAT_MODEL)
    embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)

    llm = ChatOpenAI(model=chat_model, temperature=0)
    embeddings = OpenAIEmbeddings(model=embedding_model)
    return llm, embeddings


def build_vector_store(
    embeddings: OpenAIEmbeddings,
    *,
    persist_directory: Path,
    collection_name: str,
) -> Chroma:
    """Connect to a persisted Chroma collection."""
    return Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=str(persist_directory),
    )
