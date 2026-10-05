import pytest

from coding_assistant.approval.policy import action_type_for_tool, requires_approval
from coding_assistant.runtime.types import PendingApproval, StructuredAction
from coding_assistant.runtime.approval_manager import ApprovalManager


def test_requires_approval_actions():
    assert requires_approval("git_push")
    assert requires_approval("run_tests_non_allowlisted")
    assert not requires_approval("read_file")


def test_action_type_for_run_tests():
    assert action_type_for_tool("run_tests", {"command": "make test"}) == "run_tests_non_allowlisted"
    assert action_type_for_tool("run_tests", {"command": "pytest -q"}) is None


def test_pending_approval_serializes_deferred_action():
    pending = PendingApproval(
        approval_id="abc",
        action_type="git_push",
        payload={},
        deferred_action=StructuredAction(tool="approval_request", arguments={"action_type": "git_push", "reason": "x"}),
    )
    data = pending.model_dump()
    assert data["deferred_action"]["tool"] == "approval_request"


def test_approval_manager_deferred_from_record():
    from coding_assistant.db.models import ApprovalRequest, ApprovalStatus
    import uuid

    record = ApprovalRequest(
        id=uuid.uuid4(),
        run_id=uuid.uuid4(),
        action_type="rm",
        payload={
            "deferred_action": {
                "tool": "run_tests",
                "arguments": {"command": "pytest -q"},
            }
        },
        status=ApprovalStatus.PENDING,
    )
    mgr = ApprovalManager(session=None)  # type: ignore[arg-type]
    action = mgr.deferred_action_from_record(record)
    assert action is not None
    assert action.tool == "run_tests"
