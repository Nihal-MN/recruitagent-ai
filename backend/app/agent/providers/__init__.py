"""Provider factory. ``auto`` → OpenAI when a key is configured, else demo."""

from __future__ import annotations

from app.agent.providers.base import Provider
from app.core.config import get_settings


def get_provider() -> Provider:
    settings = get_settings()
    resolved = settings.resolved_provider
    if resolved == "openai":
        from app.agent.providers.openai_provider import OpenAIProvider

        return OpenAIProvider()
    from app.agent.providers.demo import DemoProvider

    return DemoProvider()
