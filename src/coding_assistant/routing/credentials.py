"""Sync API keys from Settings into os.environ for LiteLLM provider discovery."""

from __future__ import annotations

import os

from coding_assistant.config import Settings, get_settings


def _set_env_if_set(name: str, value: str | None) -> None:
    if value:
        os.environ[name] = value


def configure_litellm_credentials(settings: Settings | None = None) -> None:
    """Expose configured keys to LiteLLM (reads OPENAI_*, ANTHROPIC_*, GEMINI_*, GOOGLE_*)."""
    s = settings or get_settings()
    _set_env_if_set("OPENAI_API_KEY", s.openai_api_key)
    _set_env_if_set("ANTHROPIC_API_KEY", s.anthropic_api_key)
    gemini = s.gemini_api_key or s.google_api_key
    if gemini:
        _set_env_if_set("GEMINI_API_KEY", gemini)
        _set_env_if_set("GOOGLE_API_KEY", gemini)
