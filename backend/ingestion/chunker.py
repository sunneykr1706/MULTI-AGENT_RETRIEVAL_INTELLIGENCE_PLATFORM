from typing import List

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from core.config import get_settings


def chunk_documents(documents: List[Document]) -> List[Document]:
    """
    Split documents into overlapping chunks using recursive character splitting.
    This strategy tries to keep paragraphs → sentences → words intact before
    splitting, giving semantically coherent chunks.
    """
    settings = get_settings()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", "! ", "? ", " ", ""],
        length_function=len,
        add_start_index=True,  # Records char offset of each chunk in metadata
    )

    chunks = splitter.split_documents(documents)

    # Attach chunk index within the same source for traceability
    source_counters: dict = {}
    for chunk in chunks:
        src = chunk.metadata.get("source", "unknown")
        source_counters[src] = source_counters.get(src, 0) + 1
        chunk.metadata["chunk_index"] = source_counters[src]

    return chunks
