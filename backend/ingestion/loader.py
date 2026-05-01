import os
import tempfile
from pathlib import Path
from typing import List
import requests
from bs4 import BeautifulSoup
from langchain_core.documents import Document
from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    TextLoader,
    UnstructuredFileLoader,
    CSVLoader
)


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".csv", ".html"}


def load_pdf(file_path: str) -> List[Document]:
    loader = PyPDFLoader(file_path)
    return loader.load()


def load_docx(file_path: str) -> List[Document]:
    loader = Docx2txtLoader(file_path)
    return loader.load()


def load_text(file_path: str) -> List[Document]:
    loader = TextLoader(file_path, autodetect_encoding=True)
    return loader.load()


def load_generic(file_path: str) -> List[Document]:
    loader = UnstructuredFileLoader(file_path)
    return loader.load()

def load_csv(file_path: str):
    loader = CSVLoader(file_path=file_path)
    return loader.load()

def load_url(url: str) -> List[Document]:
    """Fetch a webpage and extract its text content."""
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    # Remove script and style elements
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)
    return [Document(page_content=text, metadata={"source": url, "type": "url"})]


def load_from_bytes(file_bytes: bytes, filename: str) -> List[Document]:
    """Load a document from raw bytes (e.g. from an API upload)."""
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type: '{ext}'. "
            f"Supported types: {', '.join(SUPPORTED_EXTENSIONS)}"
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        docs = load_file(tmp_path)
        # Attach original filename as metadata
        for doc in docs:
            doc.metadata["source"] = filename
        return docs
    finally:
        os.unlink(tmp_path)


def load_file(file_path: str) -> List[Document]:
    """Dispatch to the correct loader based on file extension."""
    ext = Path(file_path).suffix.lower()
    loaders = {
        ".pdf": load_pdf,
        ".docx": load_docx,
        ".txt": load_text,
        ".md": load_text,
        ".csv": load_csv
    }
    loader_fn = loaders.get(ext, load_generic)
    docs = loader_fn(file_path)

    # Attach file type to metadata
    for doc in docs:
        doc.metadata.setdefault("source", file_path)
        doc.metadata["type"] = ext.lstrip(".")

    return docs
