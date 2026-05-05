"""Source-specific document loaders.

Each loader returns a list of LangChain `Document`s with consistent metadata so
the rest of the pipeline (chunking, embedding, storage) is source-agnostic.
"""

from loaders.confluence import load_confluence
from loaders.web import crawl_web

__all__ = ["crawl_web", "load_confluence"]
