"""api_call_app — OpenAPI planner+controller agent.

Ingests a Swagger / OpenAPI JSON (or YAML) document with
``langchain_community.agent_toolkits.openapi`` and, on a user prompt,
plans and executes one or several real HTTP API calls against the spec's
servers using the OpenAPI toolkit's request tools.
"""
