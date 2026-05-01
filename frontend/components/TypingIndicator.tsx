export default function TypingIndicator() {
  return (
    <div className="flex justify-start msg-enter">
      <div className="max-w-[80%] flex flex-col gap-1 items-start">
        <span className="text-xs px-1" style={{ color: "var(--muted)" }}>
          Agent
        </span>
        <div
          className="px-4 py-3 rounded-2xl flex items-center gap-1.5"
          style={{
            background: "var(--assistant-bubble)",
            border: "1px solid var(--border)",
            borderBottomLeftRadius: 4,
          }}
        >
          <span className="w-2 h-2 rounded-full typing-dot" style={{ background: "var(--muted)" }} />
          <span className="w-2 h-2 rounded-full typing-dot" style={{ background: "var(--muted)" }} />
          <span className="w-2 h-2 rounded-full typing-dot" style={{ background: "var(--muted)" }} />
        </div>
      </div>
    </div>
  );
}
