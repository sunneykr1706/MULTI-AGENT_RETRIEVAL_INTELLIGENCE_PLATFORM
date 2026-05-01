"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { login } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await login(email, password);
      router.replace("/chat");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-full flex items-center justify-center px-4">
      <form
        onSubmit={onSubmit}
        className="w-full max-w-md rounded-2xl border p-6 space-y-4"
        style={{ background: "var(--card-bg)", borderColor: "var(--border)" }}
      >
        <div className="text-center">
          <p className="text-2xl">🤖</p>
          <h1 className="text-lg font-semibold mt-1">Welcome back</h1>
          <p className="text-xs mt-1" style={{ color: "var(--muted)" }}>
            Sign in to access your chats and memory.
          </p>
        </div>

        {error && (
          <div className="text-sm px-3 py-2 rounded-lg border" style={{ borderColor: "#ef4444", color: "#ef4444", background: "#ef444420" }}>
            {error}
          </div>
        )}

        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="Email"
          required
          className="w-full rounded-lg border px-3 py-2 text-sm outline-none"
          style={{ background: "var(--sidebar-bg)", borderColor: "var(--border)", color: "var(--foreground)" }}
        />

        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Password"
          required
          className="w-full rounded-lg border px-3 py-2 text-sm outline-none"
          style={{ background: "var(--sidebar-bg)", borderColor: "var(--border)", color: "var(--foreground)" }}
        />

        <button
          disabled={loading}
          className="w-full rounded-lg py-2 text-sm font-medium disabled:opacity-50"
          style={{ background: "var(--accent)", color: "white" }}
        >
          {loading ? "Signing in..." : "Sign in"}
        </button>

        <p className="text-xs text-center" style={{ color: "var(--muted)" }}>
          New user? <Link href="/register" style={{ color: "var(--accent)" }}>Create account</Link>
        </p>
      </form>
    </div>
  );
}
