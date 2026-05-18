"""Central configuration. All runtime knobs live here so guardrails and budgets are explicit."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Loaded from environment / .env. See .env.example for documentation."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="",
        case_sensitive=True,
        extra="ignore",
    )

    # --- Secrets ---
    ANTHROPIC_API_KEY: str = Field(..., description="Anthropic API key")
    TAVILY_API_KEY: str = Field(..., description="Tavily search API key")

    # --- Models ---
    ATLAS_MODEL_REASONING: str = "claude-sonnet-4-6"
    ATLAS_MODEL_FAST: str = "claude-haiku-4-5-20251001"

    # --- Budgets / hard caps (defense-in-depth) ---
    ATLAS_MAX_SUBQUESTIONS: int = 5
    ATLAS_MAX_SEARCH_CALLS: int = 10
    ATLAS_MAX_CRITIC_RETRIES: int = 1
    ATLAS_MAX_TOKENS_PER_AGENT: int = 4000
    ATLAS_REQUEST_TIMEOUT_S: int = 120

    # --- Logging ---
    ATLAS_LOG_LEVEL: str = "INFO"


_settings: Settings | None = None


def get_settings() -> Settings:
    """Cached settings accessor."""
    global _settings
    if _settings is None:
        _settings = Settings()  # type: ignore[call-arg]
    return _settings
