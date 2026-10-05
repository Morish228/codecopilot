import json
from pathlib import Path

from coding_assistant.evals.types import EvalCase

_DATASETS_DIR = Path(__file__).resolve().parents[3] / "evals" / "datasets"


def datasets_dir() -> Path:
    return _DATASETS_DIR


def load_dataset(name: str) -> list[EvalCase]:
    path = _DATASETS_DIR / f"{name}.json"
    if not path.is_file():
        raise FileNotFoundError(f"Dataset not found: {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [EvalCase.model_validate(item) for item in raw]


def list_datasets() -> list[str]:
    if not _DATASETS_DIR.is_dir():
        return []
    return sorted(p.stem for p in _DATASETS_DIR.glob("*.json"))
