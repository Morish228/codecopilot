from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Capability(str, Enum):
    """What the agent is trying to do — not which provider to call."""

    FILE_SEARCH = "file_search"
    PLANNING = "planning"
    REFACTORING = "refactoring"
    CODING = "coding"
    DEBUGGING = "debugging"
    FALLBACK = "fallback"


class Complexity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ModelRoute(BaseModel):
    """Resolved route for a single completion call."""

    model_config = ConfigDict(extra="forbid")

    capability: Capability
    complexity: Complexity
    model: str
    tier: str = Field(description="fast | reasoning | coding | fallback")


class CompletionUsage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str
    provider: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: float | None = None
    cost_usd: float | None = None


class CompletionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str
    route: ModelRoute
    usage: CompletionUsage | None = None
    attempted_models: list[str] = Field(default_factory=list)
