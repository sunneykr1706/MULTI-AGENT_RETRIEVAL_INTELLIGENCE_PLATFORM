from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.chat import router as chat_router
from api.documents import router as documents_router
from api.agent import router as agent_router
from api.auth import router as auth_router
from core.config import get_settings
from memory.memory_manager import init_db

settings = get_settings()
init_db()   # create SQLite tables if they don't exist

app = FastAPI(
    title="Multi-Agent RAG System",
    description="Multi-Agent RAG with persistent memory, action tools (web search, code interpreter, email, GitHub), and LangGraph orchestration.",
    version="3.0.0",
)

# Allow requests from the Next.js frontend (localhost:3000) during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(documents_router)
app.include_router(agent_router)
app.include_router(auth_router)


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok", "version": "3.0.0"}
