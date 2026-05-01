from typing import List

from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
from langchain_core.embeddings import Embeddings

from core.config import get_settings


class ChromaDefaultEmbeddings(Embeddings):
    """Use Chroma's built-in all-MiniLM-L6-v2 embeddings (runs locally, free)."""

    def __init__(self):
        self._fn = DefaultEmbeddingFunction()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._fn(texts)

    def embed_query(self, text: str) -> List[float]:
        return self._fn([text])[0]


def _get_vector_store() -> Chroma:
    settings = get_settings()
    provider = settings.llm_provider.strip().lower()

    if provider == "google":
        # Use local embeddings (free, no API key needed for embedding)
        embeddings = ChromaDefaultEmbeddings()
    else:
        embeddings = OpenAIEmbeddings(
            model=settings.openai_embedding_model,
            openai_api_key=settings.openai_api_key,
        )

    return Chroma(
        collection_name=settings.chroma_collection_name,
        embedding_function=embeddings,
        persist_directory=settings.chroma_persist_dir,
    )


def embed_and_store(chunks: List[Document]) -> int:
    """Embed document chunks and persist them in ChromaDB. Returns chunk count."""
    if not chunks:
        return 0
    store = _get_vector_store()
    store.add_documents(chunks)
    return len(chunks)


def similarity_search(query: str) -> List[Document]:
    """Retrieve the top-k most relevant chunks for a given query."""
    settings = get_settings()
    store = _get_vector_store()
    results = store.similarity_search(query, k=settings.retrieval_top_k)
    return results


def delete_by_source(source: str) -> None:
    """Remove all chunks belonging to a specific source document."""
    store = _get_vector_store()
    store.delete(where={"source": source})
