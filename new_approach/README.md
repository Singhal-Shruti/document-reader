# new_approach — journey + general-context agent

A LangChain project that ingests documents from multiple sources into
**separate per-source Chroma vector stores** and ships an agent that
answers two kinds of questions over them:

1. **Feature / journey questions** — "What APIs are involved in
   onboarding a new user?", "Walk me through the checkout flow." The
   agent gathers context from Confluence/Jira/GitHub, then maps the
   discovered capabilities to endpoints in the Swagger store, and
   returns a structured *Journey summary / APIs to call / Sources*
   reply.
2. **General questions** — "Who attended the recent platform sync?",
   "What's our retention policy?", "When did we change the auth
   provider?" The agent searches the context stores only (Swagger is
   skipped — it has no business context) and returns a grounded
   *Answer / Sources* reply.

In both modes:

- The agent only uses information it actually retrieved via tools;
  prior knowledge is off.
- The "what is the journey" stores (Confluence, Jira, GitHub) are kept
  physically separate from the "which APIs implement it" store (Swagger
  / OpenAPI), so each can be rebuilt or queried independently.
- If nothing relevant turns up, the agent returns exactly:
  > I couldn't find any information about that in the ingested documents.

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
    │   └── agent.py                # journey + general-mode system prompt
    └── commands/
        ├── ingest_confluence.py    # writes to chroma_db/confluence/
        ├── ingest_swagger.py       # writes to chroma_db/swagger/
        └── journey.py              # runs the agent (both modes)
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

### 2) Run the agent

The same `journey` subcommand handles both feature-journey questions and
general questions; the agent decides which mode applies.

**Feature / journey question:**

```bash
uv run journey journey "What APIs are involved in onboarding a new user?"
uv run journey journey "Walk me through the order-checkout flow"
```

Output:

```
## Journey summary
<2-4 sentences grounded in the context tools.>

## Journey steps
1. **Create the user account**
   - API: `POST /users` (spec: Users API v1)
   - Request: `email` (string, required), `password` (string, required), `displayName` (string)
   - Response: `id` (uuid), `email`, `createdAt` (date-time)
2. **Send verification email**
   - API: `POST /users/{id}/verify` (spec: Users API v1)
   - Request: path `id` (uuid)
   - Response: empty
3. **Provision default workspace**
   - No matching API found in the Swagger store.
4. **Fetch the user profile**
   - API: `GET /users/{id}` (spec: Users API v1)
   - Request: path `id` (uuid)
   - Response: `id`, `email`, `displayName`, `workspaceId`

## Sources
- [confluence] Onboarding runbook — https://.../wiki/...
- [swagger] Users API POST /users — ./specs/users.yaml#POST /users
- [swagger] Users API POST /users/{id}/verify — ./specs/users.yaml#POST /users/{id}/verify
- [swagger] Users API GET /users/{id} — ./specs/users.yaml#GET /users/{id}
```

The `## Journey steps` list always has **exactly** as many items as the
journey has steps in the source documents — every documented step is
listed, in the documented order. Steps that have a matching Swagger
endpoint get an `API / Request / Response` block; steps without a match
are still listed and marked accordingly.

**General question:**

```bash
uv run journey journey "Who were all participants in the recent platform sync meeting?"
uv run journey journey "What does the on-call rotation policy say?"
```

Output:

```
## Answer
- Abhijit
- Manpreet
- Shruti
- Honey

## Sources
- [confluence] Platform sync 2026-05-05 — https://.../wiki/...
```

If nothing relevant turns up, the agent returns exactly:

> I couldn't find any information about that in the ingested documents.

## How the agent decides

1. **Classify the question** — *FEATURE_JOURNEY* (asks how a feature/
   flow/journey works, which APIs implement it, the call sequence,
   integration details, etc.) vs. *GENERAL* (people, meetings,
   decisions, history, runbook details, glossary lookups, anything
   else). When in doubt the agent picks *GENERAL*.
2. **Gather context** — always calls `search_confluence_context` first.
   In journey mode it also calls `search_jira_context` and
   `search_github_context`; in general mode it calls whichever stores
   are plausibly relevant. Empty stores simply return "no documents".
3. **Branch by mode** —
   - *FEATURE_JOURNEY*:
     1. Extract the journey's ordered step list **exactly** as the
        documents describe it (same count, same order, same wording).
     2. For each step, call `find_apis_for_capability` once with that
        step's operation; pick at most one best-matching endpoint
        (never guess, never reuse the same endpoint for unrelated
        steps).
     3. For matched steps, surface the endpoint's method, route,
        request parameters/body, and 200 response shape. Steps with no
        clear API match are still listed, just marked accordingly.
   - *GENERAL*: do **not** call `find_apis_for_capability` (the Swagger
     store has no business context); synthesise the answer from
     whatever the context tools returned.
4. **Answer** — only information actually grounded in tool output is
   used. Output follows the format that matches the mode (above).

## Adding a new context source (e.g. Jira)

1. Implement `journey_app/loaders/jira.py::load_jira(...)` so it returns
   `Document`s with `source`, `source_type='jira'`, and `title`.
2. Add an `ingest-jira` command under `journey_app/commands/` mirroring
   `ingest_confluence.py` (call `run_ingestion_pipeline(..., source=SOURCE_JIRA, ...)`).
3. Register the new command module in `journey_app/commands/__init__.py`.

No journey-agent changes are needed: the `search_jira_context` tool is
already wired and will start returning real chunks as soon as the store
has data.
