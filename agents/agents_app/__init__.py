"""Agents ingestion package.

Loads documents from multiple sources (Confluence, Swagger/OpenAPI, with
Jira and GitHub planned), splits them into chunks, embeds them with OpenAI,
and persists them in a local Chroma vector store using LangChain.
"""
