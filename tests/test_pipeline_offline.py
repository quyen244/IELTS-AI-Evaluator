"""End-to-end pipeline tests using a fake LLM client.

These exercise orchestration, verification, degradation and reporting without a GPU,
so a broken harness surfaces in half a second instead of at the end of a 15-minute
benchmark run.
"""

from __future__ import annotations

import json

import pytest

from src.core.schemas import (
    CriterionResult,
    EvaluationResult,
    FeedbackSummary,
    SentenceIssueList,
)
from src.evaluation.dataset import load_exams
from src.evaluation.harness import compute_metrics, render_report
from src.llm.base import LLMResponse
from src.pipeline.pipeline import EssayTooShortError, EvaluationPipeline


class FakeClient:
    """Returns schema-valid payloads. `fail_nodes` forces a node to fail."""

    model_name = "fake-model"

    def __init__(self, band: float = 6.0, fail_nodes: set[str] | None = None, quote: str | None = None):
        self.band = band
        self.fail_nodes = fail_nodes or set()
        self.quote = quote
        self.calls: list[str] = []

    def warmup(self) -> float:
        return 0.0

    def chat(self, messages, response_model=None, *, node="unknown", max_tokens=None):
        self.calls.append(node)
        if node in self.fail_nodes:
            return LLMResponse(node=node, model=self.model_name, ok=False,
                               error="forced failure", attempts=3)

        quote = self.quote or "social media"
        if response_model is CriterionResult:
            payload = CriterionResult(
                justification="Matches the descriptor.",
                band=self.band,
                confidence=0.8,
                evidence=[{"quote": quote, "comment": "c", "polarity": "negative"}],
                strengths=["s"], weaknesses=["w"], improvements=["i"],
            )
        elif response_model is SentenceIssueList:
            payload = SentenceIssueList(issues=[{
                "original": quote, "corrected": "fixed",
                "error_types": ["grammar"], "impact": "moderate",
                "explanation_vi": "giải thích",
            }])
        elif response_model is FeedbackSummary:
            payload = FeedbackSummary(
                summary_vi="tóm tắt",
                priority_actions=[{"action": "a", "criterion": "LR",
                                   "expected_gain": "+0.5 LR", "example": "e"}] * 3,
                next_band_gap="gap",
            )
        else:
            return LLMResponse(node=node, model=self.model_name, ok=True, content="ok")

        return LLMResponse(node=node, model=self.model_name, ok=True,
                           content=payload.model_dump_json(), parsed=payload,
                           prompt_tokens=100, completion_tokens=50, latency_s=0.01)


@pytest.fixture
def exams():
    return load_exams()


def _pipe(client):
    return EvaluationPipeline(client=client, warmup=False)


# ------------------------------------------------------------------ happy path
def test_pipeline_completes_and_makes_six_calls(exams):
    exam = next(e for e in exams if e.exam_id == "T2-002")
    client = FakeClient(band=6.5, quote="online learning")
    result = _pipe(client).evaluate(exam)

    assert isinstance(result, EvaluationResult)
    assert len(client.calls) == 6  # 4 criteria + corrector + synthesiser
    assert set(result.criteria) == {"TR", "CC", "LR", "GRA"}
    assert result.overall_band == 6.5
    assert result.partial is False
    assert result.feedback is not None


def test_task1_uses_ta_not_tr(exams):
    exam = next(e for e in exams if e.exam_id == "T1-002")
    result = _pipe(FakeClient(band=7.0)).evaluate(exam)
    assert "TA" in result.criteria and "TR" not in result.criteria


# ---------------------------------------------------------------- length rule
def test_length_penalty_hits_task_criterion_only(exams):
    # T2-005 is 183 words against a 250-word minimum -> 27% deficit -> 0.5 penalty.
    exam = next(e for e in exams if e.exam_id == "T2-005")
    result = _pipe(FakeClient(band=6.0)).evaluate(exam)

    assert result.criteria["TR"].band == 5.5
    assert result.criteria["TR"].raw_band == 6.0
    assert result.criteria["TR"].length_penalty == 0.5
    for code in ("CC", "LR", "GRA"):
        assert result.criteria[code].band == 6.0, f"{code} must not be penalised"
    assert result.overall_band == 6.0  # mean(5.5,6,6,6)=5.875 -> 6.0


def test_no_penalty_when_length_is_met(exams):
    exam = next(e for e in exams if e.exam_id == "T2-002")
    result = _pipe(FakeClient(band=6.0)).evaluate(exam)
    assert result.length_penalty == 0.0
    assert result.criteria["TR"].band == 6.0


# ------------------------------------------------------------- quote checking
def test_fabricated_quotes_are_flagged_not_trusted(exams):
    exam = next(e for e in exams if e.exam_id == "T2-002")
    client = FakeClient(band=6.0, quote="this sentence appears nowhere in the essay")
    result = _pipe(client).evaluate(exam)

    assert all(not e.verified for c in result.criteria.values() for e in c.evidence)
    assert result.telemetry.quote_fidelity == 0.0


def test_genuine_quotes_verify(exams):
    exam = next(e for e in exams if e.exam_id == "T2-002")
    result = _pipe(FakeClient(band=6.0, quote="online learning")).evaluate(exam)
    assert result.telemetry.quote_fidelity == 1.0


# ------------------------------------------------------------------ degrading
def test_one_failed_criterion_degrades_but_does_not_abort(exams):
    exam = next(e for e in exams if e.exam_id == "T2-002")
    result = _pipe(FakeClient(band=7.0, fail_nodes={"criterion:LR"})).evaluate(exam)

    assert result.criteria["LR"].band is None
    assert result.criteria["LR"].degraded is True
    assert result.partial is True
    assert result.overall_band == 7.0  # averaged over the surviving criteria
    assert result.telemetry.json_parse_failures == 1


def test_failed_corrector_yields_no_issues_but_still_completes(exams):
    exam = next(e for e in exams if e.exam_id == "T2-002")
    result = _pipe(FakeClient(band=6.0, fail_nodes={"corrector"})).evaluate(exam)
    assert result.sentence_issues == []
    assert result.feedback is not None


def test_essay_below_twenty_words_is_rejected_before_any_llm_call(exams):
    exam = exams[0].model_copy(update={"essay": "Too short."})
    client = FakeClient()
    with pytest.raises(EssayTooShortError):
        _pipe(client).evaluate(exam)
    assert client.calls == []


# ------------------------------------------------------------------- reporting
def test_metrics_and_report_render_over_the_whole_dataset(exams):
    client = FakeClient(band=6.0)
    pipe = _pipe(client)
    results = [pipe.evaluate(e) for e in exams]

    m = compute_metrics(exams, results, [], "test-run", 1.0)
    assert m["n_completed"] == 10
    assert m["quality"]["overall"]["n"] == 10
    assert m["quality"]["task1"]["n"] == 5 and m["quality"]["task2"]["n"] == 5
    assert set(m["quality"]["per_criterion"]) == {"TA", "TR", "CC", "LR", "GRA"}
    assert m["system"]["json_parse_rate"] == 1.0

    # A constant predictor must show zero rank correlation and a compressed spread —
    # if these come out otherwise, the metric implementation is wrong.
    assert m["quality"]["overall"]["pred_std"] == 0.0

    json.dumps(m)  # must be serialisable for metrics.json
    report = render_report(m)
    assert "Benchmark Report" in report and "T2-005" in report


def test_report_renders_with_failures_present(exams):
    client = FakeClient(band=6.0)
    pipe = _pipe(client)
    results = [pipe.evaluate(exams[0])]
    m = compute_metrics(exams[:2], results, [{"exam_id": "X", "error": "boom"}], "r", 1.0)
    assert "Failures" in render_report(m)
