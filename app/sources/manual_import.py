from __future__ import annotations

import json
from pathlib import Path

from app.models import JobApplication


def import_json(path: str | Path) -> list[JobApplication]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    items = payload if isinstance(payload, list) else [payload]
    return [JobApplication.model_validate(item) for item in items]
