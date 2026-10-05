import json
import logging
from pathlib import Path
from typing import Any

from coding_assistant.config import get_settings
from coding_assistant.routing.types import Capability, Complexity, ModelRoute

logger = logging.getLogger(__name__)

TIER_NAMES = frozenset({"fast", "reasoning", "coding", "fallback"})


class ModelRouter:
    """Capability-based model selection — agents never hardcode provider models."""

    def __init__(self, config_path: Path | None = None) -> None:
        settings = get_settings()
        path = config_path or settings.routing_config_path
        self._config = _load_config(path)
        self._tiers: dict[str, str] = dict(self._config.get("tiers") or {})
        self._routes: dict[str, dict[str, str]] = dict(self._config.get("routes") or {})
        self._fallback_chain: list[str] = list(self._config.get("fallback_chain") or [])

        if settings.routing_default_model:
            logger.info("ROUTING_DEFAULT_MODEL overrides all tier models")
            for tier in TIER_NAMES:
                self._tiers[tier] = settings.routing_default_model

    def get_model(self, capability: Capability | str, complexity: Complexity | str) -> ModelRoute:
        route = self._resolve_route(capability, complexity)
        return route

    def get_models_with_fallback(
        self,
        capability: Capability | str,
        complexity: Complexity | str,
    ) -> list[str]:
        primary = self.get_model(capability, complexity)
        seen: set[str] = set()
        ordered: list[str] = []
        for model in [primary.model, *self._fallback_chain]:
            if model not in seen:
                seen.add(model)
                ordered.append(model)
        return ordered

    def list_routes(self) -> dict[str, Any]:
        """Expose routing table for debugging / API."""
        return {
            "tiers": self._tiers,
            "routes": self._routes,
            "fallback_chain": self._fallback_chain,
        }

    def _resolve_route(
        self,
        capability: Capability | str,
        complexity: Complexity | str,
    ) -> ModelRoute:
        cap = capability.value if isinstance(capability, Capability) else str(capability)
        comp = complexity.value if isinstance(complexity, Complexity) else str(complexity)

        cap_routes = self._routes.get(cap) or self._routes.get(Capability.FALLBACK.value, {})
        tier_key = cap_routes.get(comp) or cap_routes.get(Complexity.MEDIUM.value) or "fallback"

        if tier_key in TIER_NAMES:
            tier = tier_key
            model = self._tiers.get(tier) or self._tiers.get("fallback", "openai/gpt-4o-mini")
        else:
            # Allow direct litellm model id in config for advanced setups.
            tier = "custom"
            model = tier_key

        try:
            cap_enum = Capability(cap)
        except ValueError:
            cap_enum = Capability.FALLBACK
        try:
            comp_enum = Complexity(comp)
        except ValueError:
            comp_enum = Complexity.MEDIUM

        return ModelRoute(
            capability=cap_enum,
            complexity=comp_enum,
            model=model,
            tier=tier,
        )


def _load_config(path: Path) -> dict[str, Any]:
    if not path.is_file():
        logger.warning("Routing config not found at %s, using built-in defaults", path)
        return _builtin_config()
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _builtin_config() -> dict[str, Any]:
    return {
        "tiers": {
            "fast": "openai/gpt-4o-mini",
            "reasoning": "openai/gpt-4o",
            "coding": "openai/gpt-4o",
            "fallback": "openai/gpt-4o-mini",
        },
        "routes": {
            "file_search": {"low": "fast", "medium": "fast", "high": "fast"},
            "planning": {"low": "fast", "medium": "reasoning", "high": "reasoning"},
            "refactoring": {"low": "coding", "medium": "coding", "high": "coding"},
            "coding": {"low": "coding", "medium": "coding", "high": "coding"},
            "debugging": {"low": "reasoning", "medium": "reasoning", "high": "reasoning"},
            "fallback": {"low": "fallback", "medium": "fallback", "high": "fallback"},
        },
        "fallback_chain": ["openai/gpt-4o-mini"],
    }


_router: ModelRouter | None = None


def get_router() -> ModelRouter:
    global _router
    if _router is None:
        _router = ModelRouter()
    return _router


def reset_router() -> None:
    """Clear cached router (tests)."""
    global _router
    _router = None
