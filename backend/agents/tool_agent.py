"""Tool Agent — picks the right tool based on the question, runs it, injects result into context."""
import json
import logging
import re

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from core.config import get_settings
from core.llm import get_llm_with_fallback
from tools.web_search import web_search
from tools.code_interpreter import run_python_code
from tools.email_tool import send_email
from tools.github_tool import create_github_issue
from tools.calendar_tool import create_calendar_event
from tools.image_generation_tool import generate_image
from .state import AgentState

logger = logging.getLogger(__name__)

_TOOL_PICKER_SYSTEM = """You are a tool router for an AI assistant.
Choose exactly one tool for the user request from this set:
- web_search
- code_interpreter
- email
- github
- calendar
- image_generation

Decision rules:
- code_interpreter: calculations, math, coding tasks, script execution, data transforms.
- email: sending or drafting emails to a recipient.
- github: creating/opening issues or tickets in GitHub repositories.
- calendar: creating/scheduling meeting or reminder calendar events.
- image_generation: creating an image from a visual prompt.
- web_search: current events, live information, factual lookup, or anything else.

Return ONLY valid JSON: {"tool": "web_search|code_interpreter|email|github|calendar|image_generation"}
No explanation."""

_WEB_QUERY_REWRITE_SYSTEM = """You rewrite web search queries for an AI agent.
Given current question plus optional recent conversation, return ONLY valid JSON:
{"query":"best concise web query"}

Rules:
- Preserve user intent exactly.
- If current question is a follow-up, include missing subject from conversation.
- Keep query concise and factual.
- Do not add commentary or markdown."""


def _extract_json_obj(raw: str) -> dict:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return {}
    try:
        return json.loads(match.group())
    except Exception:
        return {}


def _merge_fallback_note(existing: str, note: str) -> str:
    base = (existing or "").strip()
    add = (note or "").strip()
    if not add:
        return base
    if not base:
        return add
    if add in base:
        return base
    return f"{base} | {add}"


def _pick_tool_via_llm(question: str, settings) -> tuple[str, bool, str]:
    try:
        messages = [
            SystemMessage(content=_TOOL_PICKER_SYSTEM),
            HumanMessage(content=question),
        ]
        response, provider = get_llm_with_fallback(settings, messages)
        parsed = _extract_json_obj(response.content)
        if not parsed:
            logger.warning("Tool picker (%s): non-JSON output, defaulting to web_search", provider)
            return "web_search", True, "tool picker fallback: non-JSON output"
        selected = str(parsed.get("tool", "")).strip().lower()
        if selected in {"web_search", "code_interpreter", "email", "github", "calendar", "image_generation"}:
            return selected, False, ""
        logger.warning("Tool picker (%s): invalid tool '%s', defaulting to web_search", provider, selected)
        return "web_search", True, f"tool picker fallback: invalid tool '{selected}'"
    except Exception as exc:
        logger.warning("Tool picker failed, defaulting to web_search: %s", exc)
        return "web_search", True, "tool picker fallback: provider unavailable"


def _get_last_user_turn(state: AgentState) -> str:
    for msg in reversed(state.get("messages", [])):
        if isinstance(msg, HumanMessage):
            content = (msg.content or "").strip()
            if content:
                return content
    return ""


def _get_last_assistant_turn(state: AgentState) -> str:
    for msg in reversed(state.get("messages", [])):
        if isinstance(msg, AIMessage):
            content = (msg.content or "").strip()
            if content:
                return content
    return ""


def _rewrite_web_query_via_llm(state: AgentState, question: str, settings) -> tuple[str, bool, str]:
    prev_user = _get_last_user_turn(state)
    prev_assistant = _get_last_assistant_turn(state)
    payload = {
        "question": question,
        "previous_user": prev_user,
        "previous_assistant": prev_assistant,
    }
    try:
        messages = [
            SystemMessage(content=_WEB_QUERY_REWRITE_SYSTEM),
            HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
        ]
        response, provider = get_llm_with_fallback(settings, messages)
        parsed = _extract_json_obj(response.content)
        rewritten = str(parsed.get("query", "")).strip()
        if rewritten:
            logger.info("Web query rewrite via %s: '%s' -> '%s'", provider, question[:80], rewritten[:120])
            return rewritten, False, ""
        logger.warning("Web query rewrite (%s): empty output, using original question", provider)
        return question, True, "web query rewrite fallback: empty output"
    except Exception as exc:
        logger.warning("Web query rewrite failed, using original question: %s", exc)
        return question, True, "web query rewrite fallback: provider unavailable"


# ── Individual runners ─────────────────────────────────────────────────────────

def _run_web_search(question: str, settings) -> str:
    return web_search(question, max_results=5, tavily_api_key=settings.tavily_api_key)


def _run_code_interpreter(question: str, settings) -> str:
    """Ask the LLM to write the code, then execute it."""
    messages = [
        SystemMessage(content=(
            "You are a Python code generator. Write a Python script that answers the user's request. "
            "Use only the standard library (math, statistics, datetime, etc.) — no third-party imports. "
            "Output ONLY the Python code, no explanation, no markdown fences."
        )),
        HumanMessage(content=question),
    ]
    response, _ = get_llm_with_fallback(settings, messages)
    code = response.content.strip()
    logger.info("Code interpreter: generated code:\n%s", code[:300])
    result = run_python_code(code)
    return f"Generated code:\n```python\n{code}\n```\n\nOutput:\n{result}"


def _run_email_tool(question: str, settings) -> str:
    """Use the LLM to extract email parameters, then send."""
    messages = [
        SystemMessage(content=(
            'Extract email parameters from the request and return ONLY valid JSON:\n'
            '{"to": "recipient@example.com", "subject": "subject line", "body": "email body text"}\n'
            'If any field cannot be determined, use an empty string.'
        )),
        HumanMessage(content=question),
    ]
    response, _ = get_llm_with_fallback(settings, messages)
    match = re.search(r'\{.*\}', response.content, re.DOTALL)
    if not match:
        return "Could not extract email parameters from the request."
    try:
        params = json.loads(match.group())
    except json.JSONDecodeError:
        return "Could not parse email parameters."
    return send_email(
        to=params.get("to", ""),
        subject=params.get("subject", ""),
        body=params.get("body", ""),
        api_key=settings.sendgrid_api_key,
        from_email=settings.sendgrid_from_email,
    )


def _run_github_tool(question: str, settings) -> str:
    """Use the LLM to extract GitHub issue parameters, then create the issue."""
    messages = [
        SystemMessage(content=(
            'Extract GitHub issue parameters from the request and return ONLY valid JSON:\n'
            '{"repo": "owner/repo-name", "title": "issue title", "body": "issue description"}\n'
            'If the repo is not specified, use an empty string.'
        )),
        HumanMessage(content=question),
    ]
    response, _ = get_llm_with_fallback(settings, messages)
    match = re.search(r'\{.*\}', response.content, re.DOTALL)
    if not match:
        return "Could not extract GitHub issue parameters from the request."
    try:
        params = json.loads(match.group())
    except json.JSONDecodeError:
        return "Could not parse GitHub issue parameters."
    return create_github_issue(
        repo=params.get("repo", ""),
        title=params.get("title", ""),
        body=params.get("body", ""),
        token=settings.github_token,
    )


def _run_calendar_tool(question: str, settings) -> str:
    """Use the LLM to extract calendar event parameters, then generate ICS content."""
    messages = [
        SystemMessage(content=(
            'Extract calendar event parameters and return ONLY valid JSON:\n'
            '{"title":"meeting title","description":"optional details","start_iso":"2026-03-15T10:00:00Z","end_iso":"2026-03-15T11:00:00Z","location":"optional location","attendees":["a@example.com"]}\n'
            'Use ISO-8601 for dates. If missing, keep fields empty except title.'
        )),
        HumanMessage(content=question),
    ]
    response, _ = get_llm_with_fallback(settings, messages)
    match = re.search(r'\{.*\}', response.content, re.DOTALL)
    if not match:
        return "Could not extract calendar event parameters from the request."
    try:
        params = json.loads(match.group())
    except json.JSONDecodeError:
        return "Could not parse calendar event parameters."

    attendees = params.get("attendees", [])
    if not isinstance(attendees, list):
        attendees = []

    return create_calendar_event(
        title=str(params.get("title", "") or ""),
        description=str(params.get("description", "") or ""),
        start_iso=str(params.get("start_iso", "") or ""),
        end_iso=str(params.get("end_iso", "") or ""),
        location=str(params.get("location", "") or ""),
        attendees=[str(x) for x in attendees if str(x).strip()],
    )


def _run_image_generation_tool(question: str, settings) -> str:
    """Generate an image from natural-language prompt using free fallback providers."""
    return generate_image(
        prompt=question,
        replicate_api_token=settings.replicate_api_token,
        replicate_image_model=settings.replicate_image_model,
        hf_api_token=settings.hf_api_token,
        hf_image_model=settings.hf_image_model,
    )


# ── LangGraph node ─────────────────────────────────────────────────────────────

def tool_node(state: AgentState) -> dict:
    """
    Picks the appropriate tool for the question, runs it, and returns
    the result as `context` so the LLM agent can synthesize an answer.
    """
    settings = get_settings()
    question = state["question"]
    forced_tool = (state.get("selected_tool") or "").strip().lower()
    valid_tools = {"web_search", "code_interpreter", "email", "github", "calendar", "image_generation"}

    fallback_used = bool(state.get("fallback_used", False))
    fallback_note = state.get("fallback_note", "")

    if forced_tool in valid_tools:
        tool_name = forced_tool
    else:
        tool_name, picker_fallback, picker_note = _pick_tool_via_llm(question, settings)
        if picker_fallback:
            fallback_used = True
            fallback_note = _merge_fallback_note(fallback_note, picker_note)

    logger.info("Tool Agent: selected tool '%s' for question: %.80s", tool_name, question)

    tool_question = question
    if tool_name == "web_search":
        tool_question, rewrite_fallback, rewrite_note = _rewrite_web_query_via_llm(state, question, settings)
        if rewrite_fallback:
            fallback_used = True
            fallback_note = _merge_fallback_note(fallback_note, rewrite_note)

    if tool_name == "email":
        output = _run_email_tool(question, settings)
    elif tool_name == "github":
        output = _run_github_tool(question, settings)
    elif tool_name == "calendar":
        output = _run_calendar_tool(question, settings)
    elif tool_name == "image_generation":
        output = _run_image_generation_tool(question, settings)
    elif tool_name == "code_interpreter":
        output = _run_code_interpreter(question, settings)
    else:
        output = _run_web_search(tool_question, settings)

    return {
        "tool_used": tool_name,
        "tool_output": output,
        "fallback_used": fallback_used,
        "fallback_note": fallback_note,
        "sources": [],
        "retrieved_docs": [],
        "needs_summary": False,
        # Replace context so the LLM agent synthesizes an answer from tool output
        "context": f"[Tool used: {tool_name}]\n\n{output}",
    }
