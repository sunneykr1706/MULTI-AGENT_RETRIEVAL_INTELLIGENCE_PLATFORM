"use client";

import type { ChatMessage } from "@/lib/types";

interface Props {
  message: ChatMessage;
}

const TOOL_LABELS: Record<string, string> = {
  web_search: "Web Search",
  code_interpreter: "Code Interpreter",
  email: "Email",
  github: "GitHub Issue",
  calendar: "Calendar",
  image_generation: "Image Generation",
  none: "RAG",
};

const TOOL_COLORS: Record<string, string> = {
  web_search: "#f59e0b",
  code_interpreter: "#10b981",
  email: "#3b82f6",
  github: "#8b5cf6",
  calendar: "#ec4899",
  image_generation: "#f43f5e",
  none: "#6366f1",
};

function Badge({
  label,
  color,
  icon,
}: {
  label: string;
  color: string;
  icon: React.ReactNode;
}) {
  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium"
      style={{ background: `${color}22`, color }}
    >
      {icon}
      {label}
    </span>
  );
}

export default function AgentTrace({ message }: Props) {
  const { tool_used, provider_used, validation_passed, validation_note, sources, needs_summary, fallback_used, fallback_note } =
    message;

  if (!tool_used) return null;

  const toolLabel = TOOL_LABELS[tool_used ?? "none"] ?? tool_used;
  const toolColor = TOOL_COLORS[tool_used ?? "none"] ?? "#6366f1";
  const confidence = validation_passed ? "High" : "Needs review";

  return (
    <div
      className="mt-2 rounded-lg p-3 text-xs space-y-2 border"
      style={{
        background: "#0f1117",
        borderColor: "var(--border)",
        color: "var(--muted)",
      }}
    >
      {/* Agent pipeline badges */}
      <div className="flex flex-wrap gap-1.5 items-center">
        <span style={{ color: "var(--muted)" }}>Pipeline:</span>

        {/* memory_load */}
        <Badge label="Memory" color="#64748b" icon={<span>💾</span>} />
        <span style={{ color: "var(--border)" }}>→</span>

        {/* retrieval */}
        <Badge label="Retrieval" color="#6366f1" icon={<span>🔍</span>} />
        <span style={{ color: "var(--border)" }}>→</span>

        {/* tool or summary or direct llm */}
        {tool_used !== "none" ? (
          <Badge label={toolLabel} color={toolColor} icon={<span>⚡</span>} />
        ) : needs_summary ? (
          <Badge label="Summary" color="#f59e0b" icon={<span>📝</span>} />
        ) : null}
        {(tool_used !== "none" || needs_summary) && (
          <span style={{ color: "var(--border)" }}>→</span>
        )}

        {/* llm */}
        <Badge label="LLM" color="#10b981" icon={<span>🤖</span>} />
        <span style={{ color: "var(--border)" }}>→</span>

        {/* validator */}
        <Badge
          label={validation_passed ? "Validated ✓" : "Validation ✗"}
          color={validation_passed ? "#10b981" : "#ef4444"}
          icon={<span>{validation_passed ? "✅" : "⚠️"}</span>}
        />
        {fallback_used && (
          <>
            <span style={{ color: "var(--border)" }}>→</span>
            <Badge
              label="Fallback Used"
              color="#f59e0b"
              icon={<span>🛟</span>}
            />
          </>
        )}
        <span style={{ color: "var(--border)" }}>→</span>

        {/* memory_save */}
        <Badge label="Saved" color="#64748b" icon={<span>💾</span>} />
      </div>

      {/* Meta row */}
      <div className="flex flex-wrap gap-3 pt-1" style={{ borderTop: "1px solid var(--border)" }}>
        {provider_used && (
          <span>
            Provider: <span className="text-white">{provider_used}</span>
          </span>
        )}
        {sources && sources.length > 0 && (
          <span>
            Sources: <span className="text-white">{sources.length} chunk{sources.length !== 1 ? "s" : ""}</span>
          </span>
        )}
        {validation_note && (
          <span className="truncate max-w-xs" title={validation_note}>
            Validator: <span className="text-white">{validation_note.slice(0, 60)}{validation_note.length > 60 ? "…" : ""}</span>
          </span>
        )}
        {fallback_used && fallback_note && (
          <span className="truncate max-w-xs" title={fallback_note}>
            Fallback: <span className="text-white">{fallback_note.slice(0, 60)}{fallback_note.length > 60 ? "…" : ""}</span>
          </span>
        )}
        <span>
          Confidence: <span className="text-white">{confidence}</span>
        </span>
      </div>

      {/* Sources list */}
      {sources && sources.length > 0 && (
        <details className="pt-1">
          <summary
            className="cursor-pointer select-none"
            style={{ color: "var(--accent)" }}
          >
            View {sources.length} source{sources.length !== 1 ? "s" : ""}
          </summary>
          <ul className="mt-1.5 space-y-1">
            {sources.map((s, i) => (
              <li
                key={i}
                className="rounded p-2 border"
                style={{ background: "var(--card-bg)" }}
              >
                {/^https?:\/\//i.test(s.source) ? (
                  <a
                    href={s.source}
                    target="_blank"
                    rel="noreferrer"
                    className="font-medium text-white truncate underline"
                    style={{ color: "#c7d2fe" }}
                  >
                    {s.source}
                  </a>
                ) : (
                  <p className="font-medium text-white truncate">{s.source}</p>
                )}
                <p className="mt-0.5 line-clamp-2" style={{ color: "var(--muted)" }}>
                  {s.preview}
                </p>
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
