"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { register } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await register(email, password, name);
      router.replace("/chat");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Registration failed");
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
          <p className="text-2xl">✨</p>
          <h1 className="text-lg font-semibold mt-1">Create account</h1>
          <p className="text-xs mt-1" style={{ color: "var(--muted)" }}>
            Start secure, user-scoped chat memory.
          </p>
        </div>

        {error && (
          <div className="text-sm px-3 py-2 rounded-lg border" style={{ borderColor: "#ef4444", color: "#ef4444", background: "#ef444420" }}>
            {error}
          </div>
        )}

        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Name"
          className="w-full rounded-lg border px-3 py-2 text-sm outline-none"
          style={{ background: "var(--sidebar-bg)", borderColor: "var(--border)", color: "var(--foreground)" }}
        />

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
          placeholder="Password (min 6 chars)"
          minLength={6}
          required
          className="w-full rounded-lg border px-3 py-2 text-sm outline-none"
          style={{ background: "var(--sidebar-bg)", borderColor: "var(--border)", color: "var(--foreground)" }}
        />

        <button
          disabled={loading}
          className="w-full rounded-lg py-2 text-sm font-medium disabled:opacity-50"
          style={{ background: "var(--accent)", color: "white" }}
        >
          {loading ? "Creating..." : "Create account"}
        </button>

        <p className="text-xs text-center" style={{ color: "var(--muted)" }}>
          Already have an account? <Link href="/login" style={{ color: "var(--accent)" }}>Sign in</Link>
        </p>
      </form>
    </div>
  );
}
