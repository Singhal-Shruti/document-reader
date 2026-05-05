"""Source-agnostic ingestion pipeline: chunking, storage, summarization."""

from ingestion.chunking import split_documents
from ingestion.storage import upsert_chunks
from ingestion.summarization import summarize_documents

__all__ = ["split_documents", "summarize_documents", "upsert_chunks"]
