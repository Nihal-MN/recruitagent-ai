"""Application settings — everything environment-driven, safe defaults.

The whole product runs without any API key: the agent falls back to a clearly
labeled deterministic demo provider that drives the *same* real tools.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

# Verified-current OpenAI model identifiers (see docs/AI_DESIGN.md); always
# overridable via OPENAI_MODEL. We never invent model names at call sites.
DEFAULT_OPENAI_MODEL = "gpt-5.6-terra"

DEFAULT_CORS_ORIGINS = (
    "http://localhost:3200,http://127.0.0.1:3200,http://localhost:3000,http://127.0.0.1:3000"
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "RecruitAgent AI"
    environment: str = "development"

    # --- AI provider ---
    # auto   → use OpenAI when OPENAI_API_KEY is set, otherwise the demo agent
    # openai → always call the OpenAI API (fails loudly if the key is missing)
    # mock   → always use the deterministic demo agent (hermetic demos/tests;
    #          "mock" is the historical name, labeled as DEMO mode in the UI)
    ai_provider: str = "auto"
    openai_api_key: str = ""
    openai_model: str = ""
    # Agent loop bounds (see docs/AGENT_DESIGN.md).
    agent_max_steps: int = 8
    agent_max_tool_calls: int = 6

    # --- Backend ---
    database_url: str = ""  # empty → SQLite fallback for dev/tests
    cors_origins: str = DEFAULT_CORS_ORIGINS
    log_level: str = "INFO"
    api_port: int = 8200

    @property
    def resolved_provider(self) -> str:
        """Which provider the runtime will actually use: "openai" or "mock"."""
        if self.ai_provider == "openai":
            return "openai" if self.openai_api_key else "openai-unconfigured"
        if self.ai_provider == "mock":
            return "mock"
        return "openai" if self.openai_api_key.strip() else "mock"

    @property
    def resolved_model(self) -> str:
        return self.openai_model.strip() or DEFAULT_OPENAI_MODEL

    @property
    def sqlalchemy_url(self) -> str:
        if self.database_url.strip():
            return self.database_url.strip()
        return "sqlite:///./recruitagent-dev.db"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
