import type {
  AgentChatResponse,
  AuthResponse,
  HistoryResponse,
  SessionsResponse,
  ToolConfigResponse,
  UploadResponse,
  UserProfile,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const ACCESS_KEY = "rag_access_token";
const REFRESH_KEY = "rag_refresh_token";
const USER_KEY = "rag_user";

function isBrowser() {
  return typeof window !== "undefined";
}

export function getAccessToken(): string | null {
  if (!isBrowser()) return null;
  return localStorage.getItem(ACCESS_KEY);
}

export function getRefreshToken(): string | null {
  if (!isBrowser()) return null;
  return localStorage.getItem(REFRESH_KEY);
}

export function getStoredUser(): { user_id: string; email: string; name: string } | null {
  if (!isBrowser()) return null;
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function clearAuth() {
  if (!isBrowser()) return;
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
  localStorage.removeItem(USER_KEY);
}

function saveAuth(data: AuthResponse) {
  if (!isBrowser()) return;
  localStorage.setItem(ACCESS_KEY, data.access_token);
  localStorage.setItem(REFRESH_KEY, data.refresh_token);
  localStorage.setItem(USER_KEY, JSON.stringify(data.user));
}

async function refreshAccessToken(): Promise<string | null> {
  const refresh = getRefreshToken();
  if (!refresh) return null;

  const res = await fetch(`${BASE}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refresh }),
  });

  if (!res.ok) {
    clearAuth();
    return null;
  }

  const data: AuthResponse = await res.json();
  saveAuth(data);
  return data.access_token;
}

async function authFetch(input: string, init: RequestInit = {}, retry = true): Promise<Response> {
  const token = getAccessToken();
  const headers = new Headers(init.headers || {});
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(input, { ...init, headers });
  if (res.status !== 401 || !retry) return res;

  const newToken = await refreshAccessToken();
  if (!newToken) return res;

  const retryHeaders = new Headers(init.headers || {});
  retryHeaders.set("Authorization", `Bearer ${newToken}`);
  return fetch(input, { ...init, headers: retryHeaders });
}

// ── Auth ───────────────────────────────────────────────────────────────────────

export async function register(email: string, password: string, name: string): Promise<AuthResponse> {
  const res = await fetch(`${BASE}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, name }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }
  const data: AuthResponse = await res.json();
  saveAuth(data);
  return data;
}

export async function login(email: string, password: string): Promise<AuthResponse> {
  const res = await fetch(`${BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }
  const data: AuthResponse = await res.json();
  saveAuth(data);
  return data;
}

export async function fetchMe() {
  const res = await authFetch(`${BASE}/auth/me`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// ── Chat ───────────────────────────────────────────────────────────────────────

export async function sendMessage(
  message: string,
  sessionId: string | null,
  selectedTool?: string | null,
): Promise<AgentChatResponse> {
  const res = await authFetch(`${BASE}/agent/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId, selected_tool: selectedTool ?? "auto" }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }
  return res.json();
}

export async function sendMessageStream(
  message: string,
  sessionId: string | null,
  selectedTool: string | null | undefined,
  onChunk: (chunk: string) => void,
): Promise<AgentChatResponse> {
  const token = getAccessToken();
  const headers = new Headers({ "Content-Type": "application/json" });
  if (token) headers.set("Authorization", `Bearer ${token}`);

  let res = await fetch(`${BASE}/agent/chat/stream`, {
    method: "POST",
    headers,
    body: JSON.stringify({ message, session_id: sessionId, selected_tool: selectedTool ?? "auto" }),
  });

  if (res.status === 401) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      headers.set("Authorization", `Bearer ${newToken}`);
      res = await fetch(`${BASE}/agent/chat/stream`, {
        method: "POST",
        headers,
        body: JSON.stringify({ message, session_id: sessionId, selected_tool: selectedTool ?? "auto" }),
      });
    }
  }

  if (!res.ok || !res.body) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finalData: AgentChatResponse | null = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split("\n\n");
    buffer = events.pop() ?? "";

    for (const evt of events) {
      const line = evt.split("\n").find((l) => l.startsWith("data:"));
      if (!line) continue;

      try {
        const payload = JSON.parse(line.slice(5).trim());
        if (payload.type === "chunk" && typeof payload.content === "string") {
          onChunk(payload.content);
        }
        if (payload.type === "final" && payload.data) {
          finalData = payload.data as AgentChatResponse;
        }
      } catch {
        // ignore malformed chunk
      }
    }
  }

  if (!finalData) {
    throw new Error("Stream ended without final payload");
  }

  return finalData;
}

// ── History ────────────────────────────────────────────────────────────────────

export async function fetchHistory(sessionId: string): Promise<HistoryResponse> {
  const res = await authFetch(`${BASE}/agent/history/${sessionId}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchProfile(sessionId: string): Promise<UserProfile> {
  const res = await authFetch(`${BASE}/agent/profile/${sessionId}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchSessions(): Promise<SessionsResponse> {
  const res = await authFetch(`${BASE}/agent/sessions`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function deleteSession(sessionId: string): Promise<void> {
  const res = await authFetch(`${BASE}/agent/sessions/${sessionId}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
}

export async function submitFeedback(sessionId: string, answer: string, vote: "up" | "down"): Promise<void> {
  const res = await authFetch(`${BASE}/agent/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, answer, vote }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
}

export async function fetchToolConfig(): Promise<ToolConfigResponse> {
  const res = await authFetch(`${BASE}/agent/tool-config`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// ── Document upload ────────────────────────────────────────────────────────────

export async function uploadDocument(file: File): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);

  const token = getAccessToken();
  const headers = new Headers();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  let res = await fetch(`${BASE}/documents/upload`, {
    method: "POST",
    body: form,
    headers,
  });

  if (res.status === 401) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      headers.set("Authorization", `Bearer ${newToken}`);
      res = await fetch(`${BASE}/documents/upload`, {
        method: "POST",
        body: form,
        headers,
      });
    }
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }
  return res.json();
}

// ── Health ─────────────────────────────────────────────────────────────────────

export async function checkHealth(): Promise<{ status: string; version: string }> {
  const res = await fetch(`${BASE}/health`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
