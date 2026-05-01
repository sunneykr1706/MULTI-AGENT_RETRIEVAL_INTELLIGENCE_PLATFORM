"""Shared state definition for all agents in the LangGraph pipeline."""
from typing import TypedDict, Annotated, List
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    # Full conversation messages (LangGraph merges these via add_messages)
    messages: Annotated[List[BaseMessage], add_messages]

    # The current user question (extracted once for convenience)
    question: str

    # Raw Document objects returned by ChromaDB
    retrieved_docs: list

    # Combined text from retrieved docs (may be replaced by summary)
    context: str

    # Source citations to return to the client
    sources: list

    # Final answer from the LLM
    answer: str

    # Set True by retrieval_agent when context exceeds the summary threshold
    needs_summary: bool

    # Set by validator_agent
    validation_passed: bool
    validation_note: str

    # Which provider ultimately generated the answer
    provider_used: str

    # Session ID for persistent memory (short-term + long-term)
    session_id: str
    user_id: str

    # Optional tool preference coming from UI (web_search | code_interpreter | email | github | calendar | image_generation | rag | auto)
    selected_tool: str

    # Phase 3 — Action Tools
    tool_used: str      # e.g. "web_search", "code_interpreter", "email", "github", "none"
    tool_output: str    # raw output from the tool

    # Runtime fallback visibility
    fallback_used: bool
    fallback_note: str
