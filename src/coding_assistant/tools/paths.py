from pathlib import Path

from coding_assistant.tools.errors import ToolExecutionError

ALLOWED_TEST_COMMANDS = frozenset({"pytest -q", "pytest", "python -m pytest -q"})

APPROVAL_ACTION_TYPES = frozenset(
    {
        "rm",
        "git_reset",
        "git_push",
        "pip_install",
        "npm_install",
        "network_access",
        "environment_modifications",
    }
)


def resolve_workspace_path(workspace_root: Path, relative_path: str) -> Path:
    root = workspace_root.resolve()
    target = (root / relative_path).resolve()
    # Containment must be path-component aware: a raw prefix test would let
    # a sibling like "/ws-secret" pass as being inside "/ws".
    if target != root and root not in target.parents:
        raise ToolExecutionError(f"Path escapes workspace: {relative_path}")
    return target
