"""Conversation memory manager for Jahiv."""

from typing import Any, Optional

import httpx

try:
    from app.config import settings
except ImportError:
    try:
        from backend.app.config import settings
    except ImportError:
        try:
            import config as root_config

            class SettingsFallback:
                OLLAMA_BASE_URL: str = getattr(root_config, "OLLAMA_BASE_URL", "http://localhost:11434")
                LLM_MODEL: str = getattr(root_config, "LLM_MODEL", "llama3.1")
                EMBED_MODEL: str = getattr(root_config, "EMBED_MODEL", "nomic-embed-text")
                DATA_DIR: str = getattr(root_config, "UPLOAD_FOLDER", "data")
                SHORT_TERM_LIMIT: int = getattr(root_config, "SHORT_TERM_TURNS", 6)
                SUMMARY_TRIGGER: int = getattr(root_config, "LONG_TERM_SUMMARY_THRESHOLD", 12)

            settings = SettingsFallback()
        except ImportError:
            class DefaultSettings:
                OLLAMA_BASE_URL: str = "http://localhost:11434"
                LLM_MODEL: str = "llama3.1"
                EMBED_MODEL: str = "nomic-embed-text"
                DATA_DIR: str = "data"
                SHORT_TERM_LIMIT: int = 6
                SUMMARY_TRIGGER: int = 12

            settings = DefaultSettings()


class ConversationMemory:
    """
    Dual-memory system:
      - Short-term: last N turns passed directly into context
      - Long-term: a rolling LLM-generated summary of older turns
    """

    def __init__(self) -> None:
        self.history: list[dict[str, str]] = []
        self.rolling_summary: str = ""

    def add_turn(self, user_msg: str, assistant_msg: str) -> None:
        """Record a single conversational exchange (user prompt and assistant response)."""
        self.history.append({"user": user_msg, "assistant": assistant_msg})

    def get_recent_history(self) -> list[dict[str, str]]:
        """Return the last SHORT_TERM_LIMIT turns."""
        limit = getattr(settings, "SHORT_TERM_LIMIT", 6)
        return self.history[-limit:]

    def get_summary(self) -> str:
        """Return the current rolling summary."""
        return self.rolling_summary

    async def update_summary(self) -> None:
        """
        Condense history when turn count reaches SUMMARY_TRIGGER threshold and
        is a multiple of SUMMARY_TRIGGER, using Ollama asynchronously.
        """
        trigger = getattr(settings, "SUMMARY_TRIGGER", 12)
        if len(self.history) >= trigger and len(self.history) % trigger == 0:
            to_summarise = self.history[-trigger:]
            transcript_lines: list[str] = []
            for t in to_summarise:
                transcript_lines.append(f"USER: {t.get('user', '')}")
                transcript_lines.append(f"ASSISTANT: {t.get('assistant', '')}")

            transcript = "\n".join(transcript_lines)

            prompt = (
                "You are summarising a conversation for long-term memory storage.\n"
                "Produce a concise factual summary (max 200 words) covering:\n"
                "- Key topics discussed\n"
                "- Important facts or decisions\n"
                "- Any user preferences mentioned\n\n"
                f"Previous summary (if any):\n{self.rolling_summary}\n\n"
                f"New conversation to incorporate:\n{transcript}\n\n"
                "Updated summary:"
            )

            timeout = httpx.Timeout(120.0, connect=30.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{settings.OLLAMA_BASE_URL}/api/generate",
                    json={
                        "model": settings.LLM_MODEL,
                        "prompt": prompt,
                        "stream": False,
                    },
                )
                response.raise_for_status()
                data = response.json()
                new_summary = data.get("response", "").strip()
                if new_summary:
                    self.rolling_summary = new_summary

    def build_context(self) -> tuple[str, list[dict[str, str]]]:
        """
        Build context pair (summary, recent_messages) with messages
        formatted as {'role': ..., 'content': ...}.
        """
        recent_turns = self.get_recent_history()
        messages: list[dict[str, str]] = []
        for t in recent_turns:
            messages.append({"role": "user", "content": t.get("user", "")})
            messages.append({"role": "assistant", "content": t.get("assistant", "")})
        return self.rolling_summary, messages

    def clear(self) -> None:
        """Reset conversation history and rolling summary."""
        self.history = []
        self.rolling_summary = ""
