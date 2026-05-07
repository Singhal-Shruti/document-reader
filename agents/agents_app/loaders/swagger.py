"""Swagger / OpenAPI loader built on LangChain's OpenAPI Toolkit.

Uses ``langchain_community.agent_toolkits.openapi.spec.reduce_openapi_spec``
to dereference and condense an OpenAPI 2.0 / 3.x document into a compact
endpoint-oriented form, then converts each endpoint into a LangChain
``Document`` so it can be chunked, embedded and stored alongside other
sources.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
import yaml
from langchain_community.agent_toolkits.openapi.spec import (
    ReducedOpenAPISpec,
    reduce_openapi_spec,
)
from langchain_core.documents import Document

from agents_app.config import SOURCE_TYPE_SWAGGER


def _load_raw_spec(source: str) -> dict[str, Any]:
    """Read a Swagger/OpenAPI document from a local path or URL.

    JSON and YAML payloads are both supported.
    """
    parsed = urlparse(source)
    if parsed.scheme in {"http", "https"}:
        response = requests.get(source, timeout=30)
        response.raise_for_status()
        text = response.text
    else:
        path = Path(source).expanduser()
        if not path.is_file():
            raise FileNotFoundError(f"Swagger spec not found: {path}")
        text = path.read_text(encoding="utf-8")

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        loaded = yaml.safe_load(text)
        if not isinstance(loaded, dict):
            raise ValueError(
                f"Swagger spec at {source!r} did not parse to a mapping."
            ) from None
        return loaded


def _spec_title(spec: dict[str, Any]) -> str:
    return str(spec.get("info", {}).get("title") or "OpenAPI Spec")


def _spec_version(spec: dict[str, Any]) -> str:
    return str(spec.get("info", {}).get("version") or "unknown")


def _format_endpoint(name: str, description: str | None, docs: dict) -> str:
    """Render an endpoint as a compact, embedding-friendly block."""
    lines: list[str] = [f"# {name}"]
    if description:
        lines.append(description.strip())
    if docs:
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(docs, indent=2, sort_keys=True, default=str))
        lines.append("```")
    return "\n".join(lines).strip()


def _overview_document(
    reduced: ReducedOpenAPISpec, *, source: str, title: str, version: str
) -> Document:
    server_urls = [s.get("url", "") for s in reduced.servers if isinstance(s, dict)]
    overview = "\n".join(
        [
            f"# {title} (v{version})",
            "",
            (reduced.description or "").strip(),
            "",
            "Servers:",
            *(f"- {url}" for url in server_urls if url),
            "",
            f"Total endpoints: {len(reduced.endpoints)}",
        ]
    ).strip()

    return Document(
        page_content=overview,
        metadata={
            "source": f"{source}#overview",
            "source_type": SOURCE_TYPE_SWAGGER,
            "title": f"{title} - Overview",
            "spec_title": title,
            "spec_version": version,
            "kind": "overview",
        },
    )


def load_swagger(
    source: str,
    *,
    dereference: bool = True,
    include_overview: bool = True,
) -> list[Document]:
    """Load a Swagger/OpenAPI JSON or YAML document into LangChain documents.

    Args:
        source: Filesystem path or http(s) URL of the spec.
        dereference: If True, ``$ref`` entries are inlined for retrieval.
        include_overview: If True, prepend a single overview document with
            the API title, description, servers, and endpoint count.

    Returns:
        One ``Document`` per HTTP operation (plus an optional overview).
    """
    raw_spec = _load_raw_spec(source)
    if "paths" not in raw_spec:
        raise ValueError(
            f"Spec at {source!r} has no 'paths'; not a valid OpenAPI document."
        )

    reduced = reduce_openapi_spec(raw_spec, dereference=dereference)
    title = _spec_title(raw_spec)
    version = _spec_version(raw_spec)

    documents: list[Document] = []
    if include_overview:
        documents.append(
            _overview_document(reduced, source=source, title=title, version=version)
        )

    for name, description, docs in reduced.endpoints:
        method, _, route = name.partition(" ")
        documents.append(
            Document(
                page_content=_format_endpoint(name, description, docs),
                metadata={
                    "source": f"{source}#{name}",
                    "source_type": SOURCE_TYPE_SWAGGER,
                    "title": f"{title} - {name}",
                    "spec_title": title,
                    "spec_version": version,
                    "http_method": method,
                    "route": route,
                    "kind": "endpoint",
                },
            )
        )

    print("length of documents: ", len(documents))

    if not documents:
        raise RuntimeError(
            f"Swagger spec at {source!r} produced no endpoint documents."
        )

    print(
        f"Swagger: loaded {len(documents)} document(s) "
        f"from {title} v{version}."
    )
    return documents
