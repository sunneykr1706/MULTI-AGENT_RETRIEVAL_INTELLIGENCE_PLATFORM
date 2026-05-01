"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { clearAuth } from "@/lib/api";

const NAV = [
  {
    href: "/chat",
    label: "Chat",
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.8} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round"
          d="M8.625 12a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0ZM21 12c0 4.97-4.03 9-9 9S3 16.97 3 12 7.03 3 12 3s9 4.03 9 9Z" />
      </svg>
    ),
  },
  {
    href: "/documents",
    label: "Documents",
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.8} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round"
          d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
      </svg>
    ),
  },
  {
    href: "/history",
    label: "History",
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.8} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round"
          d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
      </svg>
    ),
  },
];

const ACTIVE_PROVIDER_KEY = "rag_active_provider";

function formatProvider(provider: string | null): { label: string; detail: string; color: string } {
  const p = (provider || "").toLowerCase().trim();
  if (!p) {
    return { label: "Auto Router", detail: "Waiting for first response", color: "#64748b" };
  }
  if (p === "google") {
    return { label: "Google Gemini", detail: "Provider active", color: "#22c55e" };
  }
  if (p === "openai") {
    return { label: "OpenAI", detail: "Provider active", color: "#38bdf8" };
  }
  if (p === "groq") {
    return { label: "Groq", detail: "Provider active", color: "#f59e0b" };
  }
  if (p === "tool") {
    return { label: "Tool Output", detail: "Bypassed LLM synthesis", color: "#f43f5e" };
  }
  return { label: provider || "Unknown", detail: "Provider active", color: "#a78bfa" };
}

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const [activeProvider, setActiveProvider] = useState<string | null>(null);

  useEffect(() => {
    const syncProvider = () => {
      const stored = localStorage.getItem(ACTIVE_PROVIDER_KEY);
      setActiveProvider(stored);
    };

    const onStorage = (event: StorageEvent) => {
      if (event.key === ACTIVE_PROVIDER_KEY) {
        syncProvider();
      }
    };

    const onProviderChange = () => syncProvider();

    syncProvider();
    window.addEventListener("storage", onStorage);
    window.addEventListener("rag:provider-change", onProviderChange as EventListener);
    return () => {
      window.removeEventListener("storage", onStorage);
      window.removeEventListener("rag:provider-change", onProviderChange as EventListener);
    };
  }, []);

  const providerInfo = useMemo(() => formatProvider(activeProvider), [activeProvider]);

  return (
    <aside
      className="w-56 flex flex-col shrink-0 border-r"
      style={{
        background: "var(--sidebar-bg)",
        borderColor: "var(--border)",
      }}
    >
      {/* Logo */}
      <div className="px-5 py-5 border-b" style={{ borderColor: "var(--border)" }}>
        <div className="flex items-center gap-2 group cursor-default">
          <div
            className="w-10 h-10 flex items-center justify-center relative select-none"
            style={{
              filter: "drop-shadow(0 6px 10px rgba(99, 102, 241, 0.35))",
            }}
            aria-label="Multi-Agent logo"
          >
            <span
              className="leading-none text-[1.7rem] transition-transform duration-300 group-hover:scale-110 group-hover:-translate-y-0.5"
              style={{
                textShadow:
                  "0 2px 0 rgba(255,255,255,0.2), 0 8px 16px rgba(0,0,0,0.45)",
              }}
            >
              🤖
            </span>
            <span
              className="absolute top-1 right-1 w-2 h-2 rounded-full transition-all duration-300 group-hover:scale-110"
              style={{
                background: "var(--accent)",
                boxShadow: "0 0 10px rgba(99, 102, 241, 0.9)",
              }}
            />
          </div>
          <div>
            <p
              className="text-sm font-black leading-tight tracking-wide"
              style={{
                background: "linear-gradient(90deg, #ffffff 0%, #c7d2fe 55%, #a5b4fc 100%)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
              }}
            >
              AI Multi-Agent
            </p>
            <p
              className="text-xs transition-colors duration-300 group-hover:text-indigo-300"
              style={{ color: "var(--muted)" }}
            >
              RAG System
            </p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3 space-y-1">
        {NAV.map(({ href, label, icon }) => {
          const active = pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors"
              style={{
                background: active ? "var(--accent)" : "transparent",
                color: active ? "#fff" : "var(--muted)",
              }}
            >
              {icon}
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t space-y-3" style={{ borderColor: "var(--border)", color: "var(--muted)" }}>
        <div
          className="rounded-xl border p-3"
          style={{
            borderColor: "var(--border)",
            background: "linear-gradient(135deg, rgba(99,102,241,0.16) 0%, rgba(15,17,23,0.2) 100%)",
          }}
        >
          <div className="flex items-center justify-between gap-2">
            <p className="text-[11px] uppercase tracking-widest" style={{ color: "#a5b4fc" }}>
              Active Model
            </p>
            <span
              className="inline-block w-2 h-2 rounded-full"
              style={{ background: providerInfo.color, boxShadow: `0 0 10px ${providerInfo.color}` }}
            />
          </div>
          <p className="text-sm font-semibold mt-1" style={{ color: "#ffffff" }}>
            {providerInfo.label}
          </p>
          <p className="text-[11px] mt-0.5" style={{ color: "var(--muted)" }}>
            {providerInfo.detail}
          </p>
        </div>

        <p className="text-xs">LangGraph • ChromaDB</p>
        <button
          onClick={() => {
            clearAuth();
            localStorage.removeItem(ACTIVE_PROVIDER_KEY);
            localStorage.removeItem("rag_session_id");
            router.replace("/login");
          }}
          className="mt-3 w-full text-xs px-2 py-1.5 rounded-md border"
          style={{ borderColor: "var(--border)", color: "var(--muted)", background: "transparent" }}
        >
          Logout
        </button>
      </div>
    </aside>
  );
}
