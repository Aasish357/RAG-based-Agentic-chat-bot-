"""
Multi-agent pipeline orchestrator for Jahiv.
Coordinates Planner, Tool Execution, Executor, Critic, and Rolling Memory.
"""

import asyncio
import logging
import math
import re
from typing import Any, Dict, List, Optional, Union

import httpx

from app.agents.critic import critique_response
from app.agents.executor import generate_response
from app.agents.planner import plan
from app.config import settings

logger = logging.getLogger("jahiv.pipeline")


async def execute_tool(
    tool_name: str,
    tool_input: str,
    **kwargs: Any,
) -> Any:
    """
    Execute an individual agent tool asynchronously.

    Args:
        tool_name: Name of tool ('retriever', 'calculator', 'document_info').
        tool_input: Input argument for the tool.
        **kwargs: Optional registry or store overrides.

    Returns:
        Tool execution output string.
    """
    # 1. Dispatch via injected registry if supplied
    registry = kwargs.get("registry")
    if registry and hasattr(registry, "dispatch"):
        result = registry.dispatch(tool_name, tool_input)
        if asyncio.iscoroutine(result):
            return await result
        return result

    # 2. Try importing tool registry from app.tools if available
    try:
        from app.tools.registry import execute_tool as reg_exec  # type: ignore
        if callable(reg_exec):
            res = reg_exec(tool_name, tool_input, **kwargs)
            if asyncio.iscoroutine(res):
                return await res
            return res
    except ImportError:
        pass

    # 3. Built-in implementations
    if tool_name == "calculator":
        try:
            safe_expr = re.sub(r"[^0-9+\-*/().^ ]", "", tool_input)
            safe_expr = safe_expr.replace("^", "**")
            result = eval(
                safe_expr,
                {"__builtins__": {}},
                {
                    "sqrt": math.sqrt,
                    "pi": math.pi,
                    "e": math.e,
                    "abs": abs,
                    "round": round,
                    "pow": pow,
                },
            )
            return f"Result: {result}"
        except Exception as exc:
            return f"Calculator error: {exc}"

    elif tool_name == "retriever":
        store = kwargs.get("store") or kwargs.get("faiss_store")
        if store and hasattr(store, "search"):
            chunks = store.search(tool_input)
            if not chunks:
                return "No relevant document content found."
            if isinstance(chunks, list):
                return "\n\n---\n\n".join(str(c) for c in chunks)
            return str(chunks)
        return "No documents indexed or vector store not connected."

    elif tool_name == "document_info":
        store = kwargs.get("store") or kwargs.get("faiss_store")
        if store and hasattr(store, "chunks"):
            if not store.chunks:
                return "No document has been uploaded yet."
            return (
                f"Document is loaded. "
                f"Total chunks indexed: {len(store.chunks)}. "
                f"Approximate pages: {len(store.chunks) // 4 + 1}."
            )
        return "No document loaded."

    return f"Unknown tool: {tool_name}"


async def summarize_history(
    to_summarise: List[Dict[str, str]],
    previous_summary: str,
) -> str:
    """
    Generate or update the long-term rolling summary using Ollama.

    Args:
        to_summarise: Conversation turns to compress.
        previous_summary: Existing rolling summary.

    Returns:
        Updated concise rolling summary string.
    """
    transcript = "\n".join(
        f"{m.get('role', 'user').upper()}: {m.get('content', '')}"
        for m in to_summarise
    )

    prompt = (
        "You are summarising a conversation for long-term memory storage.\n"
        "Produce a concise factual summary (max 200 words) covering:\n"
        "- Key topics discussed\n"
        "- Important facts or decisions\n"
        "- Any user preferences mentioned\n\n"
        f"Previous summary (if any):\n{previous_summary}\n\n"
        f"New conversation to incorporate:\n{transcript}\n\n"
        "Updated summary:"
    )

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json={"model": settings.LLM_MODEL, "prompt": prompt, "stream": False},
            )
            resp.raise_for_status()
            summary = resp.json().get("response", "").strip()
            return summary if summary else previous_summary
    except Exception as exc:
        logger.warning(f"Memory summarization call failed: {exc}")
        return previous_summary


async def run_pipeline(
    question: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    rolling_summary: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Execute full agentic RAG pipeline:
    1. Plan tool usage
    2. Execute selected tools
    3. Generate response with citations
    4. Critique response (if CRITIC_ENABLED)
    5. Update conversation memory and rolling summary

    Args:
        question: User query.
        conversation_history: List of conversation messages (modified in-place or passed).
        rolling_summary: Existing rolling summary string.
        **kwargs: Additional runtime dependencies (e.g. store, registry).

    Returns:
        Dict with keys: answer, sources, plan, critic, rolling_summary
    """
    if conversation_history is None:
        conversation_history = []
    if rolling_summary is None:
        rolling_summary = ""

    # 1. Determine recent context for prompt window
    limit_messages = settings.SHORT_TERM_LIMIT * 2
    recent_context = (
        conversation_history[-limit_messages:]
        if limit_messages > 0
        else conversation_history
    )

    # 2. Planner step
    plan_result = await plan(
        question=question,
        conversation_history=recent_context,
        rolling_summary=rolling_summary,
    )

    # 3. Tool execution step
    tool_results: Dict[str, Any] = {}
    tools_to_run: List[str] = plan_result.get("tools_needed", [])
    if not tools_to_run and plan_result.get("tool"):
        single_tool = plan_result["tool"]
        if single_tool != "none":
            tools_to_run = [single_tool]

    query_input = (
        plan_result.get("retrieval_query")
        or plan_result.get("query")
        or question
    )

    for tool_name in tools_to_run:
        if tool_name == "retriever":
            tool_input = query_input
        elif tool_name == "calculator":
            tool_input = plan_result.get("query") or question
        else:
            tool_input = plan_result.get("query", "")

        tool_results[tool_name] = await execute_tool(
            tool_name=tool_name,
            tool_input=tool_input,
            **kwargs,
        )

    # Extract source references from retriever outputs
    sources: List[Any] = []
    if "retriever" in tool_results:
        ret_val = tool_results["retriever"]
        if isinstance(ret_val, list):
            sources = ret_val
        elif (
            isinstance(ret_val, str)
            and ret_val
            and ret_val != "No relevant document content found."
            and ret_val != "No documents indexed or vector store not connected."
        ):
            sources = [s.strip() for s in ret_val.split("\n\n---\n\n") if s.strip()]

    # 4. Executor step
    draft_answer = await generate_response(
        question=question,
        tool_results=tool_results,
        plan=plan_result,
        conversation_history=recent_context,
        rolling_summary=rolling_summary,
    )

    # 5. Critic step
    critic_result: Dict[str, Any]
    if settings.CRITIC_ENABLED:
        critic_result = await critique_response(
            question=question,
            draft_answer=draft_answer,
            tool_results=tool_results,
        )
        final_answer = critic_result.get("final_answer", draft_answer)
    else:
        critic_result = {
            "verdict": "SKIPPED",
            "issues": "NONE",
            "final_answer": draft_answer,
            "raw_review": "Critic disabled via CRITIC_ENABLED configuration.",
        }
        final_answer = draft_answer

    # 6. Update conversation history
    conversation_history.append({"role": "user", "content": question})
    conversation_history.append({"role": "assistant", "content": final_answer})

    # 7. Check auto-summarization trigger
    turn_count = len(conversation_history) // 2
    if turn_count >= settings.SUMMARY_TRIGGER:
        midpoint = len(conversation_history) // 2
        to_summarise = conversation_history[:midpoint]
        conversation_history[:] = conversation_history[midpoint:]
        rolling_summary = await summarize_history(to_summarise, rolling_summary)

    return {
        "answer": final_answer,
        "sources": sources,
        "plan": plan_result,
        "critic": critic_result,
        "rolling_summary": rolling_summary,
    }
