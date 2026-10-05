from coding_assistant.evals.types import EvalCase, EvalCaseResult


def grade_case(case: EvalCase, success: bool, output: dict | None, error: str | None, duration_ms: float) -> EvalCaseResult:
    if not success:
        passed = not case.expect_success
        msg = error or "tool failed"
        return EvalCaseResult(
            case_id=case.id,
            category=case.category,
            passed=passed,
            message=msg,
            duration_ms=duration_ms,
            tool_output=output,
        )

    if case.expect_output_contains:
        text = str(output or "")
        if case.expect_output_contains not in text:
            return EvalCaseResult(
                case_id=case.id,
                category=case.category,
                passed=False,
                message=f"Expected output to contain {case.expect_output_contains!r}",
                duration_ms=duration_ms,
                tool_output=output,
            )

    return EvalCaseResult(
        case_id=case.id,
        category=case.category,
        passed=True,
        message="ok",
        duration_ms=duration_ms,
        tool_output=output,
    )
