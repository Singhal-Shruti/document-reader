# api_call — OpenAPI planner+controller agent

A small LangChain app that **ingests a Swagger / OpenAPI JSON document**
with `langchain_community.agent_toolkits.openapi` and, on a single
user prompt, **plans and executes one or several real HTTP API calls**
against the spec's declared server using only the OpenAPI toolkit's
request tools.

Under the hood it uses
[`create_openapi_agent`](https://python.langchain.com/docs/integrations/toolkits/openapi/),
which wires:

- a **planner** that turns the user prompt into a sequence of
  endpoints (`GET /pet/findByStatus`, `POST /pet`, …) drawn only from
  the ingested spec,
- a **controller** that fills in URL params, query strings, and request
  bodies and dispatches each call through
  `requests_get` / `requests_post` / `requests_put` / `requests_delete`
  / `requests_patch`,
- an **orchestrator** that loops between the two until the user's
  request is satisfied — or it runs out of relevant endpoints.

The LLM is OpenAI (`ChatOpenAI`, default `gpt-4o-mini`), and credentials
are loaded from the existing **repo-root `.env`** (`OPENAI_API_KEY`).

## Project layout

```
api_call/
├── pyproject.toml
├── README.md
└── api_call_app/
    ├── main.py                 # CLI entry point
    ├── config.py               # loads ../.env, env helpers
    ├── clients.py              # ChatOpenAI builder
    ├── loaders/
    │   └── swagger.py          # reduce_openapi_spec(JSON/YAML, path or URL)
    └── agent/
        └── openapi_agent.py    # wraps create_openapi_agent + RequestsWrapper
```

## Setup

```bash
cd api_call
uv sync
```

The repo-root `.env` is picked up automatically. The only required
variable is:

```
OPENAI_API_KEY=sk-...
```

Optional:

```
OPENAI_CHAT_MODEL=gpt-4o-mini    # override default model
```

## Usage

```bash
# Read-only example against the public Petstore demo
uv run api-call \
  --spec https://petstore3.swagger.io/api/v3/openapi.json \
  "List the first 3 pets with status=available and summarise their names and ids"

# Write example with auth
uv run api-call \
  --spec ./specs/my-api.yaml \
  --header "Authorization: Bearer $TOKEN" \
  "Create a pet named Rex (category dog, status available), then fetch it back by id"

# Restrict to read-only verbs only
uv run api-call \
  --spec ./specs/my-api.yaml \
  --allow-operation GET \
  "What endpoints expose user data, and what does /users/me return for me right now?"
```

### CLI flags

| Flag                 | Description                                                            |
| -------------------- | ---------------------------------------------------------------------- |
| `prompt`             | Natural-language instruction for the agent (positional).               |
| `--spec`             | Path or URL of the Swagger / OpenAPI JSON / YAML document. Required.   |
| `--header`           | `'Key: Value'` header attached to every outgoing call. Repeatable.     |
| `--allow-operation`  | Restrict HTTP verbs (`GET`/`POST`/`PUT`/`DELETE`/`PATCH`). Repeatable. |
| `--no-dereference`   | Skip `$ref` inlining when reducing the spec.                           |
| `--insecure`         | Disable TLS verification (use only for local/dev specs).               |
| `--quiet`            | Suppress the planner/controller streaming logs.                        |
| `--model`            | Override the OpenAI chat model.                                        |

## Programmatic use

```python
from api_call_app.agent import run_openapi_agent
from api_call_app.clients import build_chat_llm
from api_call_app.config import load_environment
from api_call_app.loaders.swagger import load_reduced_spec

load_environment()
spec = load_reduced_spec("https://petstore3.swagger.io/api/v3/openapi.json")
llm = build_chat_llm()

answer = run_openapi_agent(
    "List the first 3 available pets",
    spec=spec,
    llm=llm,
    headers={"Authorization": "Bearer ..."},   # optional
)
print(answer)
```

## Security note

`create_openapi_agent` requires `allow_dangerous_requests=True` to
actually invoke HTTP tools — this app turns it on by default because
that's the whole point. **Only point it at specs and servers you
trust.** Outbound calls go to whatever `servers[0].url` says in the
ingested document, and the agent will happily attempt `POST` / `PUT` /
`DELETE` unless you constrain it with `--allow-operation GET`.
