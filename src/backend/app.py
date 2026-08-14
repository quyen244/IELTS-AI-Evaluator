"""Minimal FastAPI wrapper around EvaluationPipeline, built for the AWS demo deploy.

This is intentionally thin: it exists so the pipeline has an HTTP surface to deploy,
not as the full P1 API design (see docs/04-roadmap/roadmap.md P1.7 for that — auth,
async job queue, DB-backed history). One process, one model held warm in memory,
one endpoint that matters.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.core.schemas import EvaluationResult, ExamItem, TaskType
from src.evaluation.dataset import load_exam, load_exams
from src.pipeline.pipeline import EssayTooShortError, EvaluationPipeline

_pipeline: EvaluationPipeline | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _pipeline
    # Warm the model once at startup, not on the first request — otherwise the
    # first caller eats the ~110s cold load documented in docs/02-technical/tech-spec.md.
    _pipeline = EvaluationPipeline(warmup=True, verbose=True)
    yield
    _pipeline = None


def get_pipeline() -> EvaluationPipeline:
    """Indirection point for tests: override via app.dependency_overrides to inject
    a fake client instead of triggering the real Ollama warmup in `lifespan`."""
    if _pipeline is None:
        raise HTTPException(503, "Model not ready")
    return _pipeline


app = FastAPI(
    title="IELTS-AI-Evaluator (demo)",
    version="0.1.0",
    lifespan=lifespan,
)


class EvaluateRequest(BaseModel):
    task_type: TaskType
    prompt: str = Field(min_length=1)
    essay: str = Field(min_length=1)
    chart_description: str | None = None


@app.get("/health")
def health():
    ok = _pipeline is not None
    return JSONResponse(
        status_code=200 if ok else 503,
        content={
            "ok": ok,
            "model": _pipeline.client.model_name if ok else None,
            "warmup_s": _pipeline.warmup_s if ok else None,
        },
    )


@app.get("/exams")
def list_exams():
    """Lists the bundled sample dataset so the demo has something to click through."""
    return [
        {"exam_id": e.exam_id, "task_type": e.task_type, "topic": e.topic}
        for e in load_exams()
    ]


@app.post("/evaluate", response_model=EvaluationResult)
def evaluate(req: EvaluateRequest, pipeline: EvaluationPipeline = Depends(get_pipeline)):
    exam = ExamItem(
        exam_id="api-request",
        task_type=req.task_type,
        prompt=req.prompt,
        essay=req.essay,
        chart_description=req.chart_description,
    )
    try:
        return pipeline.evaluate(exam)
    except EssayTooShortError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/evaluate/{exam_id}", response_model=EvaluationResult)
def evaluate_sample(exam_id: str, pipeline: EvaluationPipeline = Depends(get_pipeline)):
    """Grades one of the bundled sample exams — the quickest way to demo the system."""
    try:
        exam = load_exam(exam_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    return pipeline.evaluate(exam)
