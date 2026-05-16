"""Constants and environment helpers for the api_call app.

The repo-root ``.env`` (and optionally an ``api_call/.env``) is loaded
automatically so ``OPENAI_API_KEY`` and any per-API auth tokens are
available to the agent.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


DEFAULT_CHAT_MODEL = "gpt-4o-mini"

DEFAULT_ALLOWED_OPERATIONS: tuple[str, ...] = ("GET", "POST", "PUT", "DELETE", "PATCH")


def load_environment() -> None:
    """Load env vars from the repo-root .env and a local api_call/.env.

    Repo-root is preferred (matches the user's existing setup); a local
    ``api_call/.env`` may override or add per-app values without touching
    the global file.
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
            f"{name} is not set. Add it to the repo-root .env or "
            "api_call/.env, or export it in your shell."
        )
    return value
