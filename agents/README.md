# agents

A LangChain-based ingestion project that loads documents from multiple
sources, embeds them with OpenAI, and persists them in a local
[ChromaDB](https://www.trychroma.com/) collection so other agents/tools
can run retrieval against them.

Supported sources today:

- **Confluence Cloud** (via `langchain_community.ConfluenceLoader`)
- **Swagger / OpenAPI 2.0 / 3.x** specs, JSON or YAML, local file or URL
  (via the LangChain OpenAPI Toolkit's `reduce_openapi_spec`)

Planned sources (scaffolding in place):

- Jira
- GitHub

Once data is ingested, an **`ask` command** spins up a LangChain agent that
calls a `search_ingested_documents` tool against Chroma and answers
questions using only retrieved context.

## Project layout

```
agents/
├── pyproject.toml
├── README.md
├── .env.example
└── agents_app/
    ├── main.py                   # CLI entry point
    ├── config.py                 # Constants + .env loader
    ├── clients.py                # OpenAI + Chroma clients
    ├── loaders/
    │   ├── confluence.py         # Confluence loader
    │   └── swagger.py            # Swagger / OpenAPI loader
    ├── ingestion/
    │   ├── chunking.py           # RecursiveCharacterTextSplitter
    │   ├── metadata.py           # Sanitization + chunk IDs
    │   └── storage.py            # Idempotent Chroma upsert
    ├── qa/
    │   ├── tools.py              # search_ingested_documents tool
    │   └── agent.py              # LangChain agent + system prompt
    └── commands/
        ├── ingest_confluence.py
        ├── ingest_swagger.py
        └── ask.py                # Ask the QA agent
```

## Setup

The project is designed to live alongside the existing `document-reader`
repo and reuse the same `.env`. From the `agents/` directory:

```bash
uv sync
```

Make sure the following env vars are set in either `agents/.env` or the
repo root `.env` (both are loaded automatically):

```
OPENAI_API_KEY=...
OPENAI_CHAT_MODEL=gpt-4o-mini           # optional
OPENAI_EMBEDDING_MODEL=text-embedding-3-small  # optional

CONFLUENCE_URL=https://your-tenant.atlassian.net/wiki
CONFLUENCE_USERNAME=you@example.com
CONFLUENCE_API_TOKEN=...
```

See `.env.example` for the full template.

## Usage

### Ingest a Confluence space

```bash
uv run agents ingest-confluence --space-key ENG
```

Or by page IDs / CQL:

```bash
uv run agents ingest-confluence --page-ids 12345,67890
uv run agents ingest-confluence --cql 'space = ENG AND label = "runbook"'
```

### Ingest a Swagger / OpenAPI spec

From a URL:

```bash
uv run agents ingest-swagger https://petstore3.swagger.io/api/v3/openapi.json
```

From a local file:

```bash
uv run agents ingest-swagger ./specs/my-api.yaml
```

Useful flags:

- `--no-dereference` — skip inlining `$ref`s (faster, less context per chunk)
- `--no-overview` — skip the synthetic API overview document
- `--chunk-size` / `--chunk-overlap` — control text splitting
- `--collection-name` / `--chroma-path` — control Chroma destination

### Ask the QA agent

Once you've ingested some sources, ask questions against them:

```bash
uv run agents ask "How do I create a new pet via the API?"
uv run agents ask "Summarise the on-call runbook"
uv run agents ask "Which endpoints accept query params?" --search-results 8
```

Under the hood the `ask` command:

1. Builds a Chroma retriever over the same collection used for ingestion.
2. Wraps it as a LangChain `@tool` named `search_ingested_documents`.
3. Hands the tool to a `langchain.agents.create_agent` agent driven by the
   `OPENAI_CHAT_MODEL` (default `gpt-4o-mini`).
4. The agent is instructed to always call the tool, ground its answer in
   the returned chunks, refuse to answer if nothing relevant comes back,
   and emit a `Sources:` list at the end.

## How it works

1. **Load** — a source-specific loader returns LangChain `Document`s
   carrying consistent metadata (`source`, `source_type`, `title`, ...).
2. **Split** — `RecursiveCharacterTextSplitter` chunks the documents.
3. **Embed** — OpenAI embeddings via `langchain-openai`.
4. **Upsert** — chunks are stored in Chroma under deterministic IDs of the
   form `<source>#chunk-<index>`. Re-ingesting the same source first
   deletes the old chunks for that `source`, so it's idempotent.

## Adding a new source

1. Create `agents_app/loaders/<source>.py` returning `list[Document]`
   with `source`, `source_type`, and `title` metadata.
2. Re-export it from `agents_app/loaders/__init__.py`.
3. Add a CLI command in `agents_app/commands/<command>.py` that calls
   `run_ingestion_pipeline(args, documents, source_label=...)`.
4. Register the command module in `agents_app/commands/__init__.py`.
