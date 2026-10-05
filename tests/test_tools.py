import pytest
from pydantic import ValidationError

from coding_assistant.tools.handlers import ALLOWED_TEST_COMMANDS, handle_grep, handle_read_file
from coding_assistant.tools.registry import list_tools, tool_names
from coding_assistant.tools.schemas import ReadFileInput


def test_mvp_tool_names_match_contract():
    names = set(tool_names())
    expected = {
        "read_file",
        "grep",
        "search_code",
        "apply_patch",
        "run_tests",
        "lint",
        "approval_request",
    }
    assert names == expected


def test_tool_schemas_forbid_extra_fields():
    with pytest.raises(ValidationError):
        ReadFileInput.model_validate({"path": "a.py", "extra": True})


def test_registry_schemas_have_additional_properties_false():
    for tool in list_tools():
        assert tool.input_schema.get("additionalProperties") is False


@pytest.mark.asyncio
async def test_read_file_within_workspace(tmp_path):
    sample = tmp_path / "hello.py"
    sample.write_text("print('hi')\n", encoding="utf-8")
    result = await handle_read_file(tmp_path, {"path": "hello.py"})
    assert "print" in result["content"]


@pytest.mark.asyncio
async def test_read_file_rejects_path_traversal(tmp_path):
    from coding_assistant.tools.handlers import ToolExecutionError

    with pytest.raises(ToolExecutionError):
        await handle_read_file(tmp_path, {"path": "../etc/passwd"})


@pytest.mark.asyncio
async def test_grep_finds_pattern(tmp_path):
    (tmp_path / "a.py").write_text("foo = 1\nbar = 2\n", encoding="utf-8")
    result = await handle_grep(tmp_path, {"pattern": "foo"})
    assert result["match_count"] >= 1


@pytest.mark.asyncio
async def test_grep_skips_pycache(tmp_path):
    (tmp_path / "main.py").write_text("needle here\n", encoding="utf-8")
    cache = tmp_path / "__pycache__"
    cache.mkdir()
    (cache / "main.cpython-312.pyc").write_bytes(b"\x00needle\xff")
    result = await handle_grep(tmp_path, {"pattern": "needle"})
    paths = {m["path"] for m in result["matches"]}
    assert paths == {"main.py"}


def test_allowed_test_commands_non_empty():
    assert "pytest -q" in ALLOWED_TEST_COMMANDS
