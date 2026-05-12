"""LangChain client builders for OpenAI and per-source Chroma stores."""

from __future__ import annotations

import os
from pathlib import Path

from langchain_chroma import Chroma
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from journey_app.config import (
    CHROMA_ROOT,
    DEFAULT_CHAT_MODEL,
    DEFAULT_EMBEDDING_MODEL,
    collection_name_for,
    persist_dir_for,
    require_env_var,
)


def build_openai_clients() -> tuple[ChatOpenAI, OpenAIEmbeddings]:
    """Create LangChain OpenAI clients from environment configuration."""
    require_env_var("OPENAI_API_KEY")

    chat_model = os.getenv("OPENAI_CHAT_MODEL", DEFAULT_CHAT_MODEL)
    embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)

    llm = ChatOpenAI(model=chat_model, temperature=0)
    embeddings = OpenAIEmbeddings(model=embedding_model)
    return llm, embeddings


def build_vector_store_for_source(
    source: str,
    embeddings: OpenAIEmbeddings,
    *,
    chroma_root: Path = CHROMA_ROOT,
) -> Chroma:
    """Open (or create) the dedicated Chroma collection for ``source``."""
    persist_dir = persist_dir_for(source, chroma_root=chroma_root)
    persist_dir.mkdir(parents=True, exist_ok=True)
    return Chroma(
        collection_name=collection_name_for(source),
        embedding_function=embeddings,
        persist_directory=str(persist_dir),
    )
