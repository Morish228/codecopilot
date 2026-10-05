import ast
import re
from pathlib import Path

from coding_assistant.tools.errors import ApprovalRequiredError, ToolExecutionError
from coding_assistant.tools.paths import APPROVAL_ACTION_TYPES, resolve_workspace_path
from coding_assistant.tools.outputs import (
    ApplyPatchOutput,
    ApprovalRequestOutput,
    GrepMatch,
    GrepOutput,
    LintIssue,
    LintOutput,
    McpInvokeOutput,
    ReadFileOutput,
    RunTestsOutput,
    SearchCodeOutput,
    SearchHit,
)
from coding_assistant.tools.schemas import (
    ApplyPatchInput,
    ApprovalRequestInput,
    GrepInput,
    LintInput,
    McpInvokeInput,
    ReadFileInput,
    RunTestsInput,
    SearchCodeInput,
)


async def read_file_handler(workspace_root: Path, data: ReadFileInput) -> ReadFileOutput:
    path = resolve_workspace_path(workspace_root, data.path)
    if not path.is_file():
        raise ToolExecutionError(f"File not found: {data.path}")
    content = path.read_text(encoding="utf-8", errors="replace")
    return ReadFileOutput(path=data.path, content=content, lines=len(content.splitlines()))


async def grep_handler(workspace_root: Path, data: GrepInput) -> GrepOutput:
    root = workspace_root.resolve()
    search_root = resolve_workspace_path(workspace_root, data.path) if data.path else root
    if not search_root.exists():
        raise ToolExecutionError(f"Search path not found: {data.path}")
    pattern = re.compile(data.pattern)
    matches: list[GrepMatch] = []
    files = [search_root] if search_root.is_file() else search_root.rglob("*")
    skip_suffixes = {".pyc", ".pyo", ".so", ".dll", ".exe", ".bin"}
    for file_path in files:
        if not file_path.is_file():
            continue
        if "__pycache__" in file_path.parts or file_path.suffix.lower() in skip_suffixes:
            continue
        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if "\x00" in text:
            continue
        for line_no, line in enumerate(text.splitlines(), start=1):
            if pattern.search(line):
                rel = str(file_path.relative_to(root))
                matches.append(GrepMatch(path=rel, line=line_no, text=line[:500]))
        if len(matches) >= 100:
            break
    return GrepOutput(pattern=data.pattern, match_count=len(matches), matches=matches)


async def search_code_handler(workspace_root: Path, data: SearchCodeInput) -> SearchCodeOutput:
    from coding_assistant.intelligence.service import fallback_text_search, search_repository

    from coding_assistant.observability.tracing import traced_span

    try:
        async with traced_span("retrieval.search_code", {"query": data.query}):
            raw_hits = await search_repository(workspace_root, data.query, data.file_pattern)
    except Exception:
        raw_hits = fallback_text_search(workspace_root, data.query, data.file_pattern)

    hits = [
        SearchHit(
            path=h.path,
            snippet=h.snippet,
            kind=h.kind,
            name=h.name,
            score=h.score,
        )
        for h in raw_hits
    ]
    return SearchCodeOutput(query=data.query, hit_count=len(hits), hits=hits)


async def apply_patch_handler(workspace_root: Path, data: ApplyPatchInput) -> ApplyPatchOutput:
    path = resolve_workspace_path(workspace_root, data.path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data.content, encoding="utf-8")
    return ApplyPatchOutput(path=data.path, bytes_written=len(data.content.encode("utf-8")))


async def run_tests_handler(workspace_root: Path, data: RunTestsInput) -> RunTestsOutput:
    import shlex

    from coding_assistant.approval.context import approval_bypass_active
    from coding_assistant.sandbox.commands import COMMAND_ARGV
    from coding_assistant.sandbox.manager import get_sandbox_manager
    from coding_assistant.tools.errors import ApprovalRequiredError
    from coding_assistant.tools.paths import ALLOWED_TEST_COMMANDS

    manager = get_sandbox_manager()
    if approval_bypass_active():
        argv = COMMAND_ARGV.get(data.command, shlex.split(data.command))
        result = await manager.run_argv(workspace_root, argv)
    else:
        if data.command not in ALLOWED_TEST_COMMANDS:
            raise ApprovalRequiredError(
                "run_tests_non_allowlisted",
                {"command": data.command, "allowed": sorted(ALLOWED_TEST_COMMANDS)},
            )
        result = await manager.run_tests(workspace_root, data.command)
    status = "passed" if result.exit_code == 0 else "failed"
    message = None if result.exit_code == 0 else f"Tests exited with code {result.exit_code}"
    return RunTestsOutput(
        status=status,
        command=data.command,
        workspace=str(workspace_root.resolve()),
        exit_code=result.exit_code,
        stdout=result.stdout,
        stderr=result.stderr,
        duration_ms=result.duration_ms,
        sandbox=result.backend,
        message=message,
    )


async def lint_handler(workspace_root: Path, data: LintInput) -> LintOutput:
    paths = data.paths or ["."]
    issues: list[LintIssue] = []
    for rel in paths:
        target = resolve_workspace_path(workspace_root, rel)
        targets = [target] if target.is_file() else target.rglob("*.py")
        for file_path in targets:
            if not file_path.is_file() or file_path.suffix != ".py":
                continue
            rel_path = str(file_path.relative_to(workspace_root.resolve()))
            try:
                source = file_path.read_text(encoding="utf-8")
                ast.parse(source, filename=rel_path)
            except SyntaxError as exc:
                issues.append(
                    LintIssue(
                        path=rel_path,
                        line=exc.lineno,
                        column=exc.offset,
                        code="syntax-error",
                        message=exc.msg or "syntax error",
                    )
                )
            except OSError as exc:
                issues.append(
                    LintIssue(
                        path=rel_path,
                        code="io-error",
                        message=str(exc),
                    )
                )
    status = "ok" if not issues else "issues_found"
    return LintOutput(status=status, issue_count=len(issues), issues=issues)


async def mcp_invoke_handler(workspace_root: Path, data: McpInvokeInput) -> McpInvokeOutput:
    from coding_assistant.config import get_settings

    _ = workspace_root
    inp = data if isinstance(data, McpInvokeInput) else McpInvokeInput.model_validate(data)
    settings = get_settings()
    if not settings.mcp_enabled:
        return McpInvokeOutput(
            connector=inp.connector,
            tool=inp.tool,
            success=False,
            error="MCP disabled",
        )

    from coding_assistant.mcp.runner import McpRunner

    result = await McpRunner().invoke(inp.connector, inp.tool, inp.arguments)
    if result.approval_required:
        from coding_assistant.tools.errors import ApprovalRequiredError

        raise ApprovalRequiredError(
            result.approval_action_type or "mcp_write",
            result.output or {},
        )
    return McpInvokeOutput(
        connector=result.connector,
        tool=result.tool,
        success=result.success,
        output=result.output,
        error=result.error,
    )


async def approval_request_handler(
    workspace_root: Path,
    data: ApprovalRequestInput,
) -> ApprovalRequestOutput:
    _ = workspace_root
    if data.action_type in APPROVAL_ACTION_TYPES or data.action_type.startswith("destructive_"):
        raise ApprovalRequiredError(data.action_type, data.model_dump())
    return ApprovalRequestOutput(
        status="recorded",
        action_type=data.action_type,
        reason=data.reason,
    )
