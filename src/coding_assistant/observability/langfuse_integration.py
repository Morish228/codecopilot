"""Optional Langfuse logging for LLM generations."""

import logging
from typing import Any

from coding_assistant.config import get_settings
from coding_assistant.routing.types import CompletionResult

logger = logging.getLogger(__name__)
_client = None
_checked = False


def _get_client():
    global _client, _checked
    if _checked:
        return _client
    _checked = True
    settings = get_settings()
    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        return None
    try:
        from langfuse import Langfuse

        _client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
    except Exception as exc:
        logger.warning("Langfuse init failed: %s", exc)
        _client = None
    return _client


def log_llm_generation(
    *,
    run_id: str | None,
    capability: str,
    complexity: str,
    messages: list[dict[str, Any]],
    result: CompletionResult,
) -> None:
    client = _get_client()
    if client is None:
        return

    usage = result.usage
    try:
        trace = client.trace(name="agent.run", id=run_id) if run_id else client.trace(name="planner")
        gen = trace.generation(
            name="planning",
            model=result.route.model,
            input=messages,
            output=result.content,
            metadata={
                "capability": capability,
                "complexity": complexity,
                "tier": result.route.tier,
                "attempted_models": result.attempted_models,
            },
        )
        if usage and (usage.input_tokens or usage.output_tokens):
            gen.update(
                usage={
                    "input": usage.input_tokens or 0,
                    "output": usage.output_tokens or 0,
                },
                metadata={
                    "cost_usd": usage.cost_usd,
                    "latency_ms": usage.latency_ms,
                    "provider": usage.provider,
                },
            )
    except Exception as exc:
        logger.debug("Langfuse log failed: %s", exc)
