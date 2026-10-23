"""FAISS vector store and PDF ingestion module for Jahiv RAG pipeline."""

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import faiss
import httpx
import numpy as np
from pypdf import PdfReader

try:
    from app.config import settings
except ImportError:
    try:
        from backend.app.config import settings
    except ImportError:
        try:
            import config as root_config

            class SettingsFallback:
                OLLAMA_BASE_URL: str = getattr(root_config, "OLLAMA_BASE_URL", "http://localhost:11434")
                LLM_MODEL: str = getattr(root_config, "LLM_MODEL", "llama3.1")
                EMBED_MODEL: str = getattr(root_config, "EMBED_MODEL", "nomic-embed-text")
                DATA_DIR: str = getattr(root_config, "UPLOAD_FOLDER", "data")
                CHUNK_SIZE: int = getattr(root_config, "CHUNK_SIZE", 500)
                CHUNK_OVERLAP: int = getattr(root_config, "CHUNK_OVERLAP", 100)
                TOP_K: int = getattr(root_config, "TOP_K_RETRIEVAL", 5)
                CONFIDENCE_THRESHOLD: float = 0.4
                SHORT_TERM_LIMIT: int = getattr(root_config, "SHORT_TERM_TURNS", 6)
                SUMMARY_TRIGGER: int = getattr(root_config, "LONG_TERM_SUMMARY_THRESHOLD", 12)
                CRITIC_ENABLED: bool = True

            settings = SettingsFallback()
        except ImportError:
            class DefaultSettings:
                OLLAMA_BASE_URL: str = "http://localhost:11434"
                LLM_MODEL: str = "llama3.1"
                EMBED_MODEL: str = "nomic-embed-text"
                DATA_DIR: str = "data"
                CHUNK_SIZE: int = 500
                CHUNK_OVERLAP: int = 100
                TOP_K: int = 5
                CONFIDENCE_THRESHOLD: float = 0.4
                SHORT_TERM_LIMIT: int = 6
                SUMMARY_TRIGGER: int = 12
                CRITIC_ENABLED: bool = True

            settings = DefaultSettings()


# Module-level globals for storage
documents: list[dict[str, Any]] = []
chunks: list[dict[str, Any]] = []
index: Optional[faiss.IndexFlatIP] = None


def chunk_text(
    text: str,
    chunk_size: Optional[int] = None,
    overlap: Optional[int] = None,
) -> list[str]:
    """
    Split text into overlapping character chunks.
    Overlap preserves context at boundaries.
    """
    size = chunk_size if chunk_size is not None else getattr(settings, "CHUNK_SIZE", 500)
    ov = overlap if overlap is not None else getattr(settings, "CHUNK_OVERLAP", 100)
    chunks_list: list[str] = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = start + size
        piece = text[start:end]
        if piece.strip():
            chunks_list.append(piece.strip())
        start += size - ov
    return chunks_list


async def get_embedding(text: str) -> list[float]:
    """
    Fetch text embedding vector asynchronously via Ollama HTTP API.
    Uses 120s timeout and queries POST OLLAMA_BASE_URL/api/embed.
    """
    timeout = httpx.Timeout(120.0, connect=30.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        # Standard modern Ollama endpoint
        response = await client.post(
            f"{settings.OLLAMA_BASE_URL}/api/embed",
            json={"model": settings.EMBED_MODEL, "input": text},
        )
        if response.status_code == 200:
            data = response.json()
            embeddings = data.get("embeddings")
            if embeddings and len(embeddings) > 0:
                return embeddings[0]

        # Fallback for older Ollama versions supporting /api/embeddings
        if response.status_code == 404:
            fallback_resp = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/embeddings",
                json={"model": settings.EMBED_MODEL, "prompt": text},
            )
            fallback_resp.raise_for_status()
            return fallback_resp.json()["embedding"]

        response.raise_for_status()
        raise ValueError(f"Ollama returned unexpected embedding payload: {response.text}")


async def ingest_pdf(
    file_path: str,
    filename: str,
    clear_existing: bool = False,
) -> dict[str, Any]:
    """
    Ingest a PDF from disk into the FAISS store:
    - Extracts text page by page with pypdf
    - Chunks text while preserving metadata: text, filename, page, chunk_id, document_id
    - Embeds chunks asynchronously via Ollama
    - Updates FAISS IndexFlatIP with L2 normalized vectors
    """
    global documents, chunks, index

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    reader = PdfReader(file_path)
    document_id = str(uuid.uuid4())
    new_chunks: list[dict[str, Any]] = []

    for page_idx, page in enumerate(reader.pages):
        page_text = page.extract_text() or ""
        if not page_text.strip():
            continue
        page_chunks = chunk_text(page_text)
        for ch in page_chunks:
            new_chunks.append({
                "chunk_id": str(uuid.uuid4()),
                "document_id": document_id,
                "filename": filename,
                "page": page_idx + 1,
                "text": ch,
            })

    if not new_chunks:
        raise ValueError(f"Could not extract any readable text from {filename}")

    # Generate embeddings asynchronously with 120s timeout per call
    embeddings: list[list[float]] = []
    for chunk_item in new_chunks:
        emb = await get_embedding(chunk_item["text"])
        embeddings.append(emb)

    vectors = np.array(embeddings, dtype="float32")
    faiss.normalize_L2(vectors)

    if clear_existing or index is None:
        if clear_existing:
            chunks = []
            documents = []
        dim = vectors.shape[1]
        index = faiss.IndexFlatIP(dim)

    index.add(vectors)
    chunks.extend(new_chunks)

    doc_meta = {
        "document_id": document_id,
        "filename": filename,
        "chunks_count": len(new_chunks),
        "pages": len(reader.pages),
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }
    documents.append(doc_meta)

    return {
        "document_id": document_id,
        "filename": filename,
        "chunks_indexed": len(new_chunks),
        "pages": len(reader.pages),
        "total_documents": len(documents),
        "total_chunks": len(chunks),
    }


async def search(
    query: str,
    top_k: Optional[int] = None,
) -> list[dict[str, Any]]:
    """
    Retrieve top-k relevant chunks for a query using FAISS cosine similarity
    (IndexFlatIP with L2 normalized vectors).
    """
    if index is None or index.ntotal == 0 or not chunks:
        return []

    k = top_k if top_k is not None else getattr(settings, "TOP_K", 5)
    query_emb = await get_embedding(query)
    query_vec = np.array([query_emb], dtype="float32")
    faiss.normalize_L2(query_vec)

    search_k = min(k, index.ntotal)
    distances, indices = index.search(query_vec, search_k)

    results: list[dict[str, Any]] = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx != -1 and idx < len(chunks):
            chunk_data = dict(chunks[idx])
            chunk_data["score"] = float(dist)
            results.append(chunk_data)

    return results


def list_documents() -> list[dict[str, Any]]:
    """Return all ingested document metadata."""
    return list(documents)


def clear_store() -> None:
    """Clear all documents, chunks, and reset the FAISS index."""
    global documents, chunks, index
    documents = []
    chunks = []
    index = None


def is_empty() -> bool:
    """Check whether any chunks are currently indexed."""
    return index is None or index.ntotal == 0
