"""Swagger / OpenAPI loader for the api_call agent.

Reads an OpenAPI 2.0 / 3.x document (JSON or YAML, local path or URL)
and produces a :class:`ReducedOpenAPISpec` via
``langchain_community.agent_toolkits.openapi.spec.reduce_openapi_spec`` —
exactly the structure ``create_openapi_agent`` expects.

Before reducing the spec we **normalise its `servers` block** so the
downstream SDK always sees an absolute, scheme-qualified base URL. This
is what prevents ``create_openapi_agent``'s
``api_spec.servers[0]["url"]`` from holding a relative path like
``/api/v3`` (Petstore v3) and the request tools from later raising
``requests.exceptions.MissingSchema: No scheme supplied``.

Cases handled:

1. OpenAPI 3 spec with an **absolute** server URL → used as-is.
2. OpenAPI 3 spec with a **relative** server URL (e.g. Petstore v3:
   ``servers: [{"url": "/api/v3"}]``) → resolved against the URL the
   spec was fetched from (``urljoin``).
3. OpenAPI 3 spec with **templated** server variables
   (``"https://{env}.api.com/v1"``) → substituted using each variable's
   ``default`` value, with optional per-variable overrides.
4. OpenAPI 3 spec with **no/empty** ``servers`` → defaults to ``/`` per
   §4.7.5 of the spec, then resolved against the source URL like (2).
5. **Swagger 2.0** documents (``swagger: "2.0"``) with ``host`` /
   ``basePath`` / ``schemes`` and no ``servers`` → synthesised into an
   OpenAPI-3-shaped ``servers`` array (prefer ``https``).
6. ``--server-url`` override → replaces whatever the spec says.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
import yaml
from langchain_community.agent_toolkits.openapi.spec import (
    ReducedOpenAPISpec,
    reduce_openapi_spec,
)


_VAR_PATTERN = re.compile(r"\{([^{}]+)\}")


def _load_raw_spec(source: str) -> tuple[dict[str, Any], str | None]:
    """Read a spec from a path or URL.

    Returns the parsed spec dict and, when the source was an http(s)
    URL, that URL itself — we need it later to resolve any relative
    server URLs declared in the document.
    """
    parsed = urlparse(source)
    if parsed.scheme in {"http", "https"}:
        response = requests.get(source, timeout=30)
        response.raise_for_status()
        text = response.text
        source_url: str | None = source
    else:
        path = Path(source).expanduser()
        if not path.is_file():
            raise FileNotFoundError(f"Swagger spec not found: {path}")
        text = path.read_text(encoding="utf-8")
        source_url = None

    try:
        spec = json.loads(text)
    except json.JSONDecodeError:
        spec = yaml.safe_load(text)
        if not isinstance(spec, dict):
            raise ValueError(
                f"Swagger spec at {source!r} did not parse to a mapping."
            ) from None

    return spec, source_url


def _swagger2_to_servers(
    raw_spec: dict[str, Any], source_url: str | None
) -> list[dict[str, str]]:
    """Synthesise an OpenAPI 3 ``servers`` array from Swagger 2 fields.

    Swagger 2 stores the base URL as ``schemes`` + ``host`` + ``basePath``.
    Missing pieces fall back to the spec source URL where possible.
    """
    host = raw_spec.get("host")
    base_path = raw_spec.get("basePath") or ""
    schemes = list(raw_spec.get("schemes") or [])
    source_parsed = urlparse(source_url) if source_url else None

    if not host and source_parsed is not None:
        host = source_parsed.netloc
    if not host:
        return []

    if not schemes:
        if source_parsed is not None and source_parsed.scheme:
            schemes = [source_parsed.scheme]
        else:
            schemes = ["https"]

    scheme = "https" if "https" in schemes else schemes[0]
    base_path = base_path if base_path.startswith("/") or not base_path else f"/{base_path}"
    return [{"url": f"{scheme}://{host}{base_path}"}]


def _substitute_server_variables(
    url: str,
    variables: dict[str, Any],
    overrides: dict[str, str],
) -> str:
    """Replace ``{var}`` placeholders using overrides then defaults.

    Raises ``ValueError`` if any placeholder cannot be resolved — better
    to fail loudly here than to ship a URL like
    ``https://{env}.api.com/v1`` into the request tools.
    """
    placeholders = set(_VAR_PATTERN.findall(url))
    if not placeholders:
        return url

    resolved = url
    for name in placeholders:
        if name in overrides:
            value: Any = overrides[name]
        else:
            spec_entry = variables.get(name) if isinstance(variables, dict) else None
            if isinstance(spec_entry, dict) and "default" in spec_entry:
                value = spec_entry["default"]
            else:
                raise ValueError(
                    f"Server URL {url!r} references variable {{{name}}} "
                    f"with no default; pass --server-var {name}=<value>."
                )
        resolved = resolved.replace("{" + name + "}", str(value))
    return resolved


def _resolve_server_url(url: str, source_url: str | None) -> str:
    """Return an absolute, scheme-qualified URL.

    If ``url`` already has a scheme and host, it's returned unchanged.
    Otherwise it's resolved against ``source_url`` (the URL the spec
    itself was fetched from). For specs loaded from local files we have
    no base, so we raise a directive-style error telling the user to
    pass ``--server-url``.
    """
    parsed = urlparse(url)
    if parsed.scheme and parsed.netloc:
        return url

    if not source_url:
        raise ValueError(
            f"Spec server URL {url!r} is not absolute and the spec was "
            "loaded from a local file. Pass --server-url "
            "https://<host>[/<base>] so the agent knows where to send "
            "requests."
        )
    return urljoin(source_url, url)


def _normalise_servers(
    raw_spec: dict[str, Any],
    source_url: str | None,
    *,
    server_index: int = 0,
    server_url_override: str | None = None,
    server_variables: dict[str, str] | None = None,
) -> None:
    """Rewrite ``raw_spec['servers']`` so ``servers[0]['url']`` is absolute.

    Operates in-place because ``reduce_openapi_spec`` reads
    ``spec['servers']`` directly. After this returns, the SDK's
    ``api_spec.servers[0]['url']`` is guaranteed to start with
    ``http://`` or ``https://``.
    """
    if server_url_override:
        normalised_override = server_url_override.rstrip("/") or server_url_override
        raw_spec["servers"] = [{"url": normalised_override}]
        return

    swagger_version = str(raw_spec.get("swagger") or "")
    if swagger_version.startswith("2.") and not raw_spec.get("servers"):
        synthesised = _swagger2_to_servers(raw_spec, source_url)
        if not synthesised:
            raise ValueError(
                "Swagger 2.0 spec has no `host` and was not loaded from a "
                "URL; pass --server-url https://<host>[/<base>]."
            )
        raw_spec["servers"] = synthesised

    if not raw_spec.get("servers"):
        raw_spec["servers"] = [{"url": "/"}]

    servers = raw_spec["servers"]
    if not isinstance(servers, list) or not servers:
        raise ValueError("Spec has no `servers` after normalisation.")

    if not 0 <= server_index < len(servers):
        raise ValueError(
            f"--server-index {server_index} is out of range; spec has "
            f"{len(servers)} server(s)."
        )

    chosen = dict(servers[server_index])
    url = str(chosen.get("url") or "")
    if not url:
        raise ValueError(f"servers[{server_index}] has no `url`.")

    variables = chosen.get("variables") or {}
    if variables or "{" in url:
        url = _substitute_server_variables(url, variables, server_variables or {})

    url = _resolve_server_url(url, source_url)

    trimmed = url.rstrip("/")
    chosen["url"] = trimmed or url
    raw_spec["servers"] = [chosen]


def load_reduced_spec(
    source: str,
    *,
    dereference: bool = True,
    server_index: int = 0,
    server_url_override: str | None = None,
    server_variables: dict[str, str] | None = None,
) -> ReducedOpenAPISpec:
    """Load, normalise, and reduce a Swagger / OpenAPI spec.

    Args:
        source: Filesystem path or http(s) URL of the spec.
        dereference: If True, ``$ref`` entries are inlined so the planner
            sees full schemas without chasing references.
        server_index: Which entry of ``servers`` to use when the spec
            declares multiple environments. Default 0 (the SDK's choice).
        server_url_override: If provided, replaces the spec's server URL
            entirely — useful for local specs or pointing at staging.
        server_variables: Per-variable overrides for OpenAPI 3 server
            URL templates (e.g. ``{"environment": "staging"}``).

    Returns:
        A :class:`ReducedOpenAPISpec` whose ``servers[0]['url']`` is
        guaranteed to be absolute and scheme-qualified.
    """
    raw_spec, source_url = _load_raw_spec(source)
    if "paths" not in raw_spec:
        raise ValueError(
            f"Spec at {source!r} has no 'paths'; not a valid OpenAPI document."
        )

    _normalise_servers(
        raw_spec,
        source_url,
        server_index=server_index,
        server_url_override=server_url_override,
        server_variables=server_variables,
    )

    reduced = reduce_openapi_spec(raw_spec, dereference=dereference)
    title = str(raw_spec.get("info", {}).get("title") or "OpenAPI Spec")
    version = str(raw_spec.get("info", {}).get("version") or "unknown")
    print(
        f"Swagger: loaded {len(reduced.endpoints)} endpoint(s) "
        f"from {title} v{version}."
    )
    return reduced


def base_url_for(reduced: ReducedOpenAPISpec) -> str:
    """Return the absolute base URL the agent will hit.

    Mirrors what ``create_openapi_agent`` does internally
    (``api_spec.servers[0]["url"]``) so the CLI can print it for the
    user before any request is sent.
    """
    if not reduced.servers:
        raise ValueError(
            "Spec has no servers; cannot determine a base URL to call."
        )
    first = reduced.servers[0]
    if not isinstance(first, dict) or not first.get("url"):
        raise ValueError("First server entry in spec has no 'url'.")
    return str(first["url"])
