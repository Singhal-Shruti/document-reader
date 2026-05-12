"""Split loaded documents into embedding-sized chunks per source type.

Confluence pages (and any other natural-language source) are chunked with
:class:`RecursiveCharacterTextSplitter`. Swagger / OpenAPI documents are
emitted as JSON by ``loaders.swagger`` and are chunked with
:class:`RecursiveJsonSplitter` so each chunk stays aligned to the spec's
structure (operation, parameters, requestBody, responses, ...).
"""

from __future__ import annotations

import json
from collections import defaultdict

from langchain_core.documents import Document
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    RecursiveJsonSplitter,
)

from agents_app.config import SOURCE_TYPE_SWAGGER


def split_documents(
    documents: list[Document],
    *,
    chunk_size: int,
    chunk_overlap: int,
) -> list[Document]:
    """Chunk documents using the splitter that fits each source type.

    Documents whose ``metadata['source_type']`` equals ``SOURCE_TYPE_SWAGGER``
    are routed to a JSON splitter; everything else uses the recursive
    character splitter. ``chunk_overlap`` is ignored for Swagger documents
    because :class:`RecursiveJsonSplitter` does not support overlap.
    """
    by_type: dict[str | None, list[Document]] = defaultdict(list)
    for doc in documents:
        by_type[doc.metadata.get("source_type")].append(doc)

    swagger_docs = by_type.pop(SOURCE_TYPE_SWAGGER, [])
    other_docs = [doc for docs in by_type.values() for doc in docs]

    chunks: list[Document] = []
    if other_docs:
        chunks.extend(
            _split_text_documents(
                other_docs,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
        )
    if swagger_docs:
        chunks.extend(
            _split_swagger_documents(swagger_docs, max_chunk_size=chunk_size)
        )
    return chunks


def _split_text_documents(
    documents: list[Document],
    *,
    chunk_size: int,
    chunk_overlap: int,
) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    return splitter.split_documents(documents)


def _split_swagger_documents(
    documents: list[Document],
    *,
    max_chunk_size: int,
) -> list[Document]:
    """Treat each Swagger document's ``page_content`` as JSON and split it."""
    splitter = RecursiveJsonSplitter(max_chunk_size=max_chunk_size)

    payloads: list[dict] = []
    metadatas: list[dict] = []
    for doc in documents:
        try:
            payload = json.loads(doc.page_content)
        except json.JSONDecodeError:
            payload = {"content": doc.page_content}
        if not isinstance(payload, dict):
            payload = {"content": payload}
        payloads.append(payload)
        metadatas.append(dict(doc.metadata))

    return splitter.create_documents(texts=payloads, metadatas=metadatas)
