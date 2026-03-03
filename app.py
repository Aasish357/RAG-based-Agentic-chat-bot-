import sys
import os
import traceback

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

# Make sure project root is on the path
sys.path.insert(0, os.path.dirname(__file__))

from config import UPLOAD_FOLDER, FAISS_INDEX_PATH
from pipeline import FAISSStore, ingest_pdf
from store import ConversationMemory
from registry import ToolRegistry
from planner import run_planner
from executor import run_executor, run_tools
from critic import run_critic

# ─────────────────────────────────────────────
# App setup
# ─────────────────────────────────────────────
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"))
CORS(app)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024  # 32 MB upload limit

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(FAISS_INDEX_PATH, exist_ok=True)

# Shared state (single-user; for multi-user use sessions/db)
faiss_store = FAISSStore()
memory = ConversationMemory()
registry = ToolRegistry(faiss_store)

# Try loading existing index on startup
faiss_store.load()


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload_pdf():
    """Ingest a PDF into the FAISS vector store."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    f = request.files["file"]
    if not f.filename.endswith(".pdf"):
        return jsonify({"error": "Only PDF files are supported"}), 400

    save_path = os.path.join(UPLOAD_FOLDER, f.filename)
    f.save(save_path)

    try:
        num_chunks = ingest_pdf(save_path, faiss_store)
        memory.clear()  # fresh document = fresh conversation
        return jsonify({
            "message": f"Document ingested successfully.",
            "filename": f.filename,
            "chunks_indexed": num_chunks
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/chat", methods=["POST"])
def chat():
    """
    Main chat endpoint.
    Pipeline: Planner → Tool execution → Executor → Critic → Response
    """
    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"error": "No message provided"}), 400

    user_query = data["message"].strip()
    if not user_query:
        return jsonify({"error": "Empty message"}), 400

    try:
        # 1. Get memory context
        long_term_summary, recent_turns = memory.build_context()

        # 2. Planner: analyse query and decide tools
        plan = run_planner(user_query, long_term_summary, recent_turns)
        print(f"[Planner] Tools needed: {plan['tools_needed']}")
        print(f"[Planner] Retrieval query: {plan['retrieval_query']}")

        # 3. Execute tools
        tool_results = run_tools(plan, registry)

        # 4. Executor: generate draft answer
        draft = run_executor(
            user_query, plan["plan"],
            tool_results, long_term_summary,
            recent_turns, plan["tools_needed"]
        )

        # 5. Critic: validate and optionally improve
        critique = run_critic(user_query, draft, tool_results)
        final_answer = critique["final_answer"]

        print(f"[Critic] Verdict: {critique['verdict']} | Issues: {critique['issues']}")

        # 6. Store turn in memory
        memory.add_turn(user_query, final_answer)

        return jsonify({
            "answer": final_answer,
            "debug": {
                "tools_used": plan["tools_needed"],
                "retrieval_query": plan["retrieval_query"],
                "critic_verdict": critique["verdict"],
                "critic_issues": critique["issues"]
            }
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": "Agent pipeline error: " + str(e)}), 500


@app.route("/status", methods=["GET"])
def status():
    return jsonify({
        "document_loaded": not faiss_store.is_empty(),
        "chunks_indexed": len(faiss_store.chunks) if not faiss_store.is_empty() else 0,
        "memory_turns": len(memory.short_term) // 2
    })


@app.route("/clear", methods=["POST"])
def clear_memory():
    memory.clear()
    return jsonify({"message": "Conversation memory cleared."})


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("Starting RAG Chatbot on http://localhost:5000")
    app.run(debug=True, port=5000)
print("FLASK ROOT:", app.root_path)