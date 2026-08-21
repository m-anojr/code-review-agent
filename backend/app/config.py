"""
Centralised configuration management.

All settings are loaded from environment variables with sensible defaults.
Uses Pydantic Settings for validation and type coercion.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration — loaded from env vars / .env file."""

    # --- GitHub ---
    GITHUB_TOKEN: str = ""
    GITHUB_WEBHOOK_SECRET: str = ""  # HMAC secret for webhook signature verification

    # --- LLM Providers ---
    GROQ_API_KEY: str = ""
    GEMINI_API_KEY: str = ""

    # ASSUMPTION: Groq is primary (free, fast), Gemini is fallback.
    PRIMARY_MODEL: str = "llama-3.3-70b-versatile"
    FALLBACK_MODEL: str = "gemini-2.0-flash"

    # --- Agent ---
    AGENT_MAX_ITERATIONS: int = 5  # Max ReAct loop iterations per file
    AGENT_TOKEN_BUDGET: int = 32000  # Max tokens per PR review
    AGENT_CONFIDENCE_THRESHOLD: float = 0.7  # Drop findings below this
    AGENT_TEMPERATURE: float = 0.0  # Deterministic output

    # --- Retrieval ---
    CHROMA_PERSIST_DIR: str = "./data/chroma"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"  # sentence-transformers model

    # --- Sandboxing ---
    SANDBOX_TIMEOUT_SECONDS: int = 30  # Max execution time for linter/tests
    SANDBOX_MAX_OUTPUT_BYTES: int = 50000  # Truncate tool output beyond this

    # --- Rate Limiting ---
    RATE_LIMIT_PER_MINUTE: int = 10  # Max reviews per minute
    PER_PR_COST_CAP_USD: float = 0.05  # ASSUMPTION: ~$0.05 max per PR on Groq free tier

    # --- Database ---
    DB_PATH: str = os.getenv("DB_PATH", "reviews.db")

    # --- Server ---
    ENVIRONMENT: str = "development"  # development | staging | production
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:5173",
    ]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Singleton accessor for settings. Cached after first call."""
    return Settings()
