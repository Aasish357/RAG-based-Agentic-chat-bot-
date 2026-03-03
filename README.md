# Agentic RAG Chatbot

A PDF chatbot using a Planner-Executor-Critic multi-agent pipeline, FAISS vector search, dual memory, and Ollama LLMs — fully local.

## Quick Start

1. Install Ollama: https://ollama.com
2. Pull models: `ollama pull llama3.1 && ollama pull nomic-embed-text`
3. `pip install -r requirements.txt`
4. `python app.py`
5. Open http://localhost:5000

## Architecture

User Query -> Planner -> Tool Execution (FAISS retriever / calculator) -> Executor -> Critic -> Final Answer

Memory: Short-term (last 6 turns direct) + Long-term (LLM rolling summary after 12 turns)

## Structure

- app.py - Flask routes
- config.py - All settings
- agents/planner.py - Decides tools + retrieval query
- agents/executor.py - Synthesises answer from context
- agents/critic.py - Validates, rewrites if hallucination detected
- rag/pipeline.py - PDF ingestion, chunking, FAISS embed + search
- memory/store.py - Dual memory system
- tools/registry.py - retriever, calculator, document_info
- templates/index.html - Chat UI

## Config (config.py)

LLM_MODEL = "llama3.1"
EMBED_MODEL = "nomic-embed-text"
CHUNK_SIZE = 512
CHUNK_OVERLAP = 64
TOP_K_RETRIEVAL = 4
SHORT_TERM_TURNS = 6
LONG_TERM_SUMMARY_THRESHOLD = 12

## API

GET  /         - Chat UI
POST /upload   - Upload PDF (form-data: file)
POST /chat     - Send message (JSON: {"message": "..."})
GET  /status   - Document + memory status
POST /clear    - Clear conversation memory