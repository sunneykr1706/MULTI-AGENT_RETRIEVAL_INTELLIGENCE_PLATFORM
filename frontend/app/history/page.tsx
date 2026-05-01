"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { fetchSessions, fetchHistory, deleteSession } from "../../lib/api";
import type { SessionSummary, HistoryTurn } from "@/lib/types";

const SESSION_KEY = "rag_session_id";
const PIN_KEY = "rag_pinned_sessions";

function timeAgo(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime();
  const m = Math.floor(ms / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  return `${d}d ago`;
}

export default function HistoryPage() {
  const router = useRouter();
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [turns, setTurns] = useState<Record<string, HistoryTurn[]>>({});
  const [loadingTurns, setLoadingTurns] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [pinned, setPinned] = useState<string[]>([]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchSessions();
      setSessions(data.sessions);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load sessions");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    const raw = localStorage.getItem(PIN_KEY);
    if (!raw) return;
    try {
      const ids = JSON.parse(raw);
      if (Array.isArray(ids)) setPinned(ids);
    } catch {
      // ignore corrupted local storage value
    }
  }, []);

  const togglePin = (sid: string) => {
    setPinned((prev) => {
      const next = prev.includes(sid) ? prev.filter((x) => x !== sid) : [sid, ...prev];
      localStorage.setItem(PIN_KEY, JSON.stringify(next));
      return next;
    });
  };

  const toggleExpand = async (sid: string) => {
    if (expanded === sid) { setExpanded(null); return; }
    setExpanded(sid);
    if (turns[sid]) return;
    setLoadingTurns(sid);
    try {
      const data = await fetchHistory(sid);
      setTurns((prev) => ({ ...prev, [sid]: data.turns }));
    } catch {
      setTurns((prev) => ({ ...prev, [sid]: [] }));
    } finally {
      setLoadingTurns(null);
    }
  };

  const handleResume = (sid: string) => {
    localStorage.setItem(SESSION_KEY, sid);
    router.push("/chat");
  };

  const handleDelete = async (sid: string) => {
    if (!confirm("Delete this conversation permanently?")) return;
    setDeletingId(sid);
    try {
      await deleteSession(sid);
      setSessions((prev) => prev.filter((s) => s.session_id !== sid));
      setPinned((prev) => {
        const next = prev.filter((x) => x !== sid);
        localStorage.setItem(PIN_KEY, JSON.stringify(next));
        return next;
      });
      setTurns((prev) => { const n = { ...prev }; delete n[sid]; return n; });
      if (expanded === sid) setExpanded(null);
    } catch {
      alert("Failed to delete session.");
    } finally {
      setDeletingId(null);
    }
  };

  const visibleSessions = [...sessions]
    .filter((s) => {
      const q = query.trim().toLowerCase();
      if (!q) return true;
      return (
        s.session_id.toLowerCase().includes(q) ||
        s.first_message.toLowerCase().includes(q)
      );
    })
    .sort((a, b) => {
      const ap = pinned.includes(a.session_id) ? 1 : 0;
      const bp = pinned.includes(b.session_id) ? 1 : 0;
      if (ap !== bp) return bp - ap;
      return (new Date(b.last_active).getTime() - new Date(a.last_active).getTime());
    });

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <header
        className="flex items-center justify-between px-6 py-4 border-b shrink-0"
        style={{ borderColor: "var(--border)", background: "var(--sidebar-bg)" }}
      >
        <div>
          <h1 className="text-base font-semibold" style={{ color: "var(--foreground)" }}>
            Chat History
          </h1>
          <p className="text-xs mt-0.5" style={{ color: "var(--muted)" }}>
            {sessions.length} saved conversation{sessions.length !== 1 ? "s" : ""}
          </p>
        </div>
        <button
          onClick={load}
          className="text-xs px-3 py-1.5 rounded-lg border transition-colors cursor-pointer"
          style={{ borderColor: "var(--border)", color: "var(--muted)", background: "transparent" }}
        >
          ↺ Refresh
        </button>
      </header>

      {/* Body */}
      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-3">
        <div className="rounded-xl border px-3 py-2" style={{ borderColor: "var(--border)", background: "var(--card-bg)" }}>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by message or session id..."
            className="w-full text-sm bg-transparent outline-none"
            style={{ color: "var(--foreground)" }}
          />
        </div>

        {loading && (
          <div className="flex items-center justify-center h-40">
            <div className="flex gap-1.5">
              {[0, 1, 2].map((i) => (
                <span
                  key={i}
                  className="w-2 h-2 rounded-full typing-dot"
                  style={{ background: "var(--accent)", animationDelay: `${i * 0.2}s` }}
                />
              ))}
            </div>
          </div>
        )}

        {error && (
          <div
            className="text-sm px-4 py-3 rounded-lg border"
            style={{ background: "#ef444420", borderColor: "#ef4444", color: "#ef4444" }}
          >
            ⚠️ {error}
          </div>
        )}

        {!loading && !error && sessions.length === 0 && (
          <div className="flex flex-col items-center justify-center h-60 gap-3 text-center">
            <span className="text-4xl">💬</span>
            <p className="text-sm" style={{ color: "var(--muted)" }}>
              No conversations yet. Start a chat and it will appear here.
            </p>
          </div>
        )}

        {visibleSessions.map((s) => {
          const isOpen = expanded === s.session_id;
          const isPinned = pinned.includes(s.session_id);

          return (
            <div
              key={s.session_id}
              className="rounded-xl border overflow-hidden transition-all"
              style={{ borderColor: isOpen ? "var(--accent)" : "var(--border)", background: "var(--card-bg)" }}
            >
              {/* Session row */}
              <div
                className="flex items-center gap-3 px-4 py-3 cursor-pointer"
                onClick={() => toggleExpand(s.session_id)}
              >
                {/* Icon */}
                <div
                  className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 text-sm"
                  style={{ background: "var(--accent)" + "22", color: "var(--accent)" }}
                >
                  💬
                </div>

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <p
                    className="text-sm font-medium truncate"
                    style={{ color: "var(--foreground)" }}
                  >
                    {s.first_message
                      ? s.first_message.slice(0, 80) + (s.first_message.length > 80 ? "…" : "")
                      : "Empty session"}
                  </p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-xs font-mono" style={{ color: "var(--muted)" }}>
                      {s.session_id.slice(0, 8)}…
                    </span>
                    <span className="text-[10px]" style={{ color: "var(--border)" }}>·</span>
                    <span className="text-xs" style={{ color: "var(--muted)" }}>
                      {s.message_count} message{s.message_count !== 1 ? "s" : ""}
                    </span>
                    <span className="text-[10px]" style={{ color: "var(--border)" }}>·</span>
                    <span className="text-xs" style={{ color: "var(--muted)" }}>
                      {timeAgo(s.last_active)}
                    </span>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-1.5 shrink-0" onClick={(e) => e.stopPropagation()}>
                  <button
                    onClick={() => togglePin(s.session_id)}
                    className="text-xs px-2 py-1 rounded-lg border transition-colors cursor-pointer"
                    style={{
                      borderColor: isPinned ? "#f59e0b" : "var(--border)",
                      color: isPinned ? "#f59e0b" : "var(--muted)",
                      background: isPinned ? "#f59e0b22" : "transparent",
                    }}
                  >
                    {isPinned ? "★" : "☆"}
                  </button>
                  <button
                    onClick={() => handleResume(s.session_id)}
                    className="text-xs px-2.5 py-1 rounded-lg border transition-colors cursor-pointer"
                    style={{
                      borderColor: "var(--accent)",
                      color: "var(--accent)",
                      background: "var(--accent)" + "11",
                    }}
                  >
                    Resume →
                  </button>
                  <button
                    onClick={() => handleDelete(s.session_id)}
                    disabled={deletingId === s.session_id}
                    className="text-xs px-2 py-1 rounded-lg border transition-colors cursor-pointer disabled:opacity-40"
                    style={{
                      borderColor: "var(--border)",
                      color: "#ef4444",
                      background: "transparent",
                    }}
                  >
                    {deletingId === s.session_id ? "…" : "🗑"}
                  </button>
                </div>

                {/* Chevron */}
                <span
                  className="text-xs transition-transform duration-200"
                  style={{
                    color: "var(--muted)",
                    transform: isOpen ? "rotate(90deg)" : "rotate(0deg)",
                    display: "inline-block",
                  }}
                >
                  ›
                </span>
              </div>

              {/* Expanded transcript */}
              {isOpen && (
                <div
                  className="border-t px-4 py-3 space-y-2.5 max-h-72 overflow-y-auto"
                  style={{ borderColor: "var(--border)" }}
                >
                  {loadingTurns === s.session_id ? (
                    <p className="text-xs text-center py-4" style={{ color: "var(--muted)" }}>
                      Loading…
                    </p>
                  ) : (turns[s.session_id] ?? []).length === 0 ? (
                    <p className="text-xs text-center py-4" style={{ color: "var(--muted)" }}>
                      No messages found.
                    </p>
                  ) : (
                    (turns[s.session_id] ?? []).map((t, i) => (
                      <div
                        key={i}
                        className={`flex gap-2 ${t.role === "user" ? "justify-end" : "justify-start"}`}
                      >
                        <div
                          className="max-w-[85%] rounded-xl px-3 py-2 text-xs leading-relaxed"
                          style={{
                            background:
                              t.role === "user"
                                ? "var(--user-bubble)"
                                : "var(--sidebar-bg)",
                            color:
                              t.role === "user" ? "#ffffff" : "var(--foreground)",
                            border:
                              t.role === "user" ? "none" : "1px solid var(--border)",
                          }}
                        >
                          <span
                            className="block text-[10px] font-semibold mb-0.5 uppercase tracking-wide"
                            style={{
                              color: t.role === "user" ? "rgba(255,255,255,0.7)" : "var(--muted)",
                            }}
                          >
                            {t.role === "user" ? "You" : "Agent"}
                          </span>
                          {t.content.slice(0, 400)}
                          {t.content.length > 400 && "…"}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
