"""journey_app — feature-journey ingestion + retrieval.

Each source (Confluence, Jira, GitHub, Swagger/OpenAPI) is ingested into
its OWN Chroma collection so they can be queried independently. A
``journey`` command asks the agent to:

1. Search the *context* stores (Confluence, Jira, GitHub) for everything
   relevant to the user's feature/journey question.
2. From that context, identify the operations involved.
3. Search the Swagger store for the concrete API endpoints implementing
   each operation.
4. Return a list of APIs to call together with the source documents the
   answer was derived from.
"""
