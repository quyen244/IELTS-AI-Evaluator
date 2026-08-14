"""The evaluation orchestrator.

Six LLM calls per essay: four criterion scorers, one sentence corrector, one feedback
synthesiser. Everything numeric happens in code around them.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone

from src.core.config import PIPELINE_VERSION, Settings, settings as default_settings
from src.core.schemas import (
    CRITERIA_BY_TASK,
    CRITERION_NAMES,
    CallRecord,
    CriterionResult,
    EvaluationResult,
    ExamItem,
    FeedbackSummary,
    RunTelemetry,
    ScoredCriterion,
    SentenceIssueList,
    TextFeatures,
    VerifiedEvidence,
    VerifiedSentenceIssue,
)
from src.llm.base import LLMClient
from src.llm.prompts.builders import (
    PROMPT_VERSION,
    build_criterion_messages,
    build_corrector_messages,
    build_synthesizer_messages,
)
from src.llm.registry import get_client
from src.pipeline.aggregate import aggregate_overall, clamp, length_penalty, snap_band
from src.pipeline.preprocess import extract_features
from src.pipeline.verify import normalize, quote_in_essay


class EssayTooShortError(ValueError):
    pass


class EvaluationPipeline:
    def __init__(
        self,
        client: LLMClient | None = None,
        settings: Settings | None = None,
        *,
        warmup: bool = True,
        verbose: bool = False,
    ) -> None:
        self.settings = settings or default_settings
        self.client = client or get_client(self.settings)
        self.verbose = verbose
        self.warmup_s = 0.0
        if warmup:
            self.warmup_s = self.client.warmup()
            self._log(f"model warm in {self.warmup_s:.1f}s")

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(f"  [pipeline] {msg}", flush=True)

    # ------------------------------------------------------------------ #
    def evaluate(self, exam: ExamItem) -> EvaluationResult:
        started = time.perf_counter()
        telemetry = RunTelemetry(
            run_id=uuid.uuid4().hex[:12],
            started_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )

        essay = exam.essay.strip()
        if len(essay.split()) < 20:
            raise EssayTooShortError(
                "Essay is under 20 words; there is nothing meaningful to assess."
            )

        features = extract_features(essay, exam.task_type, self.settings)
        essay_norm = normalize(essay)

        criteria = self._score_criteria(exam, features, telemetry, essay_norm)
        issues = self._correct_sentences(essay, telemetry, essay_norm)

        overall, raw, partial = aggregate_overall([c.band for c in criteria.values()])
        feedback = self._synthesize(overall, criteria, issues, telemetry)

        telemetry.total_latency_s = round(time.perf_counter() - started, 2)

        return EvaluationResult(
            exam_id=exam.exam_id,
            task_type=exam.task_type,
            overall_band=overall,
            raw_overall=raw,
            length_penalty=max(
                (c.length_penalty for c in criteria.values()), default=0.0
            ),
            partial=partial,
            criteria=criteria,
            sentence_issues=issues,
            feedback=feedback,
            features=features,
            pipeline_version=PIPELINE_VERSION,
            prompt_version=PROMPT_VERSION,
            model=self.client.model_name,
            telemetry=telemetry,
        )

    # ------------------------------------------------------------------ #
    def _score_criteria(
        self,
        exam: ExamItem,
        features: TextFeatures,
        telemetry: RunTelemetry,
        essay_norm: str,
    ) -> dict[str, ScoredCriterion]:
        results: dict[str, ScoredCriterion] = {}
        penalty = length_penalty(features.length_deficit_ratio)

        for code in CRITERIA_BY_TASK[exam.task_type]:
            messages = build_criterion_messages(exam, code, features)
            resp = self.client.chat(
                messages, CriterionResult, node=f"criterion:{code}"
            )
            telemetry.calls.append(_record(resp))

            if not resp.ok or resp.parsed is None:
                self._log(f"{code}: FAILED ({resp.error})")
                results[code] = ScoredCriterion(
                    criterion=code,
                    name=CRITERION_NAMES[code],
                    band=None,
                    degraded=True,
                    error=resp.error,
                )
                continue

            parsed: CriterionResult = resp.parsed  # type: ignore[assignment]
            raw_band, coerced = snap_band(parsed.band)

            applied = penalty if code in ("TA", "TR") else 0.0
            final_band = round(clamp(raw_band - applied), 1) if applied else raw_band

            evidence = [
                VerifiedEvidence(
                    quote=e.quote,
                    comment=e.comment,
                    polarity=e.polarity,
                    verified=quote_in_essay(e.quote, essay_norm),
                )
                for e in parsed.evidence
            ]
            telemetry.quotes_total += len(evidence)
            telemetry.quotes_verified += sum(1 for e in evidence if e.verified)

            results[code] = ScoredCriterion(
                criterion=code,
                name=CRITERION_NAMES[code],
                band=final_band,
                raw_band=raw_band,
                length_penalty=applied,
                confidence=clamp(parsed.confidence, 0.0, 1.0),
                justification=parsed.justification,
                evidence=evidence,
                strengths=parsed.strengths,
                weaknesses=parsed.weaknesses,
                improvements=parsed.improvements,
                coerced=coerced,
            )
            self._log(
                f"{code}: band {final_band}"
                + (f" (raw {raw_band} - {applied} length)" if applied else "")
                + f" in {resp.latency_s:.1f}s"
            )
        return results

    # ------------------------------------------------------------------ #
    def _correct_sentences(
        self, essay: str, telemetry: RunTelemetry, essay_norm: str
    ) -> list[VerifiedSentenceIssue]:
        messages = build_corrector_messages(
            essay, self.settings.pipeline_max_sentence_issues
        )
        # This node emits N issues each with a Vietnamese explanation, so it needs a
        # far larger output budget than the single-object nodes.
        resp = self.client.chat(
            messages,
            SentenceIssueList,
            node="corrector",
            max_tokens=self.settings.llm_num_predict_corrector,
        )
        telemetry.calls.append(_record(resp))

        if not resp.ok or resp.parsed is None:
            self._log(f"corrector: FAILED ({resp.error})")
            return []

        issues = []
        for i in resp.parsed.issues[: self.settings.pipeline_max_sentence_issues]:
            verified = quote_in_essay(i.original, essay_norm)
            telemetry.quotes_total += 1
            telemetry.quotes_verified += int(verified)
            issues.append(
                VerifiedSentenceIssue(**i.model_dump(), verified=verified)
            )
        self._log(f"corrector: {len(issues)} issues in {resp.latency_s:.1f}s")
        return issues

    # ------------------------------------------------------------------ #
    def _synthesize(
        self,
        overall: float,
        criteria: dict[str, ScoredCriterion],
        issues: list[VerifiedSentenceIssue],
        telemetry: RunTelemetry,
    ) -> FeedbackSummary | None:
        # Only verified issues reach the student-facing summary.
        messages = build_synthesizer_messages(
            overall, criteria, [i for i in issues if i.verified]
        )
        resp = self.client.chat(messages, FeedbackSummary, node="synthesizer")
        telemetry.calls.append(_record(resp))
        if not resp.ok or resp.parsed is None:
            self._log(f"synthesizer: FAILED ({resp.error})")
            return None
        self._log(f"synthesizer: ok in {resp.latency_s:.1f}s")
        return resp.parsed  # type: ignore[return-value]


def _record(resp) -> CallRecord:
    return CallRecord(
        node=resp.node,
        model=resp.model,
        ok=resp.ok,
        attempts=resp.attempts,
        latency_s=round(resp.latency_s, 2),
        prompt_tokens=resp.prompt_tokens,
        completion_tokens=resp.completion_tokens,
        error=resp.error,
    )
