import uuid

from coding_assistant.config import get_settings
from coding_assistant.db.session import _get_engine
from coding_assistant.runtime.approval_manager import ApprovalManager
from coding_assistant.runtime.graph import AgentRuntime
from coding_assistant.runtime.state_manager import StateManager


async def _with_runtime(callback):
    _, factory = _get_engine()
    assert factory is not None
    async with factory() as session:
        state_manager = StateManager(session)
        approval_manager = ApprovalManager(session)
        runtime = AgentRuntime(state_manager, approval_manager)
        return await callback(session, runtime, state_manager)


async def execute_run_background(
    run_id: uuid.UUID,
    workspace_root: str,
    message: str,
    max_iterations: int,
) -> None:
    async def _run(session, runtime, state_manager):
        try:
            await runtime.run(run_id, workspace_root, message, max_iterations)
        except Exception as exc:
            await session.rollback()
            run = await state_manager.get_run(run_id)
            if run:
                from coding_assistant.db.models import RunStatus

                run.status = RunStatus.FAILED
                run.error = str(exc)[:2000]
                await session.commit()

    await _with_runtime(_run)


async def resume_run_background(
    run_id: uuid.UUID,
    approval_id: uuid.UUID,
    approved: bool,
) -> None:
    async def _resume(session, runtime, state_manager):
        try:
            await runtime.resume_after_approval(run_id, approval_id, approved)
        except Exception as exc:
            await session.rollback()
            run = await state_manager.get_run(run_id)
            if run:
                from coding_assistant.db.models import RunStatus

                run.status = RunStatus.FAILED
                run.error = str(exc)[:2000]
                await session.commit()

    await _with_runtime(_resume)
