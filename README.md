# 🤖 Multi-Agent RAG System — v3.0

DEMO VIDEO:-

https://www.loom.com/share/55abf6f4b21a4964b963eb5b2c4bb131



A production-ready **Retrieval-Augmented Generation (RAG)** backend built with **FastAPI**, **LangGraph**, and **LangChain**, featuring persistent memory, multi-LLM provider support, and agentic action tools (web search, email, GitHub, code interpreter).

---

## 📐 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Next.js Frontend (Port 3000)                  │
└────────────────────────────────┬────────────────────────────────────┘
                                 │ HTTP / REST
┌────────────────────────────────▼────────────────────────────────────┐
│                      FastAPI Backend (Port 8000)                      │
│                                                                       │
│   ┌──────────┐  ┌───────────┐  ┌─────────────┐  ┌───────────────┐  │
│   │ /api/auth│  │/api/chat  │  │/api/documents│  │ /api/agent    │  │
│   │ JWT Auth │  │ Chat & RAG│  │ Upload & Idx │  │ Agentic Tools │  │
│   └──────────┘  └─────┬─────┘  └──────┬───────┘  └───────┬───────┘  │
│                        │               │                   │           │
│   ┌────────────────────▼───────────────▼───────────────────▼───────┐  │
│   │                   LangGraph Orchestration Layer                  │  │
│   │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │  │
│   │  │  RAG Agent   │  │  Web Search  │  │  Code / Email /      │  │  │
│   │  │  (retrieve + │  │  (DuckDuckGo │  │  GitHub Action Tools │  │  │
│   │  │   generate)  │  │   / Tavily)  │  │                      │  │  │
│   │  └──────────────┘  └──────────────┘  └──────────────────────┘  │  │
│   └─────────────────────────────────────────────────────────────────┘  │
│                                                                       │
│   ┌────────────────────────┐   ┌───────────────────────────────────┐  │
│   │   LLM Provider Layer   │   │       Vector Store (ChromaDB)     │  │
│   │  Groq → Google → OpenAI│   │   Embeddings: OpenAI / Google     │  │
│   │  (priority fallback)   │   │   Chunking: 512 tokens, 64 overlap│  │
│   └────────────────────────┘   └───────────────────────────────────┘  │
│                                                                       │
│   ┌────────────────────────────────────────────────────────────────┐  │
│   │                  Persistent Memory (SQLite)                     │  │
│   │  sessions · messages · users · user_profiles                   │  │
│   │  refresh_tokens · message_feedback                             │  │
│   └────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## ✨ Features

| Feature | Details |
|---|---|
| **Multi-LLM Support** | Groq (default), Google Gemini, OpenAI — with automatic priority fallback |
| **RAG Pipeline** | ChromaDB vector store, semantic chunking, top-K retrieval |
| **Persistent Memory** | SQLite-backed chat history, sessions, and user profiles |
| **Agentic Tools** | Web search (DuckDuckGo / Tavily), email via SendGrid, GitHub Issues, code interpreter |
| **LangGraph Orchestration** | Stateful multi-agent graph with conditional routing |
| **Authentication** | JWT access tokens + refresh tokens, bcrypt password hashing |
| **Document Ingestion** | PDF, DOCX, HTML, plain text — chunked and indexed automatically |
| **Feedback Loop** | Per-message thumbs-up/down feedback stored in SQLite |

---

## 🗂️ Project Structure

```
.
├── main.py                    # FastAPI app entry point
├── requirements.txt           # Python dependencies
├── .env.example               # Environment variable template
├── memory.db                  # SQLite persistent memory (auto-created)
├── chroma_db/                 # ChromaDB vector store (auto-created)
│
├── api/
│   ├── auth.py                # Registration, login, token refresh
│   ├── chat.py                # Chat endpoint with RAG + memory
│   ├── documents.py           # Document upload & indexing
│   └── agent.py               # Agentic multi-tool endpoint
│
├── core/
│   └── config.py              # Settings via pydantic-settings
│
├── memory/
│   └── memory_manager.py      # SQLite session/message CRUD + init_db()
│
├── agents/                    # LangGraph agent definitions
├── tools/                     # Action tools (search, email, GitHub)
└── frontend/                  # Next.js frontend (see Frontend section)
```

---

## 🗄️ Database Schema (SQLite — `memory.db`)

```
users               → user_id (PK), email, password_hash, name, created_at
sessions            → session_id (PK), user_id (FK), created_at
messages            → id (PK), session_id, user_id, role, content, timestamp
user_profiles       → session_id (PK), user_id, sources_accessed, query_count, updated_at
refresh_tokens      → jti (PK), user_id, expires_at, revoked, created_at
message_feedback    → id (PK), user_id, session_id, answer, vote, created_at
```

---

## 🔑 Environment Variables

Copy `.env.example` to `.env` and fill in your keys:

```bash
cp .env.example .env
```

| Variable | Required | Description |
|---|---|---|
| `LLM_PROVIDER` | ✅ | Primary LLM: `groq`, `google`, or `openai` |
| `LLM_FALLBACK_ORDER` | ✅ | Comma-separated fallback chain |
| `GROQ_API_KEY` | ✅ (if using Groq) | Free at [console.groq.com](https://console.groq.com) |
| `GROQ_MODEL` | ✅ | e.g. `llama-3.3-70b-versatile` |
| `GOOGLE_API_KEY` | Optional | Google Gemini API key |
| `OPENAI_API_KEY` | Optional | OpenAI API key |
| `OPENAI_EMBEDDING_MODEL` | Optional | e.g. `text-embedding-3-small` |
| `CHROMA_PERSIST_DIR` | ✅ | Path for ChromaDB storage, e.g. `./chroma_db` |
| `RETRIEVAL_TOP_K` | ✅ | Number of chunks to retrieve (default: `5`) |
---

## 🚀 Backend Setup

> **Requires Python 3.11**

### 1 — Find your Python 3.11 executable

```powershell
py -3.11 -c "import sys; print(sys.executable)"
```

### 2 — Create and activate a virtual environment

```powershell
& "C:\Users\<YourUser>\AppData\Local\Programs\Python\Python311\python.exe" -m venv venv
.\venv\Scripts\Activate.ps1
```

> If you get an execution policy error, run:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

### 3 — Install dependencies

```powershell
pip install -r requirements.txt
```

### 4 — Configure environment

```powershell
copy .env.example .env
# Open .env and fill in at least GROQ_API_KEY (free, no credit card)
```

### 5 — Start the backend server

```powershell
 python main.py or 
 uvicorn main:app --reload
```

The API will be live at **http://localhost:8000**

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health check: http://localhost:8000/health

---

## 💻 Frontend Setup

> **Requires Node.js 18+**

```powershell
cd frontend
npm install
npm run dev
```

The Next.js dev server starts at **http://localhost:3000**

CORS is pre-configured: the backend accepts requests from `localhost:3000` and `127.0.0.1:3000` in development.

---

## 📡 API Endpoints

### Auth
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/auth/register` | Create new user account |
| `POST` | `/auth/login` | Login → returns access + refresh tokens |
| `POST` | `/auth/refresh` | Refresh access token |

### Chat & RAG
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/chat` | Send message → RAG retrieval + LLM response |
| `GET` | `/chat/history/{session_id}` | Fetch conversation history |

### Documents
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/documents/upload` | Upload and index a document (PDF, DOCX, HTML, TXT) |
| `GET` | `/documents` | List indexed documents |
| `DELETE` | `/documents/{doc_id}` | Remove a document from the index |

### Agent
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/agent/run` | Run agentic workflow with tool access |

---

## 🤝 LLM Provider Fallback

The system tries providers in order of `LLM_FALLBACK_ORDER`. If Groq is rate-limited or unavailable, it automatically falls back to Google Gemini, then OpenAI. Embedding models follow the same priority.

```
Default: Groq (llama-3.3-70b-versatile)
  ↓ fallback
Google (gemini-2.5-flash-lite)
  ↓ fallback
OpenAI (gpt-4o)
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Web Framework** | FastAPI 0.115+ |
| **LLM Orchestration** | LangChain 1.x + LangGraph 0.2+ |
| **LLM Providers** | Groq, Google Gemini, OpenAI |
| **Vector Store** | ChromaDB 0.6+ |
| **Persistent Memory** | SQLite (via standard `sqlite3`) |
| **Authentication** | JWT (python-jose) + bcrypt (passlib) |
| **Document Parsing** | pypdf, python-docx, beautifulsoup4 |
| **Web Search** | DuckDuckGo (`ddgs`) / Tavily (optional) |
| **Server** | Uvicorn (ASGI) |
| **Frontend** | Next.js (React) |

---

## 🔒 Security Notes

- Never commit your `.env` file — it's in `.gitignore`
- JWT tokens expire; use `/auth/refresh` to renew
- Refresh tokens are stored in SQLite and can be revoked server-side
- The example `.env.example` contains a placeholder Groq key — replace it with your own

---

## 📄 License

MIT — see `LICENSE` for details.