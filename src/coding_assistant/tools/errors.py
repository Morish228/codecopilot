from typing import Any


class ToolExecutionError(Exception):
    pass


class ApprovalRequiredError(Exception):
    def __init__(self, action_type: str, payload: dict[str, Any]) -> None:
        self.action_type = action_type
        self.payload = payload
        super().__init__(f"Approval required for action: {action_type}")
