"""Source-specific document loaders.

Each loader returns a list of LangChain ``Document``s with consistent
metadata so the downstream chunking/embedding/storage pipeline is
source-agnostic.
"""

from agents_app.loaders.confluence import load_confluence
from agents_app.loaders.swagger import load_swagger

__all__ = ["load_confluence", "load_swagger"]
