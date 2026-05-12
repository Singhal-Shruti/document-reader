"""Constants and environment helpers shared across the project.

Each source has its OWN Chroma collection name and its OWN persist
directory under ``CHROMA_ROOT``. This is the "different vector dbs per
source" model — keeping them isolated makes it easy to retrieve from one
source at a time, rebuild a single store, or swap implementations later.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


DEFAULT_CHAT_MODEL = "gpt-4o-mini"
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"

DEFAULT_CHUNK_SIZE = 1_000
DEFAULT_CHUNK_OVERLAP = 150
DEFAULT_SEARCH_RESULTS = 5

CHROMA_ROOT = Path("chroma_db")

SOURCE_CONFLUENCE = "confluence"
SOURCE_JIRA = "jira"
SOURCE_GITHUB = "github"
SOURCE_SWAGGER = "swagger"

ALL_SOURCES: tuple[str, ...] = (
    SOURCE_CONFLUENCE,
    SOURCE_JIRA,
    SOURCE_GITHUB,
    SOURCE_SWAGGER,
)


def collection_name_for(source: str) -> str:
    """Per-source Chroma collection name (kept stable across CLIs)."""
    return f"journey_{source}"


def persist_dir_for(source: str, *, chroma_root: Path = CHROMA_ROOT) -> Path:
    """Per-source on-disk Chroma directory."""
    return chroma_root / source


def load_environment() -> None:
    """Load env vars from new_approach/.env and the repo root .env."""
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
            "(checked new_approach/.env and the repository root .env)."
        )
    return value
