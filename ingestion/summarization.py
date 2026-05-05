"""Generate a short bullet-point summary of newly ingested chunks."""

from __future__ import annotations

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI


SUMMARY_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", "You summarize ingested documents clearly and concisely."),
        ("human", "Summarize this document in 5 bullet points:\n\n{document_text}"),
    ]
)


def summarize_documents(
    llm: ChatOpenAI,
    chunks: list[Document],
    *,
    max_chunks: int = 8,
) -> str:
    chain = SUMMARY_PROMPT | llm
    document_text = "\n\n".join(chunk.page_content for chunk in chunks[:max_chunks])
    response = chain.invoke({"document_text": document_text})
    return str(response.content)
