"""Retrieval Agent — fetches relevant chunks from ChromaDB."""
import logging
import json
from langchain_core.messages import HumanMessage, SystemMessage
from core.config import get_settings
from core.llm import get_llm_with_fallback
from .state import AgentState
from ingestion.embedder import similarity_search

logger = logging.getLogger(__name__)

_SUMMARY_ROUTER_SYSTEM = """You are a summarization router for RAG context.
Given question + retrieved context, return ONLY valid JSON:
{"needs_summary": true|false}

Set true when the context is too long/redundant/noisy for direct answer quality.
Set false when direct answering is likely better.
No extra keys or prose."""


def _should_summarize(question: str, context: str) -> tuple[bool, bool, str]:
    settings = get_settings()
    preview = context[:6000]
    payload = {
        "question": question,
        "context_preview": preview,
        "context_chars": len(context),
    }
    messages = [
        SystemMessage(content=_SUMMARY_ROUTER_SYSTEM),
        HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
    ]
    try:
        response, provider = get_llm_with_fallback(settings, messages)
        raw = (response.content or "").strip()
        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw.lower().startswith("json"):
                raw = raw[4:].strip()
        parsed = json.loads(raw)
        decision = bool(parsed.get("needs_summary"))
        logger.info("Retrieval summary router via %s: needs_summary=%s", provider, decision)
        return decision, False, ""
    except Exception as exc:
        logger.warning("Retrieval summary router failed (%s), fallback by context size", exc)
        return len(context) > 6000, True, "summary router fallback: provider unavailable"


def retrieval_node(state: AgentState) -> dict:
    """Search ChromaDB for chunks relevant to the user question."""
    docs = similarity_search(state["question"])
    logger.info("Retrieval: found %d chunks for question: %.60s", len(docs), state["question"])

    sources = []
    context_parts = []
    for doc in docs:
        context_parts.append(doc.page_content)
        sources.append({
            "source": doc.metadata.get("source", "unknown"),
            "chunk_index": doc.metadata.get("chunk_index", 0),
            "preview": doc.page_content[:200],
        })

    context = "\n\n---\n\n".join(context_parts)
    needs_summary = False
    fallback_used = bool(state.get("fallback_used", False))
    fallback_note = state.get("fallback_note", "")
    if context:
        needs_summary, used_fallback, fallback_reason = _should_summarize(state["question"], context)
        if used_fallback:
            fallback_used = True
            if fallback_reason and fallback_reason not in fallback_note:
                fallback_note = f"{fallback_note} | {fallback_reason}".strip(" |")

    return {
        "retrieved_docs": docs,
        "context": context,
        "sources": sources,
        "needs_summary": needs_summary,
        "fallback_used": fallback_used,
        "fallback_note": fallback_note,
    }
