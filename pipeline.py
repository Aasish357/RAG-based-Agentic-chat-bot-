# rag/pipeline.py — PDF ingestion → chunking → embedding → FAISS index

import os
import pickle
import numpy as np
import faiss
import requests
from pypdf import PdfReader
from config import (
    OLLAMA_BASE_URL, EMBED_MODEL,
    CHUNK_SIZE, CHUNK_OVERLAP,
    FAISS_INDEX_PATH, TOP_K_RETRIEVAL
)


# ─────────────────────────────────────────────
# 1. PDF TEXT EXTRACTION
# ─────────────────────────────────────────────

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract raw text from all pages of a PDF."""
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text.strip()


# ─────────────────────────────────────────────
# 2. CHUNKING
# ─────────────────────────────────────────────

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP):
    """
    Split text into overlapping chunks by character count.
    Overlap preserves context at chunk boundaries.
    """
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start += chunk_size - overlap
    return chunks


# ─────────────────────────────────────────────
# 3. EMBEDDING via Ollama
# ─────────────────────────────────────────────

def embed_text(text: str):
    """Get embedding vector for a single text string via Ollama."""
    response = requests.post(
        f"{OLLAMA_BASE_URL}/api/embeddings",
        json={"model": EMBED_MODEL, "prompt": text}
    )
    response.raise_for_status()
    return response.json()["embedding"]


def embed_batch(texts):
    """Embed a list of texts and return as numpy float32 array."""
    embeddings = [embed_text(t) for t in texts]
    return np.array(embeddings, dtype="float32")


# ─────────────────────────────────────────────
# 4. FAISS INDEX — Build & Persist
# ─────────────────────────────────────────────

class FAISSStore:
    """
    Wraps a FAISS flat L2 index with the original chunk texts.
    Supports incremental addition and persistence to disk.
    """

    def __init__(self):
        self.index = None
        self.chunks = []
        self.dim = 0

    def build(self, chunks):
        """Embed all chunks and build a fresh FAISS index."""
        print(f"[RAG] Embedding {len(chunks)} chunks with {EMBED_MODEL}...")
        vectors = embed_batch(chunks)
        self.dim = vectors.shape[1]
        self.index = faiss.IndexFlatL2(self.dim)
        self.index.add(vectors)
        self.chunks = chunks
        print(f"[RAG] FAISS index built — {self.index.ntotal} vectors, dim={self.dim}")

    def add(self, new_chunks):
        """Add more chunks to an existing index."""
        vectors = embed_batch(new_chunks)
        if self.index is None:
            self.dim = vectors.shape[1]
            self.index = faiss.IndexFlatL2(self.dim)
        self.index.add(vectors)
        self.chunks.extend(new_chunks)

    def search(self, query: str, top_k: int = TOP_K_RETRIEVAL):
        """Return top_k most relevant chunks for a query."""
        if self.index is None or self.index.ntotal == 0:
            return []
        query_vec = np.array([embed_text(query)], dtype="float32")
        distances, indices = self.index.search(query_vec, top_k)
        results = []
        for idx in indices[0]:
            if idx != -1 and idx < len(self.chunks):
                results.append(self.chunks[idx])
        return results

    def save(self, path: str = FAISS_INDEX_PATH):
        """Persist index and chunks to disk."""
        os.makedirs(path, exist_ok=True)
        faiss.write_index(self.index, os.path.join(path, "index.faiss"))
        with open(os.path.join(path, "chunks.pkl"), "wb") as f:
            pickle.dump(self.chunks, f)
        print(f"[RAG] Index saved to {path}")

    def load(self, path: str = FAISS_INDEX_PATH):
        """Load index and chunks from disk. Returns True if successful."""
        index_file = os.path.join(path, "index.faiss")
        chunks_file = os.path.join(path, "chunks.pkl")
        if not os.path.exists(index_file):
            return False
        self.index = faiss.read_index(index_file)
        with open(chunks_file, "rb") as f:
            self.chunks = pickle.load(f)
        self.dim = self.index.d
        print(f"[RAG] Loaded index with {self.index.ntotal} vectors")
        return True

    def is_empty(self):
        return self.index is None or self.index.ntotal == 0


# ─────────────────────────────────────────────
# 5. PUBLIC HELPER
# ─────────────────────────────────────────────

def ingest_pdf(pdf_path: str, store: FAISSStore):
    text = extract_text_from_pdf(pdf_path)
    if not text:
        raise ValueError(f"Could not extract text from {pdf_path}")

    chunks = chunk_text(text)

    # 🔥 Clear old index completely
    store.index = None
    store.chunks = []
    store.dim = 0

    store.build(chunks)
    store.save()

    return len(chunks)