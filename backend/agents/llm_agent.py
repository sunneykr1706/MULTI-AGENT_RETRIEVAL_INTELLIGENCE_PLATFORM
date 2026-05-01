"""LLM Agent — generates the final answer using retrieved (and optionally summarized) context."""
import logging
from langchain_core.messages import HumanMessage, SystemMessage
from core.config import get_settings
from core.llm import get_llm_with_fallback
from .state import AgentState

logger = logging.getLogger(__name__)

_SYSTEM = """You are a helpful AI assistant. Answer the user's question using ONLY
the provided context. If the context does not contain enough information to answer
confidently, say so clearly — do not make up facts.

Context:
{context}"""

_SYSTEM_TOOL = """You are a helpful AI assistant. The context contains raw output from an external tool.
Answer the user's question directly using that tool output.
Do not say phrases like 'based on the provided context'.
When useful, present concise bullet points and include source links if they are present in tool output.
If the tool output is insufficient, say what is missing and ask one concise follow-up.

Tool output:
{context}"""


def llm_node(state: AgentState) -> dict:
    """Call the LLM with retrieved context and conversation history."""
    settings = get_settings()

    tool_mode = (state.get("tool_used") or "none") != "none"

    # Preserve exact image tool output (URLs, quota errors, retry guidance)
    # instead of paraphrasing through another model step.
    if (state.get("tool_used") or "") == "image_generation":
        return {
            "answer": state.get("tool_output") or state.get("context") or "Image generation tool returned no output.",
            "provider_used": "tool",
        }

    if tool_mode:
        messages = [SystemMessage(content=_SYSTEM_TOOL.format(context=state["context"]))]
    else:
        messages = [SystemMessage(content=_SYSTEM.format(context=state["context"]))]

    # Replay full conversation history loaded by memory_load_node.
    for msg in state.get("messages", []):
        messages.append(msg)

    # Append the current question (NOT stored in state["messages"] until memory_save)
    messages.append(HumanMessage(content=state["question"]))

    response, provider = get_llm_with_fallback(settings, messages)
    logger.info("LLM Agent: answer generated via %s", provider)

    return {
        "answer": response.content,
        "provider_used": provider,
    }
