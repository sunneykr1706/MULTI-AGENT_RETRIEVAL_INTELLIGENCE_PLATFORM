"""Summary Agent — condenses long retrieved context before the answer LLM sees it."""
import logging
from langchain_core.messages import HumanMessage, SystemMessage
from core.config import get_settings
from core.llm import get_llm_with_fallback
from .state import AgentState

logger = logging.getLogger(__name__)

_SYSTEM = "You are a precise and concise document summarizer."

_HUMAN = """Summarize the following document excerpts into a dense paragraph that
preserves all key facts, names, and figures. Keep it under 600 words.

Documents:
{context}
"""


def summary_node(state: AgentState) -> dict:
    """Condense retrieved context when it exceeds the summary threshold."""
    settings = get_settings()
    messages = [
        SystemMessage(content=_SYSTEM),
        HumanMessage(content=_HUMAN.format(context=state["context"])),
    ]
    response, provider = get_llm_with_fallback(settings, messages)
    logger.info("Summary Agent: condensed context via %s", provider)
    return {"context": response.content}
