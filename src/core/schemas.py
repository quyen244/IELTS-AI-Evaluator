"""All data contracts. Schemas that cross the LLM boundary are marked LLM-FACING.

Field ordering in LLM-FACING models is deliberate: JSON Schema preserves property
order and constrained decoding emits tokens sequentially, so a field placed before
`band` is generated before the model commits to a score. That is how we recover the
benefit of chain-of-thought after disabling `think`.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

TaskType = Literal["task1", "task2"]
CriterionCode = Literal["TA", "TR", "CC", "LR", "GRA"]
Impact = Literal["negligible", "minor", "moderate", "major", "critical"]
Polarity = Literal["positive", "negative"]

CRITERIA_BY_TASK: dict[str, tuple[str, ...]] = {
    "task1": ("TA", "CC", "LR", "GRA"),
    "task2": ("TR", "CC", "LR", "GRA"),
}

CRITERION_NAMES: dict[str, str] = {
    "TA": "Task Achievement",
    "TR": "Task Response",
    "CC": "Coherence and Cohesion",
    "LR": "Lexical Resource",
    "GRA": "Grammatical Range and Accuracy",
}


# --------------------------------------------------------------------------- #
# Dataset
# --------------------------------------------------------------------------- #
class GoldLabel(BaseModel):
    overall: float
    criteria: dict[str, float]
    source: str
    confidence: Literal["high", "medium", "low"] = "medium"


class ExamItem(BaseModel):
    exam_id: str
    task_type: TaskType
    task_variant: str = ""
    topic: str = ""
    prompt: str
    chart_description: str | None = None
    essay: str
    gold: GoldLabel | None = None
    notes: str | None = None


# --------------------------------------------------------------------------- #
# Preprocessing (computed in code, never by the LLM)
# --------------------------------------------------------------------------- #
class TextFeatures(BaseModel):
    word_count: int
    sentence_count: int
    paragraph_count: int
    avg_sentence_length: float
    unique_words: int
    type_token_ratio: float
    repeated_content_words: list[tuple[str, int]]
    cohesive_devices_found: list[str]
    min_words_required: int
    meets_min_words: bool
    length_deficit_ratio: float


# --------------------------------------------------------------------------- #
# LLM-FACING
# --------------------------------------------------------------------------- #
class Evidence(BaseModel):
    """`verified` is set by QuoteVerifier, never by the model — see docs/02-technical/data-schemas.md."""

    quote: str = Field(description="Text copied verbatim from the student essay")
    comment: str = Field(description="Why this quote supports the assessment")
    polarity: Polarity


class CriterionResult(BaseModel):
    justification: str = Field(
        description="3-5 sentences in English explaining which band descriptor the "
        "essay matches and why. Write this BEFORE deciding the band."
    )
    band: float = Field(description="Band score from 1.0 to 9.0 in steps of 0.5")
    confidence: float = Field(description="How certain you are, 0.0 to 1.0")
    evidence: list[Evidence] = Field(description="2-4 verbatim quotes with commentary")
    strengths: list[str]
    weaknesses: list[str]
    improvements: list[str]


class SentenceIssue(BaseModel):
    original: str = Field(description="The problematic text, copied verbatim")
    corrected: str = Field(description="The corrected version")
    error_types: list[str] = Field(
        description="e.g. grammar, word choice, collocation, word form, typo, "
        "punctuation, article, tense, agreement"
    )
    impact: Impact
    explanation_vi: str = Field(description="Explanation in Vietnamese")


class SentenceIssueList(BaseModel):
    issues: list[SentenceIssue]


class PriorityAction(BaseModel):
    action: str = Field(description="A specific, imperative instruction in Vietnamese")
    criterion: CriterionCode
    expected_gain: str = Field(description='e.g. "+0.5 LR"')
    example: str = Field(description="A concrete example drawn from the analysis")


class FeedbackSummary(BaseModel):
    summary_vi: str = Field(description="3-5 sentence overall comment in Vietnamese")
    priority_actions: list[PriorityAction] = Field(description="Exactly 3 actions")
    next_band_gap: str = Field(description="In Vietnamese: what it takes to reach the next band")


# --------------------------------------------------------------------------- #
# Enriched / output-side
# --------------------------------------------------------------------------- #
class VerifiedEvidence(Evidence):
    verified: bool = False


class ScoredCriterion(BaseModel):
    criterion: CriterionCode
    name: str
    band: float | None
    raw_band: float | None = None
    length_penalty: float = 0.0
    confidence: float = 0.0
    justification: str = ""
    evidence: list[VerifiedEvidence] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    coerced: bool = False
    degraded: bool = False
    error: str | None = None


class VerifiedSentenceIssue(SentenceIssue):
    verified: bool = False


DISCLAIMER = (
    "Điểm số và nhận xét do IELTS-AI-Evaluator sinh tự động, chỉ mang tính tham khảo "
    "cho mục đích luyện tập. Đây KHÔNG phải điểm IELTS chính thức."
)


class EvaluationResult(BaseModel):
    exam_id: str | None = None
    task_type: TaskType
    overall_band: float
    raw_overall: float
    length_penalty: float = 0.0
    partial: bool = False
    criteria: dict[str, ScoredCriterion]
    sentence_issues: list[VerifiedSentenceIssue] = Field(default_factory=list)
    feedback: FeedbackSummary | None = None
    features: TextFeatures
    pipeline_version: str
    prompt_version: str
    model: str
    telemetry: "RunTelemetry"
    disclaimer: str = DISCLAIMER


# --------------------------------------------------------------------------- #
# Telemetry
# --------------------------------------------------------------------------- #
class CallRecord(BaseModel):
    node: str
    model: str
    ok: bool
    attempts: int
    latency_s: float
    prompt_tokens: int = 0
    completion_tokens: int = 0
    error: str | None = None


class RunTelemetry(BaseModel):
    run_id: str
    started_at: str
    total_latency_s: float = 0.0
    calls: list[CallRecord] = Field(default_factory=list)
    quotes_total: int = 0
    quotes_verified: int = 0

    @property
    def total_prompt_tokens(self) -> int:
        return sum(c.prompt_tokens for c in self.calls)

    @property
    def total_completion_tokens(self) -> int:
        return sum(c.completion_tokens for c in self.calls)

    @property
    def json_parse_failures(self) -> int:
        return sum(1 for c in self.calls if not c.ok)

    @property
    def retry_count(self) -> int:
        return sum(max(0, c.attempts - 1) for c in self.calls)

    @property
    def quote_fidelity(self) -> float:
        return self.quotes_verified / self.quotes_total if self.quotes_total else 1.0


EvaluationResult.model_rebuild()
