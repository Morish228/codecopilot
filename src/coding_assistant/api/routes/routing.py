from fastapi import APIRouter, Query

from coding_assistant.routing.router import get_router
from coding_assistant.routing.types import Capability, Complexity

router = APIRouter(prefix="/v1/routing", tags=["routing"])


@router.get("")
async def get_routing_table() -> dict:
    """Return configured tiers, capability routes, and fallback chain."""
    return get_router().list_routes()


@router.get("/resolve")
async def resolve_model(
    capability: Capability = Query(default=Capability.PLANNING),
    complexity: Complexity = Query(default=Complexity.HIGH),
) -> dict:
    """Preview which model would be selected for a capability/complexity pair."""
    route = get_router().get_model(capability, complexity)
    models = get_router().get_models_with_fallback(capability, complexity)
    return {
        "capability": route.capability.value,
        "complexity": route.complexity.value,
        "model": route.model,
        "tier": route.tier,
        "fallback_chain": models,
    }
