from fastapi import APIRouter, HTTPException

from coding_assistant.evals.dataset import list_datasets
from coding_assistant.evals.runner import EvalRunner
from coding_assistant.evals.types import EvalReport

router = APIRouter(prefix="/v1/evals", tags=["evals"])


@router.get("/datasets")
async def get_datasets() -> dict:
    return {"datasets": list_datasets()}


@router.post("/run/{dataset_name}", response_model=EvalReport)
async def run_eval(dataset_name: str) -> EvalReport:
    if dataset_name not in list_datasets():
        raise HTTPException(status_code=404, detail=f"Unknown dataset: {dataset_name}")
    runner = EvalRunner()
    return await runner.run_dataset(dataset_name)
