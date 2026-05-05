"""Environment defaults and helpers shared across the project."""

from __future__ import annotations

import os


DEFAULT_CHAT_MODEL = "gpt-4o-mini"
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_CHROMA_COLLECTION = "document_reader"
DEFAULT_CHROMA_PATH = "chroma_db"
DEFAULT_SEARCH_RESULTS = 5

SOURCE_TYPE_WEB = "web"
SOURCE_TYPE_CONFLUENCE = "confluence"


def require_env_var(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"{name} is not set. Export it or add it to a local .env file."
        )
    return value
