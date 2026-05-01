"""SQLite-backed store for auth + user-scoped memory."""
import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "memory.db"
LEGACY_USER_ID = "legacy-user"


def _conn():
    c = sqlite3.connect(str(DB_PATH))
    c.row_factory = sqlite3.Row
    return c


def _column_exists(db: sqlite3.Connection, table: str, column: str) -> bool:
    rows = db.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r["name"] == column for r in rows)


def _ensure_column(db: sqlite3.Connection, table: str, column: str, definition: str):
    if not _column_exists(db, table, column):
        db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db():
    """Create/migrate tables for auth and user-scoped memory."""
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id        TEXT PRIMARY KEY,
                email          TEXT NOT NULL UNIQUE,
                password_hash  TEXT NOT NULL,
                name           TEXT NOT NULL DEFAULT '',
                created_at     TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS refresh_tokens (
                jti         TEXT PRIMARY KEY,
                user_id     TEXT NOT NULL,
                expires_at  TEXT NOT NULL,
                revoked     INTEGER NOT NULL DEFAULT 0,
                created_at  TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS message_feedback (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     TEXT NOT NULL,
                session_id  TEXT NOT NULL,
                answer      TEXT NOT NULL,
                vote        TEXT NOT NULL,
                created_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                user_id    TEXT
            );

            CREATE TABLE IF NOT EXISTS messages (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  TEXT NOT NULL,
                role        TEXT NOT NULL,
                content     TEXT NOT NULL,
                timestamp   TEXT NOT NULL,
                user_id     TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            );

            CREATE TABLE IF NOT EXISTS user_profiles (
                session_id       TEXT PRIMARY KEY,
                sources_accessed TEXT NOT NULL DEFAULT '[]',
                query_count      INTEGER NOT NULL DEFAULT 0,
                updated_at       TEXT NOT NULL,
                user_id          TEXT
            );
            """
        )

        _ensure_column(db, "sessions", "user_id", "TEXT")
        _ensure_column(db, "messages", "user_id", "TEXT")
        _ensure_column(db, "user_profiles", "user_id", "TEXT")

        db.execute(
            "INSERT OR IGNORE INTO users (user_id, email, password_hash, name, created_at) VALUES (?,?,?,?,?)",
            (LEGACY_USER_ID, "legacy@local", "", "Legacy", now),
        )

        db.execute("UPDATE sessions SET user_id = ? WHERE user_id IS NULL", (LEGACY_USER_ID,))
        db.execute("UPDATE messages SET user_id = ? WHERE user_id IS NULL", (LEGACY_USER_ID,))
        db.execute("UPDATE user_profiles SET user_id = ? WHERE user_id IS NULL", (LEGACY_USER_ID,))

        db.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_messages_session_user ON messages(session_id, user_id)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_profiles_user_session ON user_profiles(user_id, session_id)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_refresh_user ON refresh_tokens(user_id)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_feedback_user_session ON message_feedback(user_id, session_id)")

    logger.info("Memory/Auth DB initialised at %s", DB_PATH)


def create_user(email: str, password_hash: str, name: str = "") -> dict:
    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as db:
        db.execute(
            "INSERT INTO users (user_id, email, password_hash, name, created_at) VALUES (?,?,?,?,?)",
            (user_id, email.lower().strip(), password_hash, name.strip(), now),
        )
    return {"user_id": user_id, "email": email.lower().strip(), "name": name.strip()}


def get_user_by_email(email: str) -> dict | None:
    with _conn() as db:
        row = db.execute(
            "SELECT user_id, email, password_hash, name, created_at FROM users WHERE email = ?",
            (email.lower().strip(),),
        ).fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: str) -> dict | None:
    with _conn() as db:
        row = db.execute(
            "SELECT user_id, email, password_hash, name, created_at FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    return dict(row) if row else None


def store_refresh_token(user_id: str, jti: str, expires_at: str):
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as db:
        db.execute(
            "INSERT INTO refresh_tokens (jti, user_id, expires_at, revoked, created_at) VALUES (?,?,?,?,?)",
            (jti, user_id, expires_at, 0, now),
        )


def is_refresh_token_active(user_id: str, jti: str) -> bool:
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as db:
        row = db.execute(
            "SELECT 1 FROM refresh_tokens WHERE jti = ? AND user_id = ? AND revoked = 0 AND expires_at > ?",
            (jti, user_id, now),
        ).fetchone()
    return bool(row)


def revoke_refresh_token(jti: str):
    with _conn() as db:
        db.execute("UPDATE refresh_tokens SET revoked = 1 WHERE jti = ?", (jti,))


def get_or_create_session(user_id: str, session_id: str | None = None) -> str:
    if not session_id:
        session_id = str(uuid.uuid4())

    with _conn() as db:
        exists = db.execute(
            "SELECT session_id FROM sessions WHERE session_id = ? AND user_id = ?",
            (session_id, user_id),
        ).fetchone()

        if not exists:
            # if client passed someone else's session_id, avoid hijack by creating a new one
            owned_by_other = db.execute(
                "SELECT 1 FROM sessions WHERE session_id = ? AND user_id != ?",
                (session_id, user_id),
            ).fetchone()
            if owned_by_other:
                session_id = str(uuid.uuid4())

            db.execute(
                "INSERT OR IGNORE INTO sessions (session_id, created_at, user_id) VALUES (?, ?, ?)",
                (session_id, datetime.now(timezone.utc).isoformat(), user_id),
            )
    return session_id


def load_history(user_id: str, session_id: str) -> list[BaseMessage]:
    with _conn() as db:
        rows = db.execute(
            "SELECT role, content FROM messages WHERE session_id = ? AND user_id = ? ORDER BY id",
            (session_id, user_id),
        ).fetchall()

    messages: list[BaseMessage] = []
    for row in rows:
        if row["role"] == "user":
            messages.append(HumanMessage(content=row["content"]))
        else:
            messages.append(AIMessage(content=row["content"]))
    return messages


def save_turn(user_id: str, session_id: str, question: str, answer: str):
    ts = datetime.now(timezone.utc).isoformat()
    with _conn() as db:
        db.execute(
            "INSERT INTO messages (session_id, role, content, timestamp, user_id) VALUES (?, ?, ?, ?, ?)",
            (session_id, "user", question, ts, user_id),
        )
        db.execute(
            "INSERT INTO messages (session_id, role, content, timestamp, user_id) VALUES (?, ?, ?, ?, ?)",
            (session_id, "assistant", answer, ts, user_id),
        )


def update_user_profile(user_id: str, session_id: str, new_sources: list[str]):
    ts = datetime.now(timezone.utc).isoformat()
    with _conn() as db:
        existing = db.execute(
            "SELECT sources_accessed, query_count FROM user_profiles WHERE session_id = ? AND user_id = ?",
            (session_id, user_id),
        ).fetchone()

        if existing:
            sources = list(set(json.loads(existing["sources_accessed"]) + new_sources))
            db.execute(
                "UPDATE user_profiles SET sources_accessed=?, query_count=?, updated_at=? WHERE session_id=? AND user_id=?",
                (json.dumps(sources), existing["query_count"] + 1, ts, session_id, user_id),
            )
        else:
            db.execute(
                "INSERT INTO user_profiles (session_id, sources_accessed, query_count, updated_at, user_id) VALUES (?,?,?,?,?)",
                (session_id, json.dumps(list(set(new_sources))), 1, ts, user_id),
            )


def get_user_profile(user_id: str, session_id: str) -> dict:
    with _conn() as db:
        row = db.execute(
            "SELECT sources_accessed, query_count, updated_at FROM user_profiles WHERE session_id=? AND user_id=?",
            (session_id, user_id),
        ).fetchone()

    if row:
        return {
            "session_id": session_id,
            "sources_accessed": json.loads(row["sources_accessed"]),
            "query_count": row["query_count"],
            "updated_at": row["updated_at"],
        }
    return {
        "session_id": session_id,
        "sources_accessed": [],
        "query_count": 0,
        "updated_at": None,
    }


def list_sessions(user_id: str) -> list[dict]:
    with _conn() as db:
        rows = db.execute(
            """
            SELECT
                s.session_id,
                s.created_at,
                COUNT(m.id) AS message_count,
                MIN(CASE WHEN m.role='user' THEN m.content END) AS first_message,
                MAX(m.timestamp) AS last_active
            FROM sessions s
            LEFT JOIN messages m ON m.session_id = s.session_id AND m.user_id = s.user_id
            WHERE s.user_id = ?
            GROUP BY s.session_id
            ORDER BY last_active DESC
            """,
            (user_id,),
        ).fetchall()

    return [
        {
            "session_id": r["session_id"],
            "created_at": r["created_at"],
            "message_count": r["message_count"] or 0,
            "first_message": r["first_message"] or "",
            "last_active": r["last_active"] or r["created_at"],
        }
        for r in rows
    ]


def delete_session(user_id: str, session_id: str):
    with _conn() as db:
        db.execute("DELETE FROM message_feedback WHERE session_id = ? AND user_id = ?", (session_id, user_id))
        db.execute("DELETE FROM messages WHERE session_id = ? AND user_id = ?", (session_id, user_id))
        db.execute("DELETE FROM user_profiles WHERE session_id = ? AND user_id = ?", (session_id, user_id))
        db.execute("DELETE FROM sessions WHERE session_id = ? AND user_id = ?", (session_id, user_id))


def save_feedback(user_id: str, session_id: str, answer: str, vote: str):
    ts = datetime.now(timezone.utc).isoformat()
    with _conn() as db:
        db.execute(
            "INSERT INTO message_feedback (user_id, session_id, answer, vote, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, session_id, answer[:4000], vote, ts),
        )
