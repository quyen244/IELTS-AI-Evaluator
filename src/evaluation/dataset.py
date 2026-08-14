"""Dataset loading."""

from __future__ import annotations

import json
from pathlib import Path

from src.core.config import settings as default_settings
from src.core.schemas import ExamItem


def load_exams(
    exams_dir: Path | None = None,
    *,
    task_filter: str | None = None,
    limit: int | None = None,
) -> list[ExamItem]:
    root = exams_dir or default_settings.exams_dir
    files = sorted(root.glob("*/*.json"))
    if not files:
        raise FileNotFoundError(f"No exam files found under {root}")

    exams = [ExamItem.model_validate_json(f.read_text(encoding="utf-8")) for f in files]
    if task_filter:
        exams = [e for e in exams if e.task_type == task_filter]
    if limit:
        exams = exams[:limit]
    return exams


def load_exam(exam_id: str, exams_dir: Path | None = None) -> ExamItem:
    for exam in load_exams(exams_dir):
        if exam.exam_id == exam_id:
            return exam
    raise KeyError(f"No exam with id {exam_id!r}")


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
