from pydantic import BaseModel, ConfigDict, Field


class EvalCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    category: str
    description: str = ""
    workspace_fixture: str = Field(description="Subdirectory under evals/datasets/fixtures/")
    tool: str
    arguments: dict = Field(default_factory=dict)
    expect_success: bool = True
    expect_output_contains: str | None = None


class EvalCaseResult(BaseModel):
    case_id: str
    category: str
    passed: bool
    message: str
    duration_ms: float
    tool_output: dict | None = None


class EvalReport(BaseModel):
    dataset: str
    total: int
    passed: int
    failed: int
    success_rate: float
    results: list[EvalCaseResult]
    avg_duration_ms: float
