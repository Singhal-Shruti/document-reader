"""OpenAPI planner+controller agent built on the LangChain OpenAPI toolkit.

The agent is a thin wrapper around
``langchain_community.agent_toolkits.openapi.planner.create_openapi_agent``
which already implements the recommended *planner / controller /
orchestrator* hierarchy from the LangChain OpenAPI cookbook.

Given a natural-language user prompt, the orchestrator:

1. Asks the planner to produce a sequence of HTTP calls
   (e.g. ``GET /pet/findByStatus``, ``POST /pet``) that satisfy the
   prompt, drawn ONLY from endpoints in the supplied
   :class:`ReducedOpenAPISpec`.
2. Hands that plan to the controller, which assembles the actual
   request URL, params, and body — and invokes the matching
   ``requests_get`` / ``requests_post`` / … tool to perform the call
   against ``api_spec.servers[0]['url']``.
3. Returns the final answer, grounded in the response bodies.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from langchain_community.agent_toolkits.openapi.planner import (
    create_openapi_agent,
)
from langchain_community.agent_toolkits.openapi.spec import ReducedOpenAPISpec
from langchain_community.utilities.requests import RequestsWrapper
from langchain_openai import ChatOpenAI


Operation = str

_VALID_OPERATIONS: frozenset[str] = frozenset(
    {"GET", "POST", "PUT", "DELETE", "PATCH"}
)


def _normalise_operations(
    operations: Iterable[str] | None,
) -> Sequence[Operation]:
    if not operations:
        return ("GET", "POST", "PUT", "DELETE", "PATCH")
    cleaned: list[str] = []
    for op in operations:
        op_upper = op.strip().upper()
        if op_upper not in _VALID_OPERATIONS:
            raise ValueError(
                f"Unsupported HTTP operation {op!r}; "
                f"choose from {sorted(_VALID_OPERATIONS)}."
            )
        if op_upper not in cleaned:
            cleaned.append(op_upper)
    return tuple(cleaned)


def build_requests_wrapper(
    headers: dict[str, str] | None = None,
    *,
    verify_ssl: bool = True,
) -> RequestsWrapper:
    """Build the requests wrapper that the controller will use.

    Pass any auth headers (e.g. ``Authorization: Bearer ...``) here and
    every API call the agent makes will include them.
    """
    return RequestsWrapper(headers=headers or {}, verify=verify_ssl)


def build_openapi_agent(
    spec: ReducedOpenAPISpec,
    llm: ChatOpenAI,
    *,
    headers: dict[str, str] | None = None,
    verify_ssl: bool = True,
    allowed_operations: Iterable[str] | None = None,
    allow_dangerous_requests: bool = True,
    verbose: bool = True,
) -> Any:
    """Wire the OpenAPI orchestrator agent for ``spec``.

    Args:
        spec: Reduced OpenAPI spec, produced by ``reduce_openapi_spec``.
        llm: ChatOpenAI used by planner, controller, and parsing chains.
        headers: Optional auth/static headers attached to every request.
        verify_ssl: Whether to verify TLS certificates on outgoing calls.
        allowed_operations: HTTP verbs the controller is allowed to use.
            Defaults to all of GET/POST/PUT/DELETE/PATCH.
        allow_dangerous_requests: Must be True for the agent to actually
            invoke HTTP tools — the underlying ``BaseRequestsTool``
            refuses to run otherwise. The caller is expected to vet the
            spec source.
        verbose: Stream the planner/controller reasoning to stdout.

    Returns:
        A LangChain ``AgentExecutor`` that takes ``{"input": prompt}``.
    """
    requests_wrapper = build_requests_wrapper(headers, verify_ssl=verify_ssl)
    return create_openapi_agent(
        api_spec=spec,
        requests_wrapper=requests_wrapper,
        llm=llm,
        allow_dangerous_requests=allow_dangerous_requests,
        allowed_operations=_normalise_operations(allowed_operations),
        verbose=verbose,
    )


def run_openapi_agent(
    prompt: str,
    *,
    spec: ReducedOpenAPISpec,
    llm: ChatOpenAI,
    headers: dict[str, str] | None = None,
    verify_ssl: bool = True,
    allowed_operations: Iterable[str] | None = None,
    allow_dangerous_requests: bool = True,
    verbose: bool = True,
) -> str:
    """Build the agent and run it once for ``prompt``."""
    executor = build_openapi_agent(
        spec,
        llm,
        headers=headers,
        verify_ssl=verify_ssl,
        allowed_operations=allowed_operations,
        allow_dangerous_requests=allow_dangerous_requests,
        verbose=verbose,
    )
    result = executor.invoke({"input": prompt})
    if isinstance(result, dict):
        return str(result.get("output") or result)
    return str(result)
