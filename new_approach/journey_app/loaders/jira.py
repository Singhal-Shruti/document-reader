"""Jira Cloud loader (planned).

The journey workflow already supports a `jira` vector store; once a real
loader is implemented here it just needs to return ``Document``s with
``source``, ``source_type='jira'``, and ``title`` metadata.
"""

from __future__ import annotations

from langchain_core.documents import Document


def load_jira(**_: object) -> list[Document]:
    """Placeholder. Implement with ``langchain_community`` Jira tooling."""
    raise NotImplementedError(
        "Jira ingestion isn't implemented yet. Implement load_jira() to "
        "return LangChain Documents with metadata "
        "{'source': <issue url>, 'source_type': 'jira', 'title': <summary>}."
    )
