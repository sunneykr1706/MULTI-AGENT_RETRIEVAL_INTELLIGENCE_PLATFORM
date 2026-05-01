// ── API response types ─────────────────────────────────────────────────────────

export interface Source {
  source: string;
  chunk_index: number;
  preview: string;
}

export interface AgentChatResponse {
  answer: string;
  sources: Source[];
  provider_used: string;
  validation_passed: boolean;
  validation_note: string;
  needs_summary: boolean;
  session_id: string;
  tool_used: string;
  fallback_used: boolean;
  fallback_note: string;
}

export interface HistoryTurn {
  role: "user" | "assistant";
  content: string;
}

export interface HistoryResponse {
  session_id: string;
  turns: HistoryTurn[];
}

export interface UserProfile {
  session_id: string;
  sources_accessed: string[];
  message_count: number;
}

export interface SessionSummary {
  session_id: string;
  created_at: string;
  message_count: number;
  first_message: string;
  last_active: string;
}

export interface SessionsResponse {
  sessions: SessionSummary[];
}

export interface AuthUser {
  user_id: string;
  email: string;
  name: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: AuthUser;
}

export interface ToolConfigResponse {
  web_search: boolean;
  code_interpreter: boolean;
  email: boolean;
  github: boolean;
  calendar: boolean;
  image_generation: boolean;
}

export interface UploadResponse {
  filename: string;
  chunks_stored: number;
  message: string;
}

// ── UI types ───────────────────────────────────────────────────────────────────

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  // metadata attached to assistant messages
  sources?: Source[];
  provider_used?: string;
  validation_passed?: boolean;
  validation_note?: string;
  tool_used?: string;
  needs_summary?: boolean;
  fallback_used?: boolean;
  fallback_note?: string;
  timestamp: number;
}
