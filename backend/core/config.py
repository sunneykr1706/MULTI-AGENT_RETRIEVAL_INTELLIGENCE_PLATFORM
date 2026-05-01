from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Primary provider: "google", "groq", or "openai"
    llm_provider: str = "google"
    # Comma-separated fallback order e.g. "google,groq,openai"
    llm_fallback_order: str = "google,groq,openai"

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-small"

    # Google Gemini
    google_api_key: str = ""
    google_model: str = "gemini-2.5-flash-lite"
    google_embedding_model: str = "models/text-embedding-004"

    # Groq (free tier: https://console.groq.com/)
    groq_api_key: str = "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"
    groq_model: str = "llama-3.3-70b-versatile"

    # ChromaDB
    chroma_persist_dir: str = "./chroma_db"
    chroma_collection_name: str = "rag_documents"

    # Retrieval
    retrieval_top_k: int = 5
    chunk_size: int = 512
    chunk_overlap: int = 64

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Auth / JWT
    jwt_secret_key: str = "change-me-in-env"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Phase 3 — Action Tools
    # Web search: Tavily (optional upgrade, free tier at https://tavily.com)
    tavily_api_key: str = ""
    # Email: SendGrid (free: 100 emails/day at https://sendgrid.com)
    sendgrid_api_key: str = ""
    sendgrid_from_email: str = ""   # must be a verified sender in SendGrid
    # GitHub: personal access token (https://github.com/settings/tokens, needs 'repo' scope)
    github_token: str = ""

    # Image generation: Replicate (recommended primary provider)
    replicate_api_token: str = ""
    replicate_image_model: str = "black-forest-labs/flux-schnell"

    # Image fallback (optional): Hugging Face Inference API
    hf_api_token: str = ""
    hf_image_model: str = "stabilityai/stable-diffusion-xl-base-1.0"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
