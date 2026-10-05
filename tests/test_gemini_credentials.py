import os

import pytest

from coding_assistant.config import get_settings
from coding_assistant.routing.credentials import configure_litellm_credentials


@pytest.fixture(autouse=True)
def _clear_settings_cache(monkeypatch):
    monkeypatch.setenv("ROUTING_DEFAULT_MODEL", "")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_configure_gemini_key(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    get_settings.cache_clear()

    configure_litellm_credentials()

    assert os.environ.get("GEMINI_API_KEY") == "test-gemini-key"
    assert os.environ.get("GOOGLE_API_KEY") == "test-gemini-key"


def test_google_api_key_alias(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setenv("GOOGLE_API_KEY", "google-key-only")
    get_settings.cache_clear()

    configure_litellm_credentials()

    assert os.environ.get("GEMINI_API_KEY") == "google-key-only"
    assert os.environ.get("GOOGLE_API_KEY") == "google-key-only"


def test_gemini_router_config(tmp_path, monkeypatch):
    gemini_config = tmp_path / "routing.config.gemini.json"
    gemini_config.write_text(
        '{"tiers":{"fast":"gemini/gemini-2.0-flash","reasoning":"gemini/gemini-2.0-flash",'
        '"coding":"gemini/gemini-2.0-flash","fallback":"gemini/gemini-2.0-flash"},'
        '"routes":{"planning":{"high":"reasoning"}},'
        '"fallback_chain":["gemini/gemini-2.0-flash"]}',
        encoding="utf-8",
    )
    monkeypatch.setenv("ROUTING_CONFIG_PATH", str(gemini_config))
    get_settings.cache_clear()

    from coding_assistant.routing.router import ModelRouter, reset_router
    from coding_assistant.routing.types import Capability, Complexity

    reset_router()
    route = ModelRouter().get_model(Capability.PLANNING, Complexity.HIGH)
    assert route.model == "gemini/gemini-2.0-flash"
    assert route.model.startswith("gemini/")
