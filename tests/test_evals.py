import pytest

from coding_assistant.evals.dataset import load_dataset
from coding_assistant.evals.runner import EvalRunner


def test_load_smoke_dataset():
    cases = load_dataset("smoke")
    assert len(cases) >= 3


@pytest.mark.asyncio
async def test_run_smoke_eval():
    report = await EvalRunner().run_dataset("smoke")
    assert report.total == len(report.results)
    assert report.success_rate >= 0.5
