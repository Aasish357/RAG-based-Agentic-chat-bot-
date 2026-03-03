import re
import requests
from config import OLLAMA_BASE_URL, LLM_MODEL

CRITIC_SYSTEM = (
    "You are the Critic agent. Your job is to review a draft answer for quality.\n\n"
    "Check for:\n"
    "1. Hallucination — does it claim facts not present in the document context?\n"
    "2. Relevance — does it actually address the user query?\n"
    "3. Completeness — is anything important missing from the context?\n\n"
    "Respond in this EXACT format:\n"
    "VERDICT: PASS or FAIL\n"
    "ISSUES: brief description of problems, or NONE\n"
    "IMPROVED_ANSWER: improved version if FAIL, or SAME if PASS\n"
)


def run_critic(user_query, draft_answer, tool_results):
    doc_context = ""
    if tool_results.get("retriever"):
        doc_context = "[Document context used]\n" + tool_results["retriever"] + "\n\n"

    prompt = (
        CRITIC_SYSTEM + "\n\n"
        + doc_context
        + "USER QUERY: " + user_query + "\n\n"
        + "DRAFT ANSWER:\n" + draft_answer + "\n\n"
        + "Your review:"
    )

    raw = _call(prompt)

    verdict_match = re.search(r"VERDICT:\s*(\w+)", raw, re.IGNORECASE)
    verdict = verdict_match.group(1).upper() if verdict_match else "PASS"

    improved_match = re.search(r"IMPROVED_ANSWER:\s*([\s\S]+)", raw, re.IGNORECASE)
    if improved_match:
        improved = improved_match.group(1).strip()
        if improved.upper() == "SAME" or verdict == "PASS":
            final_answer = draft_answer
        else:
            final_answer = improved
    else:
        final_answer = draft_answer

    issues_match = re.search(r"ISSUES:\s*(.+)", raw, re.IGNORECASE)
    issues = issues_match.group(1).strip() if issues_match else "NONE"

    return {
        "verdict": verdict,
        "issues": issues,
        "final_answer": final_answer,
        "raw_review": raw
    }


def _call(prompt):
    r = requests.post(
        OLLAMA_BASE_URL + "/api/generate",
        json={"model": LLM_MODEL, "prompt": prompt, "stream": False}
    )
    r.raise_for_status()
    return r.json().get("response", "")
