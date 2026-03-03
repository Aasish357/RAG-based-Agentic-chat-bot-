# memory/store.py — Short-term + Long-term conversation memory

import requests
from config import (
    OLLAMA_BASE_URL, LLM_MODEL,
    SHORT_TERM_TURNS, LONG_TERM_SUMMARY_THRESHOLD
)


class ConversationMemory:
    """
    Dual-memory system:
      - Short-term : last N turn pairs passed directly into context
      - Long-term  : a rolling LLM-generated summary of older turns
    """

    def __init__(self):
        self.short_term = []
        self.long_term_summary = ""

    def add_turn(self, user_msg: str, assistant_msg: str):
        self.short_term.append({"role": "user",      "content": user_msg})
        self.short_term.append({"role": "assistant",  "content": assistant_msg})
        if len(self.short_term) // 2 >= LONG_TERM_SUMMARY_THRESHOLD:
            self._compress()

    def build_context(self):
        recent = self.short_term[-(SHORT_TERM_TURNS * 2):]
        return self.long_term_summary, recent

    def clear(self):
        self.short_term = []
        self.long_term_summary = ""

    def _compress(self):
        midpoint = len(self.short_term) // 2
        to_summarise = self.short_term[:midpoint]
        self.short_term = self.short_term[midpoint:]

        transcript = "\n".join(
            f"{m['role'].upper()}: {m['content']}" for m in to_summarise
        )

        prompt = (
            "You are summarising a conversation for long-term memory storage.\n"
            "Produce a concise factual summary (max 200 words) covering:\n"
            "- Key topics discussed\n"
            "- Important facts or decisions\n"
            "- Any user preferences mentioned\n\n"
            f"Previous summary (if any):\n{self.long_term_summary}\n\n"
            f"New conversation to incorporate:\n{transcript}\n\n"
            "Updated summary:"
        )

        summary = _call_ollama(prompt)
        self.long_term_summary = summary.strip()
        print(f"[Memory] Long-term summary updated ({len(self.long_term_summary)} chars)")


def _call_ollama(prompt: str) -> str:
    response = requests.post(
        f"{OLLAMA_BASE_URL}/api/generate",
        json={"model": LLM_MODEL, "prompt": prompt, "stream": False}
    )
    response.raise_for_status()
    return response.json().get("response", "")
