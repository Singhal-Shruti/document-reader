"""Shared configuration constants and environment helpers."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


DEFAULT_CHAT_MODEL = "gpt-4o-mini"
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_CHROMA_COLLECTION = "agents_documents"
DEFAULT_CHROMA_PATH = "chroma_db"
DEFAULT_CHUNK_SIZE = 1_000
DEFAULT_CHUNK_OVERLAP = 150
DEFAULT_SEARCH_RESULTS = 5

SOURCE_TYPE_CONFLUENCE = "confluence"
SOURCE_TYPE_SWAGGER = "swagger"
SOURCE_TYPE_JIRA = "jira"
SOURCE_TYPE_GITHUB = "github"


def load_environment() -> None:
    """Load env vars from agents/.env and the parent project's .env.

    Both files are loaded so the agents project can reuse the existing
    Confluence/OpenAI configuration in the repo root .env.
    """
    project_root = Path(__file__).resolve().parents[1]
    repo_root = project_root.parent

    for candidate in (repo_root / ".env", project_root / ".env"):
        if candidate.is_file():
            load_dotenv(candidate, override=False)


def require_env_var(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"{name} is not set. Export it or add it to a .env file "
            "(checked agents/.env and the repository root .env)."
        )
    return value
