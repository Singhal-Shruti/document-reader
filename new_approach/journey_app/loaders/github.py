"""GitHub loader (planned).

The journey workflow already supports a `github` vector store; once a
real loader is implemented here it just needs to return ``Document``s with
``source``, ``source_type='github'``, and ``title`` metadata.
"""

from __future__ import annotations

from langchain_core.documents import Document


def load_github(**_: object) -> list[Document]:
    """Placeholder. Implement with the GitHub REST/GraphQL APIs or a code loader."""
    raise NotImplementedError(
        "GitHub ingestion isn't implemented yet. Implement load_github() "
        "to return LangChain Documents with metadata "
        "{'source': <html_url>, 'source_type': 'github', 'title': <title>}."
    )
