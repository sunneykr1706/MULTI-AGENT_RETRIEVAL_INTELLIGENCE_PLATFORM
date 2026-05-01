"use client";

import { useState } from "react";
import type { ChatMessage as ChatMessageType } from "@/lib/types";
import AgentTrace from "./AgentTrace";

interface Props {
  message: ChatMessageType;
  onRegenerate?: () => void;
  onFeedback?: (vote: "up" | "down") => void;
  hideMeta?: boolean;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function extractGeneratedImageUrls(content: string): string[] {
  const text = content || "";
  const pathMatches = text.match(/(?:https?:\/\/[^\s)]+\/generated-images\/[^\s)]+|\/generated-images\/[^\s)]+)/gi) ?? [];
  const dataMatches = text.match(/data:image\/[a-zA-Z0-9.+-]+;base64,[A-Za-z0-9+/=]+/g) ?? [];

  const normalized = pathMatches.map((raw) => {
    const cleaned = raw.trim().replace(/["'`]+$/g, "");
    if (/^https?:\/\//i.test(cleaned)) return cleaned;
    return `${API_BASE}${cleaned}`;
  });

  return [...new Set([...normalized, ...dataMatches])];
}

function stripImagePayload(content: string): string {
  return (content || "")
    .replace(/data:image\/[a-zA-Z0-9.+-]+;base64,[A-Za-z0-9+/=]+/g, "")
    .replace(/(?:https?:\/\/[^\s)]+\/generated-images\/[^\s)]+|\/generated-images\/[^\s)]+)/gi, "")
    .trim();
}

export default function ChatMessage({ message, onRegenerate, onFeedback, hideMeta = false }: Props) {
  const isUser = message.role === "user";
  const imageUrls = !isUser ? extractGeneratedImageUrls(message.content) : [];
  const textWithoutImage = !isUser ? stripImagePayload(message.content) : message.content;
  const hasContent = (isUser ? message.content : textWithoutImage).trim().length > 0;
  const hasRenderableAssistantContent = hasContent || imageUrls.length > 0;
  const [vote, setVote] = useState<"up" | "down" | null>(null);
  const [copied, setCopied] = useState(false);

  if (!isUser && !hasRenderableAssistantContent) {
    return null;
  }

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 1200);
    } catch {
      setCopied(false);
    }
  };

  return (
    <div
      className={`flex msg-enter ${isUser ? "justify-end" : "justify-start"}`}
    >
      <div className={`max-w-[80%] ${isUser ? "items-end" : "items-start"} flex flex-col gap-1`}>
        {/* Avatar label */}
        <span className="text-xs px-1" style={{ color: "var(--muted)" }}>
          {isUser ? "You" : "Agent"}
        </span>

        {/* Bubble */}
        {hasContent && (
          <div
            className="px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap"
            style={{
              background: isUser ? "var(--user-bubble)" : "var(--assistant-bubble)",
              color: isUser ? "#fff" : "var(--foreground)",
              borderBottomRightRadius: isUser ? 4 : undefined,
              borderBottomLeftRadius: !isUser ? 4 : undefined,
              border: isUser ? "none" : "1px solid var(--border)",
            }}
          >
            {isUser ? message.content : textWithoutImage}
          </div>
        )}

        {!isUser && imageUrls.length > 0 && (
          <div className="w-full grid gap-2 mt-1">
            {imageUrls.map((url) => (
              <div
                key={url}
                className="block rounded-xl border overflow-hidden"
                style={{ borderColor: "var(--border)", background: "var(--card-bg)" }}
              >
                <img
                  src={url}
                  alt="Generated image"
                  className="w-full h-auto max-h-90 object-contain"
                  loading="lazy"
                />
              </div>
            ))}
          </div>
        )}

        {!isUser && !hideMeta && (
          <div className="flex items-center gap-1.5 px-1">
            <button
              type="button"
              onClick={handleCopy}
              className="text-[11px] px-2 py-1 rounded-md border"
              style={{ borderColor: "var(--border)", color: "var(--muted)", background: "transparent" }}
            >
              {copied ? "Copied" : "Copy"}
            </button>
            <button
              type="button"
              onClick={onRegenerate}
              className="text-[11px] px-2 py-1 rounded-md border"
              style={{ borderColor: "var(--border)", color: "var(--muted)", background: "transparent" }}
            >
              Regenerate
            </button>
            <button
              type="button"
              onClick={() => {
                const next = vote === "up" ? null : "up";
                setVote(next);
                if (next && onFeedback) onFeedback(next);
              }}
              className="text-[11px] px-2 py-1 rounded-md border"
              style={{
                borderColor: vote === "up" ? "#10b981" : "var(--border)",
                color: vote === "up" ? "#10b981" : "var(--muted)",
                background: vote === "up" ? "#10b98122" : "transparent",
              }}
            >
              👍
            </button>
            <button
              type="button"
              onClick={() => {
                const next = vote === "down" ? null : "down";
                setVote(next);
                if (next && onFeedback) onFeedback(next);
              }}
              className="text-[11px] px-2 py-1 rounded-md border"
              style={{
                borderColor: vote === "down" ? "#ef4444" : "var(--border)",
                color: vote === "down" ? "#ef4444" : "var(--muted)",
                background: vote === "down" ? "#ef444422" : "transparent",
              }}
            >
              👎
            </button>
          </div>
        )}

        {/* Agent trace — only for assistant messages */}
        {!isUser && !hideMeta && <AgentTrace message={message} />}
      </div>
    </div>
  );
}
