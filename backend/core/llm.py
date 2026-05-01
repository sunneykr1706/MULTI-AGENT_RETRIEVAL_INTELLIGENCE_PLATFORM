"""Shared LLM factory — used by both api/chat.py and the agents layer."""
import logging

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from fastapi import HTTPException

logger = logging.getLogger(__name__)


def make_llm(provider: str, settings, streaming: bool = False):
    """Create an LLM instance for the given provider, or None if not configured."""
    if provider == "google" and settings.google_api_key:
        return ChatGoogleGenerativeAI(
            model=settings.google_model,
            google_api_key=settings.google_api_key,
            temperature=0,
            streaming=streaming,
        )
    if provider == "groq" and settings.groq_api_key:
        return ChatGroq(
            model=settings.groq_model,
            groq_api_key=settings.groq_api_key,
            temperature=0,
            streaming=streaming,
        )
    if provider == "openai" and settings.openai_api_key:
        return ChatOpenAI(
            model=settings.openai_model,
            openai_api_key=settings.openai_api_key,
            temperature=0,
            streaming=streaming,
        )
    return None


def get_llm_with_fallback(settings, messages, streaming: bool = False):
    """Try providers in llm_fallback_order. Returns (response, provider_used)."""
    order = [p.strip().lower() for p in settings.llm_fallback_order.split(",")]
    last_error = None
    for provider in order:
        llm = make_llm(provider, settings, streaming)
        if llm is None:
            continue
        try:
            response = llm.invoke(messages)
            logger.info("LLM answered via provider: %s", provider)
            return response, provider
        except Exception as exc:
            logger.warning("Provider %s failed: %s", provider, exc)
            last_error = exc
    raise HTTPException(
        status_code=503,
        detail=f"All LLM providers failed. Last error: {last_error}",
    )
