"""Validator Agent — checks the LLM answer for hallucination against retrieved context."""
import logging
import json
from langchain_core.messages import HumanMessage, SystemMessage
from core.config import get_settings
from core.llm import get_llm_with_fallback
from .state import AgentState

logger = logging.getLogger(__name__)

_SYSTEM = """You are a strict factual grounding checker.
Return ONLY valid JSON with this exact schema:
{"passed": true|false, "note": "short reason"}
Do not output markdown or extra keys."""

_HUMAN = """Given the CONTEXT and the ANSWER below, determine if the answer is
grounded in the context (no invented facts) or appropriately says it doesn't know.

CONTEXT:
{context}

ANSWER:
{answer}

SOURCES:
{sources}
"""

def _strip_json_fence(text: str) -> str:
    content = (text or "").strip()
    if content.startswith("```"):
        content = content.strip("`")
        if content.lower().startswith("json"):
            content = content[4:].strip()
    return content.strip()


def _llm_validate(state: AgentState) -> tuple[bool, str]:
    settings = get_settings()
    messages = [
        SystemMessage(content=_SYSTEM),
        HumanMessage(content=_HUMAN.format(
            context=state.get("context", ""),
            answer=state.get("answer", ""),
            sources="\n".join(state.get("sources") or []) or "none",
        )),
    ]
    response, _ = get_llm_with_fallback(settings, messages)
    content = _strip_json_fence(response.content)
    parsed = json.loads(content)
    passed = bool(parsed.get("passed"))
    note = str(parsed.get("note") or "model verdict")
    return passed, note


def validator_node(state: AgentState) -> dict:
    """Verify the answer is grounded in the retrieved context."""
    try:
        passed, note = _llm_validate(state)
        verdict = f"{'PASS' if passed else 'FAIL'}: {note}"
        logger.info("Validator Agent: %s", verdict[:180])
        return {
            "validation_passed": passed,
            "validation_note": verdict,
        }
    except Exception as exc:
        logger.warning("Validator Agent: model validation unavailable (%s)", exc)
        existing_note = (state.get("fallback_note") or "").strip()
        validator_note = "validator fallback: provider unavailable"
        merged_note = validator_note if not existing_note else f"{existing_note} | {validator_note}"
        return {
            "validation_passed": False,
            "validation_note": "FAIL: validator unavailable",
            "fallback_used": True,
            "fallback_note": merged_note,
        }
