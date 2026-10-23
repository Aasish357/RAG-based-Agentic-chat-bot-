"""
Planner agent for Jahiv - analyzes user queries and determines necessary tools.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings

logger = logging.getLogger("jahiv.planner")

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


async def _call_ollama(prompt: str) -> str:
    """Call Ollama generate API asynchronously with a 120-second timeout."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{settings.OLLAMA_BASE_URL}/api/generate",
            json={"model": settings.LLM_MODEL, "prompt": prompt, "stream": False},
        )
        if response.status_code != 200:
            err_msg = response.text
            try:
                err_msg = response.json().get("error", response.text)
            except Exception:
                pass
            raise RuntimeError(
                f"Ollama error ({response.status_code}): {err_msg}. "
                f"Verify '{settings.LLM_MODEL}' is pulled (run 'ollama list')."
            )
        return response.json().get("response", "")


async def plan(
    question: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    rolling_summary: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate an execution plan and select tools for a user question.

    Args:
        question: The user query to evaluate.
        conversation_history: Recent conversation turns.
        rolling_summary: Long-term conversation summary.

    Returns:
        Dict containing plan, tool, query, tools_needed, retrieval_query.
    """
    context = ""
    if rolling_summary:
        context = f"[Long-term memory]\n{rolling_summary}\n\n"

    history = ""
    if conversation_history:
        for m in conversation_history[-4:]:
            role = m.get("role", "user").upper()
            content = m.get("content", "")
            history += f"{role}: {content}\n"

    prompt = (
        PLANNER_SYSTEM
        + "\n\n"
        + context
        + history
        + f"\nUSER QUERY: {question}\n\nYour plan:"
    )

    try:
        raw = await _call_ollama(prompt)
    except Exception as exc:
        logger.warning(f"Planner LLM call failed: {exc}. Using fallback.")
        return {
            "plan": f"Fallback due to LLM error: {exc}",
            "tool": "retriever",
            "query": question,
            "tools_needed": ["retriever"],
            "retrieval_query": question,
        }

    # 1. Attempt JSON parsing if LLM responded with JSON
    try:
        json_candidate = raw.strip()
        if "```json" in json_candidate:
            json_candidate = json_candidate.split("```json")[1].split("```")[0].strip()
        elif "```" in json_candidate:
            json_candidate = json_candidate.split("```")[1].split("```")[0].strip()

        if json_candidate.startswith("{") and json_candidate.endswith("}"):
            parsed = json.loads(json_candidate)
            if isinstance(parsed, dict):
                tool = parsed.get("tool")
                if not tool:
                    tools_list = parsed.get("tools_needed", [])
                    tool = tools_list[0] if tools_list else "retriever"
                query = parsed.get("query") or parsed.get("retrieval_query") or question
                tools_needed = parsed.get("tools_needed", [tool] if tool != "none" else [])
                return {
                    "plan": parsed.get("plan", raw),
                    "tool": tool,
                    "query": query,
                    "tools_needed": tools_needed,
                    "retrieval_query": query,
                }
    except Exception:
        # Fall through to template regex parsing
        pass

    # 2. Parse standard prompt template format via regex
    tools: List[str] = []
    retrieval_query: Optional[str] = None

    tm = re.search(r"TOOLS_NEEDED:\s*(.+)", raw, re.IGNORECASE)
    if tm:
        parts = tm.group(1).strip().lower().split(",")
        tools = [t.strip() for t in parts if t.strip() != "none"]

    rm = re.search(r"RETRIEVAL_QUERY:\s*(.+)", raw, re.IGNORECASE)
    if rm:
        val = rm.group(1).strip()
        if val.upper() != "NONE":
            retrieval_query = val

    if tm or rm:
        primary_tool = tools[0] if tools else "retriever"
        query_str = retrieval_query if retrieval_query else question
        return {
            "plan": raw,
            "tool": primary_tool,
            "query": query_str,
            "tools_needed": tools,
            "retrieval_query": retrieval_query,
        }

    # 3. Fallback logic: if parsing fails, return {"tool": "retriever", "query": question}
    return {
        "plan": raw if raw else "Fallback to retriever",
        "tool": "retriever",
        "query": question,
        "tools_needed": ["retriever"],
        "retrieval_query": question,
    }


# Backwards compatibility alias
async def run_planner(
    user_query: str,
    long_term_summary: Optional[str] = None,
    recent_turns: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    return await plan(
        question=user_query,
        conversation_history=recent_turns,
        rolling_summary=long_term_summary,
    )
