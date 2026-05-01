"""Agent chat endpoint — runs the full multi-agent LangGraph pipeline."""
import asyncio
import json
import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional

from agents.graph import get_agent_graph
from api.auth import get_current_user
from core.config import get_settings
from memory.memory_manager import load_history, get_user_profile, list_sessions, delete_session, save_feedback

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/agent", tags=["agent"])


class AgentChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = Field(
        default=None,
        description="Leave empty to start a new session. Pass the session_id returned from a previous call to continue the conversation.",
        json_schema_extra={"example": None},
    )
    selected_tool: Optional[str] = Field(
        default=None,
        description="Optional tool hint from UI: web_search | code_interpreter | email | github | calendar | image_generation | rag | auto",
    )


class AgentChatResponse(BaseModel):
    answer: str
    sources: list
    provider_used: str
    validation_passed: bool
    validation_note: str
    needs_summary: bool
    session_id: str
    tool_used: str              # which tool ran ("none" if RAG path was taken)
    fallback_used: bool
    fallback_note: str


class FeedbackRequest(BaseModel):
    session_id: str
    answer: str
    vote: str


@router.post("/chat", response_model=AgentChatResponse)
async def agent_chat(body: AgentChatRequest, current_user: dict = Depends(get_current_user)):
    """
    Multi-agent RAG pipeline with persistent memory:
      1. Memory Load    — load conversation history from SQLite
      2. Retrieval Agent — fetch relevant chunks from ChromaDB
      3. Summary Agent   — (optional) condense long context
      4. LLM Agent       — generate an answer grounded in context
      5. Validator Agent — check the answer for hallucination
      6. Memory Save     — persist Q&A and update user profile

    Pass the returned `session_id` back in subsequent requests to maintain
    conversation memory across calls.
    """
    graph = get_agent_graph()

    # Reject placeholder values that Swagger auto-fills (e.g. "string")
    import re
    sid_input = body.session_id or ""
    if sid_input and not re.match(r'^[0-9a-f\-]{36}$', sid_input):
        sid_input = ""   # treat invalid/placeholder as new session

    initial_state = {
        "messages": [],
        "user_id": current_user["user_id"],
        "session_id": sid_input,
        "question": body.message,
        "selected_tool": body.selected_tool or "auto",
        "retrieved_docs": [],
        "context": "",
        "sources": [],
        "answer": "",
        "needs_summary": False,
        "validation_passed": False,
        "validation_note": "",
        "provider_used": "",
        "tool_used": "none",
        "tool_output": "",
        "fallback_used": False,
        "fallback_note": "",
    }

    try:
        result = graph.invoke(initial_state)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Agent graph error")
        raise HTTPException(status_code=503, detail=str(exc))

    return AgentChatResponse(
        answer=result["answer"],
        sources=result["sources"],
        provider_used=result["provider_used"],
        validation_passed=result["validation_passed"],
        validation_note=result["validation_note"],
        needs_summary=result["needs_summary"],
        session_id=result["session_id"],
        tool_used=result.get("tool_used", "none"),
        fallback_used=result.get("fallback_used", False),
        fallback_note=result.get("fallback_note", ""),
    )


@router.post("/chat/stream", tags=["agent"])
async def agent_chat_stream(body: AgentChatRequest, current_user: dict = Depends(get_current_user)):
    """Run agent chat and stream answer chunks + final metadata as SSE."""
    graph = get_agent_graph()

    import re
    sid_input = body.session_id or ""
    if sid_input and not re.match(r'^[0-9a-f\-]{36}$', sid_input):
        sid_input = ""

    initial_state = {
        "messages": [],
        "user_id": current_user["user_id"],
        "session_id": sid_input,
        "question": body.message,
        "selected_tool": body.selected_tool or "auto",
        "retrieved_docs": [],
        "context": "",
        "sources": [],
        "answer": "",
        "needs_summary": False,
        "validation_passed": False,
        "validation_note": "",
        "provider_used": "",
        "tool_used": "none",
        "tool_output": "",
        "fallback_used": False,
        "fallback_note": "",
    }

    try:
        result = graph.invoke(initial_state)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Agent graph error")
        raise HTTPException(status_code=503, detail=str(exc))

    answer = result.get("answer", "") or ""
    chunk_size = 28

    async def event_gen():
        yield f"data: {json.dumps({'type': 'start'})}\n\n"

        for i in range(0, len(answer), chunk_size):
            chunk = answer[i:i + chunk_size]
            yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
            await asyncio.sleep(0.01)

        final_payload = {
            "type": "final",
            "data": {
                "answer": answer,
                "sources": result.get("sources", []),
                "provider_used": result.get("provider_used", ""),
                "validation_passed": result.get("validation_passed", False),
                "validation_note": result.get("validation_note", ""),
                "needs_summary": result.get("needs_summary", False),
                "session_id": result.get("session_id", sid_input),
                "tool_used": result.get("tool_used", "none"),
                "fallback_used": result.get("fallback_used", False),
                "fallback_note": result.get("fallback_note", ""),
            },
        }
        yield f"data: {json.dumps(final_payload)}\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.get("/history/{session_id}", tags=["agent"])
async def get_history(session_id: str, current_user: dict = Depends(get_current_user)):
    """Return the full conversation history for a session."""
    msgs = load_history(current_user["user_id"], session_id)
    return {
        "session_id": session_id,
        "turns": [
            {"role": "user" if msg.__class__.__name__ == "HumanMessage" else "assistant",
             "content": msg.content}
            for msg in msgs
        ],
    }


@router.get("/profile/{session_id}", tags=["agent"])
async def get_profile(session_id: str, current_user: dict = Depends(get_current_user)):
    """Return the long-term user profile for a session (sources accessed, query count)."""
    return get_user_profile(current_user["user_id"], session_id)


@router.get("/sessions", tags=["agent"])
async def get_all_sessions(current_user: dict = Depends(get_current_user)):
    """Return all sessions ordered by most recent, with message count and first message preview."""
    return {"sessions": list_sessions(current_user["user_id"])}


@router.delete("/sessions/{session_id}", tags=["agent"])
async def delete_session_route(session_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a session and all its messages for the current user."""
    delete_session(current_user["user_id"], session_id)
    return {"deleted": session_id}


@router.post("/feedback", tags=["agent"])
async def submit_feedback(body: FeedbackRequest, current_user: dict = Depends(get_current_user)):
    vote = body.vote.lower().strip()
    if vote not in {"up", "down"}:
        raise HTTPException(status_code=400, detail="vote must be 'up' or 'down'")
    save_feedback(current_user["user_id"], body.session_id, body.answer, vote)
    return {"saved": True}


@router.get("/tool-config", tags=["agent"])
async def tool_config(current_user: dict = Depends(get_current_user)):
    settings = get_settings()
    return {
        "web_search": True,
        "code_interpreter": True,
        "email": bool(settings.sendgrid_api_key and settings.sendgrid_from_email),
        "github": bool(settings.github_token),
        "calendar": True,
        "image_generation": True,
    }
