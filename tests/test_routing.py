import json

import pytest

from coding_assistant.config import get_settings
from coding_assistant.routing.policy import infer_capability_and_complexity
from coding_assistant.routing.router import ModelRouter, reset_router
from coding_assistant.routing.types import Capability, Complexity
from coding_assistant.runtime.types import ToolResult, initial_state


@pytest.fixture
def routing_config(tmp_path):
    config = {
        "tiers": {
            "fast": "openai/fast-model",
            "reasoning": "openai/reasoning-model",
            "coding": "anthropic/coding-model",
            "fallback": "openai/fallback-model",
        },
        "routes": {
            "planning": {"low": "fast", "medium": "reasoning", "high": "reasoning"},
            "file_search": {"low": "fast", "medium": "fast", "high": "fast"},
            "fallback": {"low": "fallback", "medium": "fallback", "high": "fallback"},
        },
        "fallback_chain": ["openai/fallback-model", "anthropic/backup-model"],
    }
    path = tmp_path / "routing.config.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    return path


@pytest.fixture(autouse=True)
def _reset_router(monkeypatch):
    monkeypatch.setenv("ROUTING_DEFAULT_MODEL", "")
    reset_router()
    get_settings.cache_clear()
    yield
    reset_router()
    get_settings.cache_clear()


def test_get_model_planning_high(routing_config, monkeypatch):
    monkeypatch.setenv("ROUTING_CONFIG_PATH", str(routing_config))
    get_settings.cache_clear()
    reset_router()

    route = ModelRouter().get_model(Capability.PLANNING, Complexity.HIGH)
    assert route.model == "openai/reasoning-model"
    assert route.tier == "reasoning"


def test_get_model_file_search_low(routing_config, monkeypatch):
    monkeypatch.setenv("ROUTING_CONFIG_PATH", str(routing_config))
    get_settings.cache_clear()
    reset_router()

    route = ModelRouter().get_model(Capability.FILE_SEARCH, Complexity.LOW)
    assert route.model == "openai/fast-model"
    assert route.tier == "fast"


def test_fallback_chain_dedupes_primary(routing_config, monkeypatch):
    monkeypatch.setenv("ROUTING_CONFIG_PATH", str(routing_config))
    get_settings.cache_clear()
    reset_router()

    models = ModelRouter().get_models_with_fallback(Capability.FALLBACK, Complexity.LOW)
    assert models[0] == "openai/fallback-model"
    assert models == ["openai/fallback-model", "anthropic/backup-model"]


def test_infer_planning_on_first_iteration():
    state = initial_state("r1", "/tmp/ws", "Add logging to the API", max_iterations=10)
    cap, comp = infer_capability_and_complexity(state)
    assert cap == Capability.PLANNING
    assert comp == Complexity.HIGH


def test_infer_fallback_after_tool_failure():
    state = initial_state("r1", "/tmp/ws", "Do something", max_iterations=10)
    state["iteration"] = 2
    state["tool_results"] = [
        ToolResult(tool="grep", arguments={}, success=False, error="timeout"),
    ]
    cap, comp = infer_capability_and_complexity(state)
    assert cap == Capability.FALLBACK
    assert comp == Complexity.LOW


def test_infer_debugging_from_user_message():
    state = initial_state("r1", "/tmp/ws", "Fix this bug in the auth module", max_iterations=10)
    state["iteration"] = 2
    cap, comp = infer_capability_and_complexity(state)
    assert cap == Capability.DEBUGGING
    assert comp == Complexity.HIGH


def test_infer_coding_after_apply_patch():
    state = initial_state("r1", "/tmp/ws", "Update the handler", max_iterations=10)
    state["iteration"] = 2
    state["tool_results"] = [
        ToolResult(
            tool="apply_patch",
            arguments={"path": "a.py"},
            success=True,
            output={"bytes_written": 10},
        ),
    ]
    cap, comp = infer_capability_and_complexity(state)
    assert cap == Capability.CODING
    assert comp == Complexity.HIGH
