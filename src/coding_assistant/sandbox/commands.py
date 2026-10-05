"""Allowlisted test commands → fixed argv (never shell)."""

from coding_assistant.tools.errors import ApprovalRequiredError
from coding_assistant.tools.paths import ALLOWED_TEST_COMMANDS

COMMAND_ARGV: dict[str, list[str]] = {
    "pytest -q": ["pytest", "-q"],
    "pytest": ["pytest"],
    "python -m pytest -q": ["python", "-m", "pytest", "-q"],
}


def parse_allowlisted_command(command: str) -> list[str]:
    if command not in ALLOWED_TEST_COMMANDS:
        raise ApprovalRequiredError(
            "run_tests_non_allowlisted",
            {"command": command, "allowed": sorted(ALLOWED_TEST_COMMANDS)},
        )
    argv = COMMAND_ARGV.get(command)
    if argv is None:
        raise ApprovalRequiredError(
            "run_tests_non_allowlisted",
            {"command": command, "allowed": sorted(ALLOWED_TEST_COMMANDS)},
        )
    return list(argv)
