from __future__ import annotations
from pathlib import Path
from rfc2spec.models.schemas import SegmentedDoc
import json

def load_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")

def save_json(path: str, obj) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")

def load_segmented(path: str) -> SegmentedDoc:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return SegmentedDoc.model_validate(data)
