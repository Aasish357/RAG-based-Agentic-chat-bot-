import re
import requests
from config import OLLAMA_BASE_URL, LLM_MODEL

PLANNER_SYSTEM = (
    "You are the Planner agent in a multi-agent RAG chatbot system.\n"
    "Given a user query and conversation context, decide the best approach.\n\n"
    "Respond in this EXACT format:\n"
    "PLAN:\n"
    "- Step 1: describe what to do\n"
    "- Step 2: describe what to do\n"
    "TOOLS_NEEDED: retriever, calculator, document_info, or none\n"
    "RETRIEVAL_QUERY: an optimised search query string, or NONE\n"
)


def run_planner(user_query, long_term_summary, recent_turns):
    context = ""
    if long_term_summary:
        context = "[Long-term memory]\n" + long_term_summary + "\n\n"

    history = ""
    for m in recent_turns[-4:]:
        role = m["role"].upper()
        content = m["content"]
        history += role + ": " + content + "\n"

    prompt = PLANNER_SYSTEM + "\n\n" + context + history + "\nUSER QUERY: " + user_query + "\n\nYour plan:"
    raw = _call(prompt)

    tools = []
    retrieval_query = None

    tm = re.search(r"TOOLS_NEEDED:\s*(.+)", raw)
    if tm:
        parts = tm.group(1).strip().lower().split(",")
        tools = [t.strip() for t in parts if t.strip() != "none"]

    rm = re.search(r"RETRIEVAL_QUERY:\s*(.+)", raw)
    if rm:
        val = rm.group(1).strip()
        if val.upper() != "NONE":
            retrieval_query = val

    return {"plan": raw, "tools_needed": tools, "retrieval_query": retrieval_query}


def _call(prompt):
    r = requests.post(
        OLLAMA_BASE_URL + "/api/generate",
        json={"model": LLM_MODEL, "prompt": prompt, "stream": False}
    )
    r.raise_for_status()
    return r.json().get("response", "")
