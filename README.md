# 🧠 Jahiv — Fully Local Agentic RAG Workspace

**Jahiv** is a 100% local, privacy-first Agentic Retrieval-Augmented Generation (RAG) workspace. Powered entirely by [Ollama](https://ollama.ai/), Jahiv eliminates cloud dependencies, subscription fees, and data leaks. It features a transparent, modular multi-agent pipeline built with **FastAPI**, **Pydantic v2**, **FAISS**, and **SQLAlchemy 2.0 (aiosqlite)**, paired with a modern **React + Vite** frontend — completely free of heavyweight orchestration frameworks like LangChain or LlamaIndex.

---

## 🏛 Architecture

Jahiv employs an isolated multi-agent orchestration pattern where specialized agents collaborate sequentially to plan, retrieve, formulate, and critique answers:

```
                  ┌──────────────────────┐
                  │      User Query      │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │       Planner        │ ◄── Analyzes query & selects tools
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │    Tool Execution    │ ◄── Executes Retriever / Calculator / Docs
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │       Executor       │ ◄── Generates grounded answer + citations
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │        Critic        │ ◄── Validates against hallucination & quality
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │    Final Response    │
                  └──────────────────────┘
```

1. **Planner Agent**: Evaluates user intent and conversational context to decide whether tools are necessary (e.g. searching documents, mathematical computations, or general reasoning) and structures a multi-step plan.
2. **Tool Execution Engine**: Executes tools in an isolated, deterministic environment (safe AST calculator, FAISS vector retriever, document metadata inspector).
3. **Executor Agent**: Synthesizes retrieved context, tool outputs, and conversational memory into a coherent, cited response with explicit source references (e.g. `[filename.pdf p.N]`).
4. **Critic Agent**: Reviews generated responses against source citations to detect hallucinations, ensure factual consistency, and enforce response quality before delivering the final answer to the user.

---

## 🧠 Dual-Layer Memory System

Jahiv incorporates a hybrid memory management model designed to maintain long-running conversations without exceeding LLM context windows:

- **Short-Term Memory (Sliding Window)**: Retains the most recent conversational exchanges (default: 6 turns / 12 messages) in full detail to preserve immediate dialogue context.
- **Long-Term Memory (Progressive Summarization)**: When dialogue turns exceed a configured threshold (default: 12 turns), a background summarization agent condenses earlier history into an evolving, persistent summary.
- **Multi-Session Database Persistence**: Uses asynchronous SQLite via SQLAlchemy 2.0 and `aiosqlite` to store separate conversation sessions, message history, and document catalogs persistently in `data/jahiv.db`.

---

## 🛠 Built-in Tools

- **`retriever`**: Semantically searches indexed documents using FAISS and vector embeddings (`nomic-embed-text`) with L2-normalized cosine similarity scoring.
- **`calculator`**: Deterministically evaluates mathematical expressions and numeric calculations using an AST-safe evaluator.
- **`document_info`**: Inspects indexed document catalogs, metadata, chunk sizes, and vector database status.

---

## 📂 Project Structure

```
jahiv/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point & lifespan initialization
│   │   ├── config.py            # Pydantic Settings (BaseSettings)
│   │   ├── api/
│   │   │   └── routes.py        # REST API endpoints (Chat, Upload, Memory, Docs)
│   │   ├── agents/
│   │   │   ├── planner.py       # Query analysis & tool selection
│   │   │   ├── executor.py      # Grounded response synthesis with citations
│   │   │   ├── critic.py        # Hallucination detection & answer improvement
│   │   │   └── pipeline.py      # Async multi-agent orchestrator
│   │   ├── rag/
│   │   │   └── store.py         # FAISS vector store & PDF ingestion
│   │   ├── memory/
│   │   │   └── manager.py       # Sliding window + progressive summarizer
│   │   ├── tools/
│   │   │   └── registry.py      # Tool definitions (Retriever, Calculator, Docs)
│   │   └── db/
│   │       ├── session.py       # Async SQLite engine & sessionmaker (aiosqlite)
│   │       ├── models.py        # SQLAlchemy models (Document, Session, Message)
│   │       └── crud.py          # Async database repository operations
│   ├── requirements.txt         # Backend Python dependencies
│   └── Dockerfile               # Backend Docker containerization
├── frontend/                    # React 18 + Vite SPA workspace
│   ├── src/
│   │   ├── components/          # ChatWindow, Sidebar, DocumentManager, AgentInspector
│   │   ├── api/client.js        # Frontend API client
│   │   ├── icons/Icons.jsx      # Clean SVG icon components
│   │   ├── App.jsx              # Main application state & health polling
│   │   └── index.css            # Dark cyber-minimalist styles
│   ├── package.json
│   ├── vite.config.js           # Vite dev server with proxy to backend
│   └── Dockerfile               # Production multi-stage Nginx container
├── docker-compose.yml           # Multi-container orchestration
├── .env.example                 # Example configuration template
└── README.md                    # Project documentation
```

---

## 🚀 Getting Started

### Prerequisites

- **Python**: 3.11 or higher
- **Node.js**: 18 or higher (for frontend)
- **Ollama**: Installed and running locally ([Download Ollama](https://ollama.ai/download))
- **Ollama Models**:
  ```bash
  # Pull the embedding model (required for RAG)
  ollama pull nomic-embed-text

  # Pull your preferred LLM model:
  ollama pull llama3.2          # Recommended for speed and lower RAM
  # or:
  ollama pull llama3.1          # Standard model
  ```

---

### Local Setup

#### 1. Clone the repository:
```bash
git clone https://github.com/Aasish357/Agentic-AI-project.git
cd "Agentic-AI project"
```

#### 2. Configure Environment:
```bash
cp .env.example .env
```
*(Make sure `LLM_MODEL` in `.env` matches your installed Ollama model, e.g. `llama3.2:latest` or `llama3.1`).*

#### 3. Start the Backend:
```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
The FastAPI backend will be live at `http://localhost:8000` with Swagger documentation at `http://localhost:8000/docs`.

#### 4. Start the Frontend Workspace:
In a separate terminal window:
```bash
cd frontend
npm install
npm run dev
```
Open your browser to **`http://localhost:5173`**.

---

## 🐳 Docker Deployment

Run the complete Jahiv workspace using Docker Compose:

```bash
docker compose up --build
```

> **Note**: The backend container connects to Ollama running on your host system at `http://host.docker.internal:11434`.

---

## 📡 API Endpoints Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check & Ollama service connectivity / model listing |
| `POST` | `/api/chat` | Send a query to the agentic RAG pipeline (`message`, `session_id`) |
| `POST` | `/api/upload` | Upload and chunk PDF files into FAISS & SQLite catalog |
| `GET` | `/api/documents` | List all ingested documents, page counts, and chunk statistics |
| `DELETE` | `/api/documents/{doc_id}` | Remove a document from the database and vector index |
| `GET` | `/api/memory/{session_id}` | Retrieve persistent conversational history and rolling summary |
| `GET` | `/api/status` | Ingestion status, indexed chunk counts, and memory turns |
| `POST` | `/api/clear` | Clear the current conversation memory |

---

## ⚙️ Configuration Reference

Settings can be specified in `.env`:

| Variable | Default | Description |
|---|---|---|
| `HOST` | `0.0.0.0` | Backend bind address |
| `PORT` | `8000` | Backend listening port |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama HTTP API endpoint |
| `LLM_MODEL` | `llama3.2:latest` | Primary LLM tag served by Ollama |
| `EMBED_MODEL` | `nomic-embed-text` | Embedding model tag served by Ollama |
| `TOP_K` | `5` | Number of chunks retrieved from FAISS |
| `CONFIDENCE_THRESHOLD` | `0.4` | Cosine similarity threshold for search filtering |
| `CHUNK_SIZE` | `500` | Character chunk size for PDF ingestion |
| `CHUNK_OVERLAP` | `100` | Overlap between consecutive chunks |
| `SHORT_TERM_LIMIT` | `6` | Number of turns kept in short-term buffer |
| `SUMMARY_TRIGGER` | `12` | Turn count triggering auto-summarization |
| `CRITIC_ENABLED` | `true` | Enable or disable the Critic agent step |
| `DATA_DIR` | `data` | Directory for SQLite DB (`jahiv.db`) and vector index |
| `MAX_UPLOAD_SIZE_MB` | `50` | Maximum file upload size in megabytes |

---

## 🔧 Troubleshooting

- **Ollama 500 / EOF error**: Ensure the model declared in `LLM_MODEL` is pulled on your system. Run `ollama list` in your terminal to see installed models, and update `.env` accordingly (e.g. `LLM_MODEL=llama3.2:latest`).
- **Embedding model error**: Ensure `nomic-embed-text` is installed by running `ollama pull nomic-embed-text`.
- **Database resets**: The SQLite database is stored at `data/jahiv.db`. Deleting this file resets all session histories and document catalogs.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).