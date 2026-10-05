import logging
import time
from typing import Any

import litellm

from coding_assistant.observability.langfuse_integration import log_llm_generation
from coding_assistant.observability.metrics import record_llm
from coding_assistant.observability.tracing import traced_span
from coding_assistant.routing.router import ModelRouter, get_router
from coding_assistant.routing.types import Capability, Complexity, CompletionResult, CompletionUsage, ModelRoute

logger = logging.getLogger(__name__)


class RoutedCompletionService:
    """LiteLLM completions with capability routing and provider fallback."""

    def __init__(self, router: ModelRouter | None = None) -> None:
        self._router = router or get_router()

    async def complete(
        self,
        *,
        capability: Capability | str,
        complexity: Complexity | str,
        messages: list[dict[str, Any]],
        response_format: dict[str, Any] | None = None,
        temperature: float = 0.2,
        run_id: str | None = None,
        **kwargs: Any,
    ) -> CompletionResult:
        cap = capability.value if hasattr(capability, "value") else str(capability)
        comp = complexity.value if hasattr(complexity, "value") else str(complexity)

        async with traced_span(
            "planning",
            {
                "llm.capability": cap,
                "llm.complexity": comp,
                "run.id": run_id,
            },
        ):
            route = self._router.get_model(capability, complexity)
            models = self._router.get_models_with_fallback(capability, complexity)
            last_error: Exception | None = None

            for model in models:
                started = time.perf_counter()
                try:
                    response = await litellm.acompletion(
                        model=model,
                        messages=messages,
                        response_format=response_format,
                        temperature=temperature,
                        **kwargs,
                    )
                    latency_ms = (time.perf_counter() - started) * 1000
                    duration_s = latency_ms / 1000
                    content = response.choices[0].message.content or ""
                    usage = _extract_usage(response, model, latency_ms)
                    resolved_route = ModelRoute(
                        capability=route.capability,
                        complexity=route.complexity,
                        model=model,
                        tier=route.tier if model == route.model else "fallback",
                    )
                    result = CompletionResult(
                        content=content,
                        route=resolved_route,
                        usage=usage,
                        attempted_models=models[: models.index(model) + 1],
                    )
                    record_llm(
                        model,
                        "ok",
                        duration_s,
                        usage.input_tokens if usage else None,
                        usage.output_tokens if usage else None,
                    )
                    log_llm_generation(
                        run_id=run_id,
                        capability=cap,
                        complexity=comp,
                        messages=messages,
                        result=result,
                    )
                    return result
                except Exception as exc:
                    last_error = exc
                    record_llm(model, "error", time.perf_counter() - started, None, None)
                    logger.warning("Model %s failed (%s), trying fallback", model, exc)

            assert last_error is not None
            raise last_error


def _extract_usage(response: Any, model: str, latency_ms: float) -> CompletionUsage | None:
    usage_obj = getattr(response, "usage", None)
    if usage_obj is None:
        return CompletionUsage(model=model, latency_ms=latency_ms)

    provider = model.split("/")[0] if "/" in model else None
    cost = None
    try:
        cost = litellm.completion_cost(completion_response=response)
    except Exception:
        pass

    return CompletionUsage(
        model=model,
        provider=provider,
        input_tokens=getattr(usage_obj, "prompt_tokens", None),
        output_tokens=getattr(usage_obj, "completion_tokens", None),
        latency_ms=latency_ms,
        cost_usd=cost,
    )
