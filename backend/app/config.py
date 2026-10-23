"""
Configuration management for Jahiv backend using Pydantic Settings.
Reads environment variables from .env file or environment with default fallbacks.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    HOST: str = "0.0.0.0"
    PORT: int = 8000
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    LLM_MODEL: str = "llama3.1"
    EMBED_MODEL: str = "nomic-embed-text"
    TOP_K: int = 5
    CONFIDENCE_THRESHOLD: float = 0.4
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 100
    SHORT_TERM_LIMIT: int = 6
    SUMMARY_TRIGGER: int = 12
    CRITIC_ENABLED: bool = True
    DATA_DIR: str = "data"
    MAX_UPLOAD_SIZE_MB: int = 50


settings = Settings()

__all__ = ["Settings", "settings"]
