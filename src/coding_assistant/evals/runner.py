import time
from pathlib import Path

from coding_assistant.config import get_settings
from coding_assistant.evals.dataset import datasets_dir, load_dataset
from coding_assistant.evals.grader import grade_case
from coding_assistant.evals.types import EvalCaseResult, EvalReport
from coding_assistant.tools.registry import get_registered_tool


class EvalRunner:
    """Run tool-level eval cases against fixture workspaces (no LLM required)."""

    def __init__(self, fixtures_root: Path | None = None) -> None:
        settings = get_settings()
        self._fixtures_root = fixtures_root or (datasets_dir() / "fixtures")
        self._sandbox_backend = settings.sandbox_backend

    async def run_dataset(self, name: str) -> EvalReport:
        cases = load_dataset(name)
        results: list[EvalCaseResult] = []

        for case in cases:
            started = time.perf_counter()
            workspace = self._fixtures_root / case.workspace_fixture
            tool = get_registered_tool(case.tool)
            if tool is None:
                results.append(
                    EvalCaseResult(
                        case_id=case.id,
                        category=case.category,
                        passed=False,
                        message=f"Unknown tool: {case.tool}",
                        duration_ms=0,
                    )
                )
                continue

            try:
                output = await tool.execute(workspace, case.arguments)
                duration_ms = (time.perf_counter() - started) * 1000
                results.append(grade_case(case, True, output, None, duration_ms))
            except Exception as exc:
                duration_ms = (time.perf_counter() - started) * 1000
                results.append(grade_case(case, False, None, str(exc), duration_ms))

        passed = sum(1 for r in results if r.passed)
        total = len(results)
        avg = sum(r.duration_ms for r in results) / total if total else 0.0

        return EvalReport(
            dataset=name,
            total=total,
            passed=passed,
            failed=total - passed,
            success_rate=passed / total if total else 0.0,
            results=results,
            avg_duration_ms=avg,
        )
