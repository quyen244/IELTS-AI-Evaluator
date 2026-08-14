"""API-layer tests using the same fake LLM client as test_pipeline_offline.py.

The FastAPI `lifespan` triggers a real Ollama warmup, so these tests never construct
TestClient as a context manager (which would run it) and instead override the
`get_pipeline` dependency directly — no GPU, no network, runs in CI.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.backend.app import app, get_pipeline
from src.pipeline.pipeline import EvaluationPipeline
from tests.test_pipeline_offline import FakeClient


def _client(band: float = 6.0) -> TestClient:
    fake = FakeClient(band=band, quote="online learning")
    pipeline = EvaluationPipeline(client=fake, warmup=False)
    app.dependency_overrides[get_pipeline] = lambda: pipeline
    return TestClient(app)


def teardown_function():
    app.dependency_overrides.clear()


def test_health_reports_not_ready_before_lifespan_runs():
    # Constructed without `with`, so lifespan never fires and the module-level
    # _pipeline stays None — this is the state right after container start.
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 503
    assert resp.json()["ok"] is False


def test_list_exams_returns_all_ten():
    client = _client()
    resp = client.get("/exams")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 10
    assert {e["task_type"] for e in body} == {"task1", "task2"}


def test_evaluate_ad_hoc_essay():
    client = _client(band=6.5)
    resp = client.post(
        "/evaluate",
        json={
            "task_type": "task2",
            "prompt": "Discuss both views on online learning.",
            "essay": "Online learning is convenient. " * 15,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["overall_band"] == 6.5
    assert body["task_type"] == "task2"


def test_evaluate_rejects_essay_under_twenty_words():
    client = _client()
    resp = client.post(
        "/evaluate",
        json={"task_type": "task2", "prompt": "p", "essay": "Too short."},
    )
    assert resp.status_code == 422


def test_evaluate_sample_by_exam_id():
    client = _client(band=7.0)
    resp = client.post("/evaluate/T2-002")
    assert resp.status_code == 200
    assert resp.json()["exam_id"] == "T2-002"


def test_evaluate_sample_unknown_id_is_404():
    client = _client()
    resp = client.post("/evaluate/DOES-NOT-EXIST")
    assert resp.status_code == 404


def test_evaluate_without_pipeline_ready_is_503():
    # No override installed and lifespan never ran -> get_pipeline raises 503.
    app.dependency_overrides.clear()
    client = TestClient(app)
    resp = client.post(
        "/evaluate",
        json={"task_type": "task2", "prompt": "p", "essay": "word " * 30},
    )
    assert resp.status_code == 503
