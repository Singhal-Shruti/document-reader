# new_approach — feature-journey agent

A LangChain project that ingests documents from multiple sources into
**separate per-source Chroma vector stores** and ships a `journey` agent
that maps a user-described feature journey to the concrete APIs that
implement it.

The key idea: keep the "what is the journey" stores (Confluence, Jira,
GitHub) physically separate from the "which APIs implement it" store
(Swagger / OpenAPI). The agent first searches the context stores, then
maps the discovered capabilities to specific endpoints in the Swagger
store, and finally returns:

- a short journey summary,
- the ordered list of APIs to call, and
- the source documents the answer was derived from.

## Status

| Source     | Loader      | Search tool                    | Status      |
| ---------- | ----------- | ------------------------------ | ----------- |
| Confluence | implemented | `search_confluence_context`    | ready       |
| Swagger    | implemented | `find_apis_for_capability`     | ready       |
| Jira       | stub        | `search_jira_context`          | placeholder |
| GitHub    | stub        | `search_github_context`        | placeholder |

The Jira/GitHub *search tools* already exist and will return "no
documents" until their loaders are implemented — so the journey
workflow doesn't need code changes once those are filled in.

## Project layout

```
new_approach/
├── pyproject.toml
├── README.md
├── .env.example
└── journey_app/
    ├── main.py                     # `journey` CLI entry point
    ├── config.py                   # constants + per-source paths + .env loader
    ├── clients.py                  # OpenAI + per-source Chroma builders
    ├── loaders/
    │   ├── confluence.py           # ConfluenceLoader (implemented)
    │   ├── swagger.py              # OpenAPI Toolkit reduce_openapi_spec (implemented)
    │   ├── jira.py                 # placeholder
    │   └── github.py               # placeholder
    ├── ingestion/
    │   ├── chunking.py             # RecursiveCharacterTextSplitter
    │   ├── metadata.py             # sanitize + chunk IDs
    │   └── storage.py              # idempotent upsert into per-source Chroma
    ├── journey/
    │   ├── tools.py                # one search tool per source
    │   └── agent.py                # workflow-driven system prompt + agent
    └── commands/
        ├── ingest_confluence.py    # writes to chroma_db/confluence/
        ├── ingest_swagger.py       # writes to chroma_db/swagger/
        └── journey.py              # runs the agent
```

Per-source Chroma layout on disk:

```
chroma_db/
├── confluence/        # collection: journey_confluence
├── jira/              # collection: journey_jira
├── github/            # collection: journey_github
└── swagger/           # collection: journey_swagger
```

## Setup

```bash
cd new_approach
uv sync
```

Either `../.env` (repo root) or `new_approach/.env` is loaded
automatically. See `.env.example` for the variables you need.

## Usage

### 1) Ingest

```bash
# Confluence
uv run journey ingest-confluence --space-key ENG
uv run journey ingest-confluence --page-ids 12345,67890
uv run journey ingest-confluence --cql 'space = ENG AND label = "runbook"'

# Swagger / OpenAPI
uv run journey ingest-swagger https://petstore3.swagger.io/api/v3/openapi.json
uv run journey ingest-swagger ./specs/my-api.yaml
```

Each command writes into its own Chroma store under
`chroma_db/<source>/`. Re-running with the same source is idempotent.

### 2) Run the journey agent

```bash
uv run journey journey "What APIs are involved in onboarding a new user?"
uv run journey journey "Walk me through the order-checkout flow"
```

The output follows a fixed Markdown layout so it's easy to consume
downstream:

```
## Journey summary
<2-4 sentences grounded in the context tools.>

## APIs to call
1. `POST /users` — Create a new user. (spec: Users API)
2. `POST /users/{id}/verify` — Send a verification email. (spec: Users API)
3. `GET /users/{id}` — Fetch the user profile. (spec: Users API)

## Sources
- [confluence] Onboarding runbook — https://.../wiki/...
- [swagger] Users API POST /users — ./specs/users.yaml#POST /users
- [swagger] Users API GET /users/{id} — ./specs/users.yaml#GET /users/{id}
```

If nothing relevant turns up, the agent returns exactly:

> I couldn't find enough information about that journey in the ingested documents to identify the APIs involved.

## How the journey workflow runs

1. **Context gathering** — the agent calls each context tool
   (`search_confluence_context`, `search_jira_context`,
   `search_github_context`) to collect background information about the
   journey from the per-source stores. Sources without ingested data
   simply return "no documents", which the agent records and moves on
   from.
2. **Capability extraction** — internally, the agent enumerates the
   discrete operations the journey requires (e.g. *create user*, *send
   verification email*, *fetch profile*).
3. **API mapping** — for each capability the agent calls
   `find_apis_for_capability` against the Swagger store and collects the
   matching endpoints.
4. **Answer** — only information actually grounded in tool output is
   used; anything the tools didn't surface is omitted. The agent
   produces the fixed Markdown structure shown above.

## Adding a new context source (e.g. Jira)

1. Implement `journey_app/loaders/jira.py::load_jira(...)` so it returns
   `Document`s with `source`, `source_type='jira'`, and `title`.
2. Add an `ingest-jira` command under `journey_app/commands/` mirroring
   `ingest_confluence.py` (call `run_ingestion_pipeline(..., source=SOURCE_JIRA, ...)`).
3. Register the new command module in `journey_app/commands/__init__.py`.

No journey-agent changes are needed: the `search_jira_context` tool is
already wired and will start returning real chunks as soon as the store
has data.
