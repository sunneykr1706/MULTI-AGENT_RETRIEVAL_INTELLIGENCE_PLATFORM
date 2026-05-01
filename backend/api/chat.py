from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import json

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
import logging
from api.auth import get_current_user

from ingestion.embedder import similarity_search
from core.config import get_settings
from core.llm import make_llm, get_llm_with_fallback

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

SYSTEM_PROMPT = """You are a helpful AI assistant. Answer the user's question using ONLY
the provided context. If the context does not contain enough information to answer
confidently, say so clearly — do not make up facts.

Context:
{context}
"""


class ChatMessage(BaseModel):
    role: str        # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = []
    stream: bool = False


class SourceChunk(BaseModel):
    source: str
    chunk_index: int
    preview: str       # First 200 chars of the chunk


class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceChunk]


# _make_llm and _get_llm_with_fallback are now in core.llm
# Aliased here for backward compatibility
_make_llm = make_llm
_get_llm_with_fallback = get_llm_with_fallback


def _build_context(docs) -> tuple[str, list[SourceChunk]]:
    """Format retrieved docs into a context string and source citations."""
    context_parts = []
    sources = []
    for doc in docs:
        context_parts.append(doc.page_content)
        sources.append(
            SourceChunk(
                source=doc.metadata.get("source", "unknown"),
                chunk_index=doc.metadata.get("chunk_index", 0),
                preview=doc.page_content[:200],
            )
        )
    return "\n\n---\n\n".join(context_parts), sources


@router.post("/", response_model=ChatResponse)
async def chat(body: ChatRequest, current_user: dict = Depends(get_current_user)):
    """Answer a question using RAG (non-streaming)."""
    settings = get_settings()

    # 1. Retrieve relevant chunks
    retrieved_docs = similarity_search(body.message)
    if not retrieved_docs:
        return ChatResponse(
            answer="I couldn't find any relevant information in the knowledge base.",
            sources=[],
        )

    context, sources = _build_context(retrieved_docs)

    # 2. Build message list for the LLM
    messages = [SystemMessage(content=SYSTEM_PROMPT.format(context=context))]
    for msg in (body.history or []):
        if msg.role == "user":
            messages.append(HumanMessage(content=msg.content))
        else:
            messages.append(AIMessage(content=msg.content))
    messages.append(HumanMessage(content=body.message))

    # 3. Call LLM with auto-fallback
    response, _ = _get_llm_with_fallback(settings, messages)

    return ChatResponse(answer=response.content, sources=sources)


@router.post("/stream")
async def chat_stream(body: ChatRequest, current_user: dict = Depends(get_current_user)):
    """Answer a question using RAG with streaming response."""
    settings = get_settings()

    retrieved_docs = similarity_search(body.message)
    if not retrieved_docs:
        async def empty_stream():
            yield json.dumps({"token": "I couldn't find any relevant information."})
        return StreamingResponse(empty_stream(), media_type="text/event-stream")

    context, sources = _build_context(retrieved_docs)

    messages = [SystemMessage(content=SYSTEM_PROMPT.format(context=context))]
    for msg in (body.history or []):
        if msg.role == "user":
            messages.append(HumanMessage(content=msg.content))
        else:
            messages.append(AIMessage(content=msg.content))
    messages.append(HumanMessage(content=body.message))

    # Try providers in fallback order for streaming
    order = [p.strip().lower() for p in settings.llm_fallback_order.split(",")]
    llm = None
    for provider in order:
        candidate = make_llm(provider, settings, streaming=True)
        if candidate is not None:
            llm = candidate
            break
    if llm is None:
        raise HTTPException(status_code=503, detail="No LLM provider configured.")

    async def token_generator():
        async for chunk in llm.astream(messages):
            if chunk.content:
                yield f"data: {json.dumps({'token': chunk.content})}\n\n"
        # Send sources at the end
        serialized = [s.model_dump() for s in sources]
        yield f"data: {json.dumps({'sources': serialized, 'done': True})}\n\n"

    return StreamingResponse(token_generator(), media_type="text/event-stream")
