"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { sendMessage, sendMessageStream, fetchHistory, submitFeedback, fetchToolConfig } from "../../lib/api";
import type { ChatMessage } from "@/lib/types";
import ChatMessageComponent from "@/components/ChatMessage";
import TypingIndicator from "@/components/TypingIndicator";
import ToolBar from "@/components/ToolBar";

const SESSION_KEY = "rag_session_id";
const ACTIVE_PROVIDER_KEY = "rag_active_provider";

function newId() {
  return Math.random().toString(36).slice(2);
}

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [selectedTool, setSelectedTool] = useState<{ id: string; label: string; color: string } | null>(null);
  const [toolConfig, setToolConfig] = useState<{ web_search: boolean; code_interpreter: boolean; email: boolean; github: boolean; calendar: boolean; image_generation: boolean } | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Load session_id from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem(SESSION_KEY);
    if (stored) setSessionId(stored);
  }, []);

  // When opening an existing session (e.g. from History → Resume), load transcript
  useEffect(() => {
    if (!sessionId) return;
    let cancelled = false;

    const loadHistory = async () => {
      setLoadingHistory(true);
      setError(null);
      try {
        const data = await fetchHistory(sessionId);
        if (cancelled) return;
        const baseTs = Date.now() - data.turns.length;
        const hydrated: ChatMessage[] = data.turns.map((turn: { role: "user" | "assistant"; content: string }, idx: number) => ({
          id: `${sessionId}-${idx}`,
          role: turn.role,
          content: turn.content,
          timestamp: baseTs + idx,
        }));
        setMessages(hydrated);
      } catch (err: unknown) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Failed to load chat history");
      } finally {
        if (!cancelled) setLoadingHistory(false);
      }
    };

    loadHistory();

    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 160) + "px";
  }, [input]);

  useEffect(() => {
    let mounted = true;
    fetchToolConfig()
      .then((cfg: { web_search: boolean; code_interpreter: boolean; email: boolean; github: boolean; calendar: boolean; image_generation: boolean }) => {
        if (mounted) setToolConfig(cfg);
      })
      .catch(() => {
        if (mounted) setToolConfig(null);
      });
    return () => {
      mounted = false;
    };
  }, []);

  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || loading || loadingHistory) return;

    const userMsg: ChatMessage = {
      id: newId(),
      role: "user",
      content: text,
      timestamp: Date.now(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);
    setError(null);

    try {
      let streamedAnswer = "";
      const data = await sendMessageStream(
        text,
        sessionId,
        selectedTool?.id,
        (chunk: string) => {
          streamedAnswer += chunk;
        },
      );

      // Persist the session_id returned by the backend
      if (data.session_id && data.session_id !== sessionId) {
        setSessionId(data.session_id);
        localStorage.setItem(SESSION_KEY, data.session_id);
      }

      const assistantMsg: ChatMessage = {
        id: newId(),
        role: "assistant",
        content: streamedAnswer || data.answer,
        sources: data.sources,
        provider_used: data.provider_used,
        validation_passed: data.validation_passed,
        validation_note: data.validation_note,
        tool_used: data.tool_used,
        needs_summary: data.needs_summary,
        fallback_used: data.fallback_used,
        fallback_note: data.fallback_note,
        timestamp: Date.now() + 1,
      };
      setMessages((prev) => [...prev, assistantMsg]);
      if (data.provider_used) {
        localStorage.setItem(ACTIVE_PROVIDER_KEY, data.provider_used);
        window.dispatchEvent(new Event("rag:provider-change"));
      }
    } catch (err: unknown) {
      // Fallback to non-stream endpoint if streaming fails
      try {
        const data = await sendMessage(text, sessionId, selectedTool?.id);

        if (data.session_id && data.session_id !== sessionId) {
          setSessionId(data.session_id);
          localStorage.setItem(SESSION_KEY, data.session_id);
        }

        const assistantMsg: ChatMessage = {
          id: newId(),
          role: "assistant",
          content: data.answer,
          sources: data.sources,
          provider_used: data.provider_used,
          validation_passed: data.validation_passed,
          validation_note: data.validation_note,
          tool_used: data.tool_used,
          needs_summary: data.needs_summary,
          fallback_used: data.fallback_used,
          fallback_note: data.fallback_note,
          timestamp: Date.now() + 1,
        };
        setMessages((prev) => [...prev, assistantMsg]);
        if (data.provider_used) {
          localStorage.setItem(ACTIVE_PROVIDER_KEY, data.provider_used);
          window.dispatchEvent(new Event("rag:provider-change"));
        }
      } catch (fallbackErr: unknown) {
        setError(
          fallbackErr instanceof Error
            ? fallbackErr.message
            : err instanceof Error
              ? err.message
              : "Unknown error",
        );
      }
    } finally {
      setLoading(false);
    }
  }, [input, loading, loadingHistory, sessionId, selectedTool]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleNewChat = () => {
    setMessages([]);
    setSessionId(null);
    setSelectedTool(null);
    setError(null);
    localStorage.removeItem(SESSION_KEY);
  };

  // Last tool used — for highlighting the active tool pill
  const lastAssistantMsg = [...messages].reverse().find((m) => m.role === "assistant");
  const lastToolUsed = lastAssistantMsg?.tool_used ?? null;

  const handleToolSelect = (toolId: string, toolLabel: string, starterPrompt: string, color: string) => {
    if (selectedTool?.id === toolId) {
      setSelectedTool(null);
      return;
    }
    setSelectedTool({ id: toolId, label: toolLabel, color });
    setInput(starterPrompt);
    setTimeout(() => {
      textareaRef.current?.focus();
      const len = starterPrompt.length;
      textareaRef.current?.setSelectionRange(len, len);
    }, 0);
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <header
        className="flex items-center justify-between px-6 py-4 border-b shrink-0"
        style={{ borderColor: "var(--border)", background: "var(--sidebar-bg)" }}
      >
        <div>
          <h1 className="text-base font-semibold" style={{ color: "var(--foreground)" }}>
            Chat
          </h1>
          {sessionId && (
            <p className="text-xs mt-0.5 font-mono" style={{ color: "var(--muted)" }}>
              Session: {sessionId.slice(0, 8)}…
            </p>
          )}
        </div>
        <button
          onClick={handleNewChat}
          className="text-xs px-3 py-1.5 rounded-lg border transition-colors cursor-pointer"
          style={{
            borderColor: "var(--border)",
            color: "var(--muted)",
            background: "transparent",
          }}
        >
          + New Chat
        </button>
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-5">
        {messages.length === 0 && !loading && !loadingHistory && (
          <div className="flex flex-col items-center justify-center h-full gap-4 text-center">
            <div
              className="w-14 h-14 rounded-2xl flex items-center justify-center text-2xl"
              style={{ background: "var(--card-bg)", border: "1px solid var(--border)" }}
            >
              🤖
            </div>
            <div>
              <p className="text-base font-medium" style={{ color: "var(--foreground)" }}>
                Ask anything
              </p>
              <p className="text-sm mt-1" style={{ color: "var(--muted)" }}>
                Search your documents, run code, or look up current info on the web.
              </p>
            </div>
            <div className="flex flex-wrap gap-2 justify-center mt-2">
              {[
                "Summarise the uploaded documents",
                "Calculate compound interest for 5% over 10 years",
                "What is the latest news about AI?",
              ].map((s) => (
                <button
                  key={s}
                  onClick={() => setInput(s)}
                  className="text-xs px-3 py-1.5 rounded-full border cursor-pointer transition-colors"
                  style={{
                    borderColor: "var(--border)",
                    color: "var(--muted)",
                    background: "var(--card-bg)",
                  }}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, idx) => (
          <ChatMessageComponent
            key={msg.id}
            message={msg}
            hideMeta={loading && msg.role === "assistant" && idx === messages.length - 1}
            onFeedback={
              msg.role === "assistant" && sessionId
                ? async (vote) => {
                    try {
                      await submitFeedback(sessionId, msg.content, vote);
                    } catch {
                      // ignore feedback save failure in UI
                    }
                  }
                : undefined
            }
            onRegenerate={
              msg.role === "assistant"
                ? () => {
                    const prevUser = [...messages.slice(0, idx)]
                      .reverse()
                      .find((m) => m.role === "user");
                    if (!prevUser) return;
                    setInput(prevUser.content);
                    setTimeout(() => textareaRef.current?.focus(), 0);
                  }
                : undefined
            }
          />
        ))}

        {(loading || loadingHistory) && <TypingIndicator />}

        {error && (
          <div
            className="text-sm px-4 py-3 rounded-lg border"
            style={{
              background: "#ef444420",
              borderColor: "#ef4444",
              color: "#ef4444",
            }}
          >
            ⚠️ {error}
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div
        className="shrink-0 px-6 py-4 border-t"
        style={{ borderColor: "var(--border)", background: "var(--sidebar-bg)" }}
      >
        {/* Tool selection bar */}
        <div className="mb-3">
          <ToolBar onToolSelect={handleToolSelect} activeTool={selectedTool?.id ?? lastToolUsed} toolConfig={toolConfig} />
        </div>

        <div
          className="flex items-end gap-3 rounded-xl border px-4 py-3"
          style={{ borderColor: "var(--border)", background: "var(--card-bg)" }}
        >
          <textarea
            ref={textareaRef}
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question… (Shift+Enter for newline)"
            disabled={loading || loadingHistory}
            className="flex-1 resize-none bg-transparent text-sm outline-none leading-relaxed"
            style={{
              color: "var(--foreground)",
              minHeight: "24px",
            }}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || loading || loadingHistory}
            className="shrink-0 w-8 h-8 rounded-lg flex items-center justify-center transition-all cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
            style={{ background: "var(--accent)" }}
          >
            <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 12 3.269 3.125A59.769 59.769 0 0 1 21.485 12 59.768 59.768 0 0 1 3.27 20.875L5.999 12Zm0 0h7.5" />
            </svg>
          </button>
        </div>
        
      </div>
    </div>
  );
}
