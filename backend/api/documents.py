from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, HttpUrl
from typing import List, Optional

from ingestion.loader import load_from_bytes, load_url
from ingestion.chunker import chunk_documents
from ingestion.embedder import embed_and_store, delete_by_source
from api.auth import get_current_user

router = APIRouter(prefix="/documents", tags=["documents"])


class IngestURLRequest(BaseModel):
    url: HttpUrl
    label: Optional[str] = None


class IngestResponse(BaseModel):
    message: str
    source: str
    chunks_stored: int


class DeleteResponse(BaseModel):
    message: str
    source: str


@router.post("/upload", response_model=IngestResponse)
async def upload_document(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    """Upload a file (PDF, DOCX, TXT, MD, CSV) for ingestion."""
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        docs = load_from_bytes(file_bytes, file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=415, detail=str(exc))

    chunks = chunk_documents(docs)
    try:
        count = embed_and_store(chunks)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Embedding failed: {exc}")

    return IngestResponse(
        message="Document ingested successfully.",
        source=file.filename,
        chunks_stored=count,
    )


@router.post("/ingest-url", response_model=IngestResponse)
async def ingest_url(body: IngestURLRequest, current_user: dict = Depends(get_current_user)):
    """Ingest content from a public URL."""
    url_str = str(body.url)
    try:
        docs = load_url(url_str)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {exc}")

    chunks = chunk_documents(docs)
    count = embed_and_store(chunks)

    return IngestResponse(
        message="URL ingested successfully.",
        source=url_str,
        chunks_stored=count,
    )


@router.delete("/{source}", response_model=DeleteResponse)
async def delete_document(source: str, current_user: dict = Depends(get_current_user)):
    """Remove all chunks for a given source document name or URL."""
    delete_by_source(source)
    return DeleteResponse(
        message="Document removed from vector store.",
        source=source,
    )
