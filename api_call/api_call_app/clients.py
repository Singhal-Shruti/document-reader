"""OpenAI client builder for the api_call app."""

from __future__ import annotations

import os

from langchain_openai import ChatOpenAI

from api_call_app.config import DEFAULT_CHAT_MODEL, require_env_var


def build_chat_llm(model: str | None = None, temperature: float = 0.0) -> ChatOpenAI:
    """Create a ChatOpenAI client from environment configuration.

    The OpenAPI planner agent needs a single LLM that it shares across
    the planner, controller, and request-parsing chains.
    """
    require_env_var("OPENAI_API_KEY")
    chat_model = model or os.getenv("OPENAI_CHAT_MODEL", DEFAULT_CHAT_MODEL)
    return ChatOpenAI(model=chat_model, temperature=temperature)
