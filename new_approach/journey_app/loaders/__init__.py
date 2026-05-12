"""Source-specific document loaders.

Each loader returns a list of LangChain ``Document``s with consistent
metadata so the downstream chunking/embedding/storage pipeline is
source-agnostic.
"""

from journey_app.loaders.confluence import load_confluence
from journey_app.loaders.github import load_github
from journey_app.loaders.jira import load_jira
from journey_app.loaders.swagger import load_swagger

__all__ = [
    "load_confluence",
    "load_github",
    "load_jira",
    "load_swagger",
]
