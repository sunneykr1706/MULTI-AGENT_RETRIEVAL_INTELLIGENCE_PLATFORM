"""Calendar tool — builds a portable .ics event payload from structured inputs."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable
from uuid import uuid4


def _escape_ics(value: str) -> str:
    text = (value or "").replace("\\", "\\\\")
    text = text.replace(";", "\\;").replace(",", "\\,")
    return text.replace("\n", "\\n")


def _parse_iso_or_default(value: str, default: datetime) -> datetime:
    if not value:
        return default
    raw = value.strip()
    try:
        if raw.endswith("Z"):
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(timezone.utc)
        parsed = datetime.fromisoformat(raw)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        return default


def _fmt_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def create_calendar_event(
    title: str,
    description: str = "",
    start_iso: str = "",
    end_iso: str = "",
    location: str = "",
    attendees: Iterable[str] | None = None,
) -> str:
    """Create a calendar event and return a summary with importable ICS content."""
    now = datetime.now(timezone.utc)
    default_start = now + timedelta(hours=1)
    default_end = default_start + timedelta(hours=1)

    start_dt = _parse_iso_or_default(start_iso, default_start)
    end_dt = _parse_iso_or_default(end_iso, default_end)
    if end_dt <= start_dt:
        end_dt = start_dt + timedelta(hours=1)

    clean_title = (title or "Follow-up meeting").strip()
    clean_desc = (description or "").strip()
    clean_location = (location or "").strip()
    attendee_list = [a.strip() for a in (attendees or []) if a and a.strip()]

    uid = f"{uuid4()}@multi-agent-rag"
    dtstamp = _fmt_utc(now)
    dtstart = _fmt_utc(start_dt)
    dtend = _fmt_utc(end_dt)

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Multi Agent RAG//Calendar Tool//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{dtstamp}",
        f"DTSTART:{dtstart}",
        f"DTEND:{dtend}",
        f"SUMMARY:{_escape_ics(clean_title)}",
    ]

    if clean_desc:
        lines.append(f"DESCRIPTION:{_escape_ics(clean_desc)}")
    if clean_location:
        lines.append(f"LOCATION:{_escape_ics(clean_location)}")
    for email in attendee_list:
        lines.append(f"ATTENDEE;CN={_escape_ics(email)}:mailto:{email}")

    lines.extend(["END:VEVENT", "END:VCALENDAR"])
    ics_text = "\n".join(lines)

    attendees_text = ", ".join(attendee_list) if attendee_list else "none"
    return (
        f"Calendar event drafted:\n"
        f"- Title: {clean_title}\n"
        f"- Start (UTC): {start_dt.isoformat()}\n"
        f"- End (UTC): {end_dt.isoformat()}\n"
        f"- Location: {clean_location or 'not set'}\n"
        f"- Attendees: {attendees_text}\n\n"
        f"Import this ICS into Google/Outlook/Apple Calendar:\n"
        f"```ics\n{ics_text}\n```"
    )
