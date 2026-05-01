"use client";

import { useState } from "react";

interface Tool {
  id: string;
  label: string;
  icon: string;
  color: string;
  description: string;
  starterPrompt: string;
  triggers: string[];
  badge: string;
}

const TOOLS: Tool[] = [
  {
    id: "web_search",
    label: "Web Search",
    icon: "🌐",
    color: "#f59e0b",
    badge: "Live",
    description: "Search the web for real-time, up-to-date information — news, prices, events.",
    starterPrompt: "Search the web for: ",
    triggers: ['"latest …"', '"current news about …"', '"look up …"', '"what is happening with …"'],
  },
  {
    id: "rag",
    label: "Ask Docs",
    icon: "📚",
    color: "#6366f1",
    badge: "RAG",
    description: "Query your uploaded documents using semantic search + ChromaDB.",
    starterPrompt: "Based on my uploaded documents, ",
    triggers: ['"summarize docs …"', '"what does the document say about …"', '"find in docs: …"'],
  },
];

interface Props {
  onToolSelect: (toolId: string, toolLabel: string, prompt: string, color: string) => void;
  /** tool_used value from the last assistant message */
  activeTool?: string | null;
  toolConfig?: { web_search: boolean; code_interpreter: boolean; email: boolean; github: boolean; calendar: boolean; image_generation: boolean } | null;
}

export default function ToolBar({ onToolSelect, activeTool, toolConfig }: Props) {
  const [openTooltip, setOpenTooltip] = useState<string | null>(null);
  const [showAllMobile, setShowAllMobile] = useState(false);

  const resolvedActive =
    activeTool === "none" ? "rag" : activeTool ?? null;

  return (
    <div className="flex items-start gap-2 flex-wrap">
      {/* Label */}
      <span
        className="text-xs font-medium shrink-0 mt-1.5"
        style={{ color: "var(--muted)" }}
      >
        Tools:
      </span>

      {TOOLS.map((tool, index) => {
        const isActive = resolvedActive === tool.id;
        const isOpen = openTooltip === tool.id;
        const isHiddenOnMobile = index >= 3 && !showAllMobile;
        const isAvailable =
          tool.id === "rag"
            ? true
            : tool.id === "web_search"
              ? !!toolConfig?.web_search
              : tool.id === "code_interpreter"
                ? !!toolConfig?.code_interpreter
                : tool.id === "email"
                  ? !!toolConfig?.email
                  : tool.id === "github"
                    ? !!toolConfig?.github
                    : tool.id === "calendar"
                      ? !!toolConfig?.calendar
                      : tool.id === "image_generation"
                        ? !!toolConfig?.image_generation
                    : true;

        return (
          <div
            key={tool.id}
            className={`relative ${isHiddenOnMobile ? "hidden md:block" : ""}`}
          >
            {/* ── Tooltip ── */}
            {isOpen && (
              <div
                className="absolute bottom-full mb-2.5 left-1/2 -translate-x-1/2 z-50 w-60 rounded-xl p-3.5 shadow-2xl border text-left"
                style={{
                  background: "var(--card-bg)",
                  borderColor: tool.color + "66",
                  color: "var(--foreground)",
                  animation: "fadeSlideIn 0.15s ease-out",
                }}
              >
                {/* Tool header */}
                <div className="flex items-center justify-between mb-2">
                  <span className="font-semibold text-sm" style={{ color: tool.color }}>
                    {tool.icon} {tool.label}
                  </span>
                  <span
                    className="text-[10px] px-1.5 py-0.5 rounded-full font-medium"
                    style={{ background: tool.color + "22", color: tool.color }}
                  >
                    {tool.badge}
                  </span>
                </div>

                {/* Description */}
                <p className="text-xs leading-relaxed mb-2.5" style={{ color: "var(--muted)" }}>
                  {tool.description}
                </p>

                {!isAvailable && (
                  <p className="text-[11px] mb-2" style={{ color: "#f59e0b" }}>
                    ⚠ Not configured in backend environment.
                  </p>
                )}

                {/* Divider */}
                <div className="border-t mb-2" style={{ borderColor: "var(--border)" }} />

                {/* Trigger keywords */}
                <p className="text-[10px] uppercase tracking-wider font-semibold mb-1.5" style={{ color: "var(--muted)" }}>
                  Auto-triggered by
                </p>
                <ul className="space-y-0.5">
                  {tool.triggers.map((t) => (
                    <li
                      key={t}
                      className="text-[11px] font-mono px-2 py-0.5 rounded"
                      style={{ background: tool.color + "11", color: tool.color }}
                    >
                      {t}
                    </li>
                  ))}
                </ul>

                {/* Click hint */}
                <p
                  className="text-[10px] mt-2.5 text-center italic"
                  style={{ color: "var(--muted)" }}
                >
                  Click to insert starter prompt ↓
                </p>

                {/* Arrow pointing down */}
                <div
                  className="absolute left-1/2 -translate-x-1/2 top-full"
                  style={{
                    width: 0,
                    height: 0,
                    borderLeft: "7px solid transparent",
                    borderRight: "7px solid transparent",
                    borderTop: `7px solid ${tool.color}66`,
                  }}
                />
              </div>
            )}

            {/* ── Pill button ── */}
            <button
              type="button"
              onClick={() => {
                onToolSelect(tool.id, tool.label, tool.starterPrompt, tool.color);
                setOpenTooltip(null);
              }}
              onMouseEnter={() => setOpenTooltip(tool.id)}
              onMouseLeave={() => setOpenTooltip(null)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border transition-all cursor-pointer select-none"
              style={{
                background: isActive ? tool.color + "20" : "var(--card-bg)",
                borderColor: isActive ? tool.color : "var(--border)",
                color: !isAvailable ? "#f59e0b" : isActive ? tool.color : "var(--muted)",
                boxShadow: isActive ? `0 0 0 1px ${tool.color}44` : "none",
                opacity: isAvailable ? 1 : 0.85,
              }}
            >
              <span>{tool.icon}</span>
              {tool.label}
              {!isAvailable && <span>⚠</span>}
              {isActive && (
                <span
                  className="w-1.5 h-1.5 rounded-full"
                  style={{ background: tool.color }}
                />
              )}
            </button>
          </div>
        );
      })}

      <button
        type="button"
        onClick={() => setShowAllMobile((prev) => !prev)}
        className="md:hidden inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border transition-colors"
        style={{
          background: "var(--card-bg)",
          borderColor: "var(--border)",
          color: "var(--muted)",
        }}
      >
        <span>{showAllMobile ? "−" : "+"}</span>
        {showAllMobile ? "Less" : `More (${TOOLS.length - 3})`}
      </button>
    </div>
  );
}
