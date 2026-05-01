"""LangGraph StateGraph — wires all agents into the multi-agent pipeline.

Flow:
  START
    └─► memory_load_node
          └─► retrieval_node
                ├─(tools needed)── tool_node ──► llm_node
                ├─(needs_summary)─ summary_node ► llm_node
                └─(short context)─────────────── llm_node
                                                    └──► validator_node ──► memory_save_node ──► END
"""
import logging
import json
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import SystemMessage, HumanMessage
from .state import AgentState
from .memory_node import memory_load_node, memory_save_node
from .retrieval_agent import retrieval_node
from .summary_agent import summary_node
from .llm_agent import llm_node
from .validator_agent import validator_node
from .tool_agent import tool_node
from core.config import get_settings
from core.llm import get_llm_with_fallback

logger = logging.getLogger(__name__)

_ROUTER_SYSTEM = """You are a strict routing function in a multi-agent RAG system.
Return ONLY valid JSON: {"route":"tools"|"summary"|"llm"}.

Routing policy:
- tools: user intent needs external actions/tools (web search, calculations/code execution, email, github), OR no useful retrieved docs.
- summary: docs exist and are long/noisy; summarization improves answer quality.
- llm: docs exist and are already concise enough for direct answering.

Never include extra keys or prose."""


def _route_after_retrieval_fallback(state: AgentState) -> str:
    """Safe fallback routing when model routing is unavailable."""
    if not state.get("retrieved_docs"):
        return "tools"
    return "summary" if state.get("needs_summary") else "llm"


def _route_after_retrieval(state: AgentState) -> str:
    """
    Three-way routing after retrieval:
    - 'tools'   : question explicitly needs a tool, OR no docs retrieved at all
    - 'summary' : docs found but context is long
    - 'llm'     : docs found and context is short
    """
    forced_tool = (state.get("selected_tool") or "").lower().strip()

    # Deterministic routing from UI tool selector
    if forced_tool and forced_tool not in {"auto", "none", "rag"}:
        return "tools"

    # User explicitly wants RAG/doc flow (no tool usage)
    if forced_tool in {"none", "rag"}:
        return "summary" if state.get("needs_summary") else "llm"

    settings = get_settings()
    docs_count = len(state.get("retrieved_docs") or [])
    context_chars = len((state.get("context") or "").strip())
    payload = {
        "question": state.get("question", ""),
        "has_docs": docs_count > 0,
        "docs_count": docs_count,
        "needs_summary": bool(state.get("needs_summary")),
        "context_chars": context_chars,
    }

    messages = [
        SystemMessage(content=_ROUTER_SYSTEM),
        HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
    ]

    try:
        response, provider = get_llm_with_fallback(settings, messages)
        content = (response.content or "").strip()
        if content.startswith("```"):
            content = content.strip("`")
            if content.lower().startswith("json"):
                content = content[4:].strip()

        route = (json.loads(content).get("route") or "").strip().lower()
        if route in {"tools", "summary", "llm"}:
            logger.info("Router: route=%s via %s", route, provider)
            return route

        logger.warning("Router: invalid route '%s', using fallback", route)
        return _route_after_retrieval_fallback(state)
    except Exception as exc:
        logger.warning("Router: LLM routing failed (%s), using fallback", exc)
        return _route_after_retrieval_fallback(state)


def build_agent_graph():
    """Construct and compile the multi-agent LangGraph."""
    graph = StateGraph(AgentState)

    graph.add_node("memory_load", memory_load_node)
    graph.add_node("retrieval", retrieval_node)
    graph.add_node("tools", tool_node)
    graph.add_node("summary", summary_node)
    graph.add_node("llm", llm_node)
    graph.add_node("validator", validator_node)
    graph.add_node("memory_save", memory_save_node)

    graph.add_edge(START, "memory_load")
    graph.add_edge("memory_load", "retrieval")
    graph.add_conditional_edges(
        "retrieval",
        _route_after_retrieval,
        {"tools": "tools", "summary": "summary", "llm": "llm"},
    )
    graph.add_edge("tools", "llm")
    graph.add_edge("summary", "llm")
    graph.add_edge("llm", "validator")
    graph.add_edge("validator", "memory_save")
    graph.add_edge("memory_save", END)

    compiled = graph.compile()
    logger.info("Multi-agent graph: memory_load → retrieval → (tools|summary|llm) → llm → validator → memory_save")
    return compiled


# Module-level singleton — compiled once and reused
_graph = None


def get_agent_graph():
    global _graph
    if _graph is None:
        _graph = build_agent_graph()
    return _graph

