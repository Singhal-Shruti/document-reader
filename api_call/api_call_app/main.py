"""CLI entry point for the api_call app.

Examples:
    uv run api-call \\
        --spec https://petstore3.swagger.io/api/v3/openapi.json \\
        "List the first 3 pets that are available and tell me their names"

    uv run api-call \\
        --spec ./specs/my-api.yaml \\
        --header "Authorization: Bearer $TOKEN" \\
        "Create a pet named Rex (dog, status=available), then fetch it back"
"""

from __future__ import annotations

if __name__ == "__main__" and __package__ in (None, ""):
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argparse
import sys

from api_call_app.agent import run_openapi_agent
from api_call_app.clients import build_chat_llm
from api_call_app.config import load_environment
from api_call_app.loaders.swagger import base_url_for, load_reduced_spec


def _parse_header(raw: str) -> tuple[str, str]:
    if ":" not in raw:
        raise argparse.ArgumentTypeError(
            f"Header {raw!r} must be in 'Key: Value' format."
        )
    name, _, value = raw.partition(":")
    name = name.strip()
    value = value.strip()
    if not name:
        raise argparse.ArgumentTypeError(
            f"Header {raw!r} has an empty name."
        )
    return name, value


def _parse_server_var(raw: str) -> tuple[str, str]:
    if "=" not in raw:
        raise argparse.ArgumentTypeError(
            f"Server variable {raw!r} must be in 'name=value' format."
        )
    name, _, value = raw.partition("=")
    name = name.strip()
    value = value.strip()
    if not name:
        raise argparse.ArgumentTypeError(
            f"Server variable {raw!r} has an empty name."
        )
    return name, value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="api-call",
        description=(
            "Ingest a Swagger / OpenAPI JSON document and, on a natural-"
            "language prompt, call one or several of its APIs via the "
            "LangChain OpenAPI planner+controller agent."
        ),
    )
    parser.add_argument(
        "prompt",
        help=(
            "Natural-language instruction for the agent, e.g. "
            "\"List the first 3 available pets and summarise them\"."
        ),
    )
    parser.add_argument(
        "--spec",
        required=True,
        help="Path or URL of the Swagger / OpenAPI JSON (or YAML) document.",
    )
    parser.add_argument(
        "--header",
        action="append",
        default=[],
        metavar="'Key: Value'",
        help=(
            "Header to attach to every outgoing API call (repeatable). "
            "Use this for auth, e.g. --header 'Authorization: Bearer ...'."
        ),
    )
    parser.add_argument(
        "--allow-operation",
        action="append",
        default=None,
        choices=["GET", "POST", "PUT", "DELETE", "PATCH"],
        help=(
            "Restrict which HTTP verbs the agent may invoke (repeatable). "
            "Defaults to all five."
        ),
    )
    parser.add_argument(
        "--no-dereference",
        action="store_true",
        help="Skip $ref dereferencing when reducing the spec (faster, but the planner sees raw $refs).",
    )
    parser.add_argument(
        "--server-url",
        default=None,
        help=(
            "Override the base URL the agent calls. Use when the spec is "
            "loaded from a local file with no `servers`, when "
            "`servers[0].url` is relative and the spec source URL is not "
            "the right base, or to point the agent at a non-prod "
            "environment."
        ),
    )
    parser.add_argument(
        "--server-index",
        type=int,
        default=0,
        help=(
            "When the spec declares multiple servers (e.g. prod/staging), "
            "pick this 0-based index. Default 0."
        ),
    )
    parser.add_argument(
        "--server-var",
        action="append",
        default=[],
        metavar="name=value",
        help=(
            "Override an OpenAPI 3 server URL variable (repeatable), e.g. "
            "--server-var environment=staging for a server URL like "
            "https://{environment}.api.com/v1."
        ),
    )
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Disable TLS certificate verification on outgoing requests.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress the planner/controller streaming logs.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Override the OpenAI chat model (defaults to OPENAI_CHAT_MODEL env / gpt-4o-mini).",
    )
    return parser


def main() -> None:
    load_environment()
    args = build_parser().parse_args()

    headers: dict[str, str] = {}
    for raw in args.header:
        name, value = _parse_header(raw)
        headers[name] = value

    server_variables: dict[str, str] = {}
    for raw in args.server_var:
        name, value = _parse_server_var(raw)
        server_variables[name] = value

    spec = load_reduced_spec(
        args.spec,
        dereference=not args.no_dereference,
        server_index=args.server_index,
        server_url_override=args.server_url,
        server_variables=server_variables or None,
    )
    base_url = base_url_for(spec)
    print(f"Calling APIs against base URL: {base_url}", file=sys.stderr)

    llm = build_chat_llm(model=args.model)

    answer = run_openapi_agent(
        args.prompt,
        spec=spec,
        llm=llm,
        headers=headers or None,
        verify_ssl=not args.insecure,
        allowed_operations=args.allow_operation,
        verbose=not args.quiet,
    )
    print(answer)


if __name__ == "__main__":
    main()
