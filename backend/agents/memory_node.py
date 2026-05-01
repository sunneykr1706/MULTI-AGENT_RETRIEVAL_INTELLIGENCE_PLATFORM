"""Memory nodes — bookend the pipeline to load and persist conversation history."""
import logging
from .state import AgentState
from memory.memory_manager import get_or_create_session, load_history, save_turn, update_user_profile

logger = logging.getLogger(__name__)


def memory_load_node(state: AgentState) -> dict:
    """
    Runs BEFORE retrieval.
    1. Resolves (or creates) the session ID.
    2. Loads all prior conversation turns from SQLite into state['messages'].
       LangGraph's add_messages merges these with any existing messages.
    """
    user_id = state["user_id"]
    session_id = get_or_create_session(user_id, state.get("session_id"))
    history = load_history(user_id, session_id)
    return {
        "session_id": session_id,
        "user_id": user_id,
        "messages": history,   # add_messages appends prior turns to the list
    }


def memory_save_node(state: AgentState) -> dict:
    """
    Runs AFTER validator.
    1. Persists the current Q&A turn to SQLite.
    2. Updates the long-term user profile with accessed document sources.
    """
    session_id = state["session_id"]
    user_id = state["user_id"]
    save_turn(user_id, session_id, state["question"], state["answer"])
    sources = [s["source"] for s in state.get("sources", [])]
    update_user_profile(user_id, session_id, sources)
    logger.info("Memory saved for session %s", session_id)
    return {}
