"""HTTP client for the coding-assistant API (used by terminal chat)."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from collections.abc import Callable
from typing import Any

import httpx


class ApiError(Exception):
    """API request failed."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass
class RunView:
    id: uuid.UUID
    status: str
    final_response: str | None
    error: str | None


@dataclass
class ApprovalView:
    id: uuid.UUID
    action_type: str
    payload: dict[str, Any]


class ApiClient:
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000",
        *,
        token: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._base = base_url.rstrip("/")
        headers: dict[str, str] = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._http = httpx.Client(
            base_url=self._base,
            headers=headers,
            timeout=timeout,
        )

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> ApiClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def health(self) -> bool:
        try:
            resp = self._http.get("/health")
            return resp.status_code == 200 and resp.json().get("status") == "ok"
        except httpx.HTTPError:
            return False

    def create_run(self, workspace_root: str, message: str) -> RunView:
        resp = self._http.post(
            "/v1/runs",
            json={"workspace_root": workspace_root, "message": message},
        )
        if resp.status_code not in (200, 202):
            raise ApiError(_error_detail(resp), status_code=resp.status_code)
        return _parse_run(resp.json())

    def get_run(self, run_id: uuid.UUID) -> RunView:
        resp = self._http.get(f"/v1/runs/{run_id}")
        if resp.status_code != 200:
            raise ApiError(_error_detail(resp), status_code=resp.status_code)
        return _parse_run(resp.json())

    def list_pending_approvals(self, run_id: uuid.UUID) -> list[ApprovalView]:
        resp = self._http.get(f"/v1/runs/{run_id}/approvals")
        if resp.status_code != 200:
            raise ApiError(_error_detail(resp), status_code=resp.status_code)
        return [
            ApprovalView(
                id=uuid.UUID(str(item["id"])),
                action_type=item["action_type"],
                payload=item.get("payload") or {},
            )
            for item in resp.json()
        ]

    def decide_approval(self, run_id: uuid.UUID, approval_id: uuid.UUID, approved: bool) -> RunView:
        resp = self._http.post(
            f"/v1/runs/{run_id}/approvals/{approval_id}",
            json={"approved": approved},
        )
        if resp.status_code != 200:
            raise ApiError(_error_detail(resp), status_code=resp.status_code)
        return _parse_run(resp.json())

    def wait_for_run(
        self,
        run_id: uuid.UUID,
        *,
        poll_interval: float = 1.0,
        timeout_seconds: float = 300.0,
        on_status: Callable[[str], None] | None = None,
        on_approval: Callable[[ApprovalView], bool] | None = None,
    ) -> RunView:
        """Poll until completed/failed/cancelled; handle approvals via callback."""
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            run = self.get_run(run_id)
            if on_status:
                on_status(run.status)

            if run.status == "awaiting_approval":
                approvals = self.list_pending_approvals(run_id)
                if not approvals:
                    time.sleep(poll_interval)
                    continue
                for approval in approvals:
                    approved = True
                    if on_approval:
                        approved = on_approval(approval)
                    self.decide_approval(run_id, approval.id, approved)
                time.sleep(poll_interval)
                continue

            if run.status in ("completed", "failed", "cancelled"):
                return run

            time.sleep(poll_interval)

        raise ApiError(f"Run {run_id} timed out after {timeout_seconds:.0f}s")


def _parse_run(data: dict[str, Any]) -> RunView:
    return RunView(
        id=uuid.UUID(str(data["id"])),
        status=data["status"],
        final_response=data.get("final_response"),
        error=data.get("error"),
    )


def _error_detail(resp: httpx.Response) -> str:
    try:
        body = resp.json()
        if isinstance(body, dict) and "detail" in body:
            return str(body["detail"])
    except Exception:
        pass
    return f"HTTP {resp.status_code}: {resp.text[:200]}"
