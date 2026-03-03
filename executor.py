import requests
from config import OLLAMA_BASE_URL, LLM_MODEL
from registry import ToolRegistry

EXECUTOR_SYSTEM = (
    "You are the Executor agent. Your job is to synthesise tool results and\n"
    "conversation context into a clear, accurate, helpful answer.\n\n"
    "Rules:\n"
    "- Answer ONLY from the provided context and tool results.\n"
    "- If the document context does not contain the answer, say so honestly.\n"
    "- Do NOT make up facts or figures.\n"
    "- Be concise and direct.\n"
)


def run_executor(user_query, plan_output, tool_results, long_term_summary, recent_turns, tools):
    context_block = ""

    if long_term_summary:
        context_block += "[Conversation history summary]\n" + long_term_summary + "\n\n"

    if recent_turns:
        context_block += "[Recent conversation]\n"
        for m in recent_turns[-6:]:
            context_block += m["role"].upper() + ": " + m["content"] + "\n"
        context_block += "\n"

    if tool_results:
        context_block += "[Tool results]\n"
        for tool_name, result in tool_results.items():
            context_block += "Tool: " + tool_name + "\n" + result + "\n\n"

    prompt = (
        EXECUTOR_SYSTEM + "\n\n"
        + context_block
        + "[Planner notes]\n" + plan_output + "\n\n"
        + "USER QUERY: " + user_query + "\n\n"
        + "Your answer:"
    )

    return _call(prompt)


def run_tools(plan, registry):
    results = {}
    for tool_name in plan["tools_needed"]:
        if tool_name == "retriever" and plan["retrieval_query"]:
            results["retriever"] = registry.dispatch("retriever", plan["retrieval_query"])
        elif tool_name in ("calculator", "document_info"):
            results[tool_name] = registry.dispatch(tool_name, "")
    return results


def _call(prompt):
    r = requests.post(
        OLLAMA_BASE_URL + "/api/generate",
        json={"model": LLM_MODEL, "prompt": prompt, "stream": False}
    )
    r.raise_for_status()
    return r.json().get("response", "")
