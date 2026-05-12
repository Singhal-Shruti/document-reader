"""Journey agent: gathers context from per-source stores and maps to APIs."""

from __future__ import annotations

from pathlib import Path

from langchain.agents import create_agent
from langchain_core.messages import AIMessage
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from journey_app.journey.tools import build_journey_tools


NO_ANSWER_FALLBACK = (
    "I couldn't find enough information about that journey in the ingested "
    "documents to identify the APIs involved."
)


SYSTEM_PROMPT = (
    "You are a senior engineer who maps product/feature journeys to the "
    "concrete APIs that implement them. You have access to four vector "
    "stores via tools:\n"
    "  - `search_confluence_context` — product/specs/runbooks\n"
    "  - `search_jira_context` — issues/epics/requirements\n"
    "  - `search_github_context` — code, READMEs, PR descriptions\n"
    "  - `find_apis_for_capability` — Swagger / OpenAPI endpoint catalog\n\n"
    "Workflow you MUST follow for every user question:\n"
    "1. CONTEXT GATHERING — call `search_confluence_context`, "
    "`search_jira_context`, and `search_github_context` (each at least "
    "once, more times with refined queries if useful) to gather context "
    "for the journey. If a context tool reports it has no documents, "
    "note that and continue; do not invent context.\n"
    "2. CAPABILITY EXTRACTION — From the gathered context, enumerate the "
    "discrete operations/capabilities the journey requires "
    "(e.g. 'create user', 'send verification email', 'authenticate', "
    "'fetch profile'). Do this internally; do not show this list yet.\n"
    "3. API MAPPING — For EACH capability identified in step 2, call "
    "`find_apis_for_capability` with that capability as the query, and "
    "collect the matching endpoints. Skip any capability you cannot map "
    "to a concrete endpoint rather than guessing.\n"
    "4. ANSWER — Respond ONLY with information grounded in the tool "
    "results. Do not use prior knowledge or guesses. If, after step 3, "
    f"you have no APIs that map to the journey, reply with exactly: "
    f"\"{NO_ANSWER_FALLBACK}\" and nothing else.\n\n"
    "When you DO have a grounded answer, format your reply in exactly "
    "this Markdown structure:\n\n"
    "## Journey summary\n"
    "<2-4 sentence summary of what the journey does, grounded in the "
    "context tools.>\n\n"
    "## APIs to call\n"
    "1. `<METHOD> <route>` — <one-line purpose>. (spec: <spec_title>)\n"
    "2. `<METHOD> <route>` — <one-line purpose>. (spec: <spec_title>)\n"
    "... (preserve the order they should be invoked in.)\n\n"
    "## Sources\n"
    "- [confluence] <title> — <source URL/path>\n"
    "- [jira] <title> — <source URL/path>\n"
    "- [github] <title> — <source URL/path>\n"
    "- [swagger] <spec_title> <METHOD> <route> — <source URL/path>\n"
    "(Include every source you actually used; omit categories that "
    "contributed nothing.)"
)


def build_journey_agent(llm: ChatOpenAI, tools: list[BaseTool]):
    """Wire an agent that follows the journey workflow above."""
    return create_agent(
        model=llm,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
    )


def _extract_final_answer(agent_response: dict) -> str:
    messages = agent_response.get("messages", [])
    for message in reversed(messages):
        if isinstance(message, AIMessage) and message.content:
            return str(message.content)
    return str(agent_response)


def run_journey(
    question: str,
    *,
    llm: ChatOpenAI,
    embeddings: OpenAIEmbeddings,
    chroma_root: Path,
    search_results: int,
) -> str:
    """End-to-end: build tools, build agent, run it, return its final reply."""
    tools = build_journey_tools(
        embeddings,
        chroma_root=chroma_root,
        search_results=search_results,
    )
    agent = build_journey_agent(llm, tools)
    response = agent.invoke(
        {"messages": [{"role": "user", "content": question}]}
    )
    return _extract_final_answer(response)
