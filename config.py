# config.py — Central configuration for the RAG Chatbot

OLLAMA_BASE_URL = "http://localhost:11434"

# LLM model served via Ollama (change to your pulled model)
LLM_MODEL = "phi3:mini"          # e.g. llama3.1, mistral, gemma2

# Embedding model served via Ollama
EMBED_MODEL = "nomic-embed-text"

# RAG chunking settings
CHUNK_SIZE = 512          # characters per chunk
CHUNK_OVERLAP = 64        # overlap between chunks

# How many chunks to retrieve per query
TOP_K_RETRIEVAL = 4

# Short-term memory: max turns to keep in context
SHORT_TERM_TURNS = 6

# Long-term memory: summary threshold (summarise after N turns)
LONG_TERM_SUMMARY_THRESHOLD = 12

# FAISS index storage path
FAISS_INDEX_PATH = "data/faiss_index"

# Upload folder
UPLOAD_FOLDER = "data/uploads"
