import pytest
from pydantic import ValidationError

from coding_assistant.runtime.tool_executor import ToolExecutor
from coding_assistant.runtime.types import StructuredAction, initial_state
from coding_assistant.tools.registry import list_tools, openai_tool_specs
from coding_assistant.tools.schema_builder import strict_json_schema
from coding_assistant.tools.schemas import GrepInput, ReadFileInput
from coding_assistant.tools.validation import ToolValidationError, validate_tool_arguments


def _all_nested_objects_strict(schema: dict, path: str = "root") -> list[str]:
    violations = []
    if isinstance(schema, dict):
        if schema.get("type") == "object" or "properties" in schema:
            if schema.get("additionalProperties") is not False:
                violations.append(path)
        for key, value in schema.items():
            violations.extend(_all_nested_objects_strict(value, f"{path}.{key}"))
    return violations


def test_tool_definitions_use_schema_key():
    for tool in list_tools():
        assert tool.input_schema.get("type") == "object"
        assert tool.input_schema.get("additionalProperties") is False
        assert tool.output_schema.get("additionalProperties") is False


def test_nested_additional_properties_false():
    for tool in list_tools():
        violations = _all_nested_objects_strict(tool.input_schema)
        assert violations == [], f"{tool.name} schema violations: {violations}"


def test_openai_specs_match_registry():
    specs = openai_tool_specs()
    assert len(specs) == 7
    for spec in specs:
        assert spec["type"] == "function"
        params = spec["function"]["parameters"]
        assert params["additionalProperties"] is False


def test_validate_rejects_unknown_tool():
    with pytest.raises(ToolValidationError):
        validate_tool_arguments("not_a_tool", {})


def test_validate_rejects_extra_properties():
    with pytest.raises((ToolValidationError, ValidationError)):
        validate_tool_arguments("read_file", {"path": "a.py", "extra": 1})


def test_strict_schema_marks_required_fields():
    schema = strict_json_schema(ReadFileInput)
    assert "path" in schema.get("required", [])


@pytest.mark.asyncio
async def test_executor_rejects_invalid_arguments(tmp_path):
    state = initial_state("r1", str(tmp_path), "test", max_iterations=5)
    executor = ToolExecutor()
    results, _ = await executor.execute_actions(
        state,
        [StructuredAction(tool="read_file", arguments={"bad": True})],
    )
    assert results[0].success is False
    assert "read_file" in (results[0].error or "")


@pytest.mark.asyncio
async def test_lint_returns_deterministic_syntax_issue(tmp_path):
    bad = tmp_path / "bad.py"
    bad.write_text("def broken(\n", encoding="utf-8")
    from coding_assistant.tools.handlers import handle_lint

    out = await handle_lint(tmp_path, {"paths": ["bad.py"]})
    assert out["status"] == "issues_found"
    assert out["issue_count"] >= 1
    assert out["issues"][0]["code"] == "syntax-error"


def test_grep_input_schema():
    schema = strict_json_schema(GrepInput)
    assert schema["additionalProperties"] is False
