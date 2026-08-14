"""Grade a single essay and print a human-readable report.

    python -m scripts.run_mvp --exam-id T2-001
    python -m scripts.run_mvp --task-type task2 --prompt-file p.txt --essay-file e.txt
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.core.schemas import DISCLAIMER, ExamItem
from src.evaluation.dataset import load_exam, write_json
from src.pipeline.pipeline import EvaluationPipeline

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def build_exam(args) -> ExamItem:
    if args.exam_id:
        return load_exam(args.exam_id)
    if not (args.prompt_file and args.essay_file):
        raise SystemExit("Provide --exam-id, or both --prompt-file and --essay-file.")
    return ExamItem(
        exam_id="ad-hoc",
        task_type=args.task_type,
        prompt=Path(args.prompt_file).read_text(encoding="utf-8"),
        essay=Path(args.essay_file).read_text(encoding="utf-8"),
        chart_description=(
            Path(args.chart_file).read_text(encoding="utf-8") if args.chart_file else None
        ),
    )


def render(result) -> str:
    L = [
        "=" * 78,
        f"  {result.exam_id}  ·  {result.task_type}  ·  model {result.model}",
        "=" * 78,
        "",
        f"  OVERALL BAND: {result.overall_band}"
        + (f"   (raw {result.raw_overall})" if result.raw_overall else ""),
        "",
    ]
    if result.partial:
        L.append("  ⚠ PARTIAL RESULT — at least one criterion could not be scored.\n")

    f = result.features
    L += [
        "-" * 78,
        "  TEXT STATISTICS",
        "-" * 78,
        f"  Words {f.word_count} / {f.min_words_required} required"
        f"{'' if f.meets_min_words else '  ← BELOW MINIMUM'}",
        f"  Paragraphs {f.paragraph_count} · Sentences {f.sentence_count} · "
        f"Avg length {f.avg_sentence_length:.1f}",
        f"  Type-token ratio {f.type_token_ratio:.2f} · Unique words {f.unique_words}",
        f"  Repeated: {', '.join(f'{w}({n})' for w, n in f.repeated_content_words) or '—'}",
        "",
    ]

    for code, c in result.criteria.items():
        L += ["-" * 78, f"  {code} — {c.name}: BAND {c.band}", "-" * 78]
        if c.length_penalty:
            L.append(f"  (raw {c.raw_band} − {c.length_penalty} length penalty)")
        L += [f"  Confidence: {c.confidence:.2f}", "", f"  {c.justification}", ""]
        for label, items in (
            ("Strengths", c.strengths),
            ("Weaknesses", c.weaknesses),
            ("Improvements", c.improvements),
        ):
            if items:
                L.append(f"  {label}:")
                L += [f"    • {i}" for i in items]
        if c.evidence:
            L.append("  Evidence:")
            for e in c.evidence:
                mark = "✓" if e.verified else "✗ UNVERIFIED"
                L.append(f'    [{mark}] "{e.quote[:90]}"')
                L.append(f"           → {e.comment}")
        L.append("")

    if result.sentence_issues:
        L += ["-" * 78, "  SENTENCE-LEVEL ISSUES", "-" * 78]
        for i, iss in enumerate(result.sentence_issues, 1):
            mark = "✓" if iss.verified else "✗"
            L += [
                f"  {i}. [{iss.impact}] [{mark}] {', '.join(iss.error_types)}",
                f'     ❌ {iss.original}',
                f'     ✅ {iss.corrected}',
                f"     → {iss.explanation_vi}",
                "",
            ]

    if result.feedback:
        fb = result.feedback
        L += ["-" * 78, "  NHẬN XÉT TỔNG QUAN", "-" * 78, f"  {fb.summary_vi}", "",
              "  VIỆC CẦN LÀM (ưu tiên):"]
        for i, a in enumerate(fb.priority_actions, 1):
            L += [f"   {i}. [{a.criterion} · {a.expected_gain}] {a.action}",
                  f"      Ví dụ: {a.example}"]
        L += ["", f"  Để lên band tiếp theo: {fb.next_band_gap}", ""]

    t = result.telemetry
    L += [
        "-" * 78,
        f"  {t.total_latency_s}s · {len(t.calls)} LLM calls · "
        f"{t.total_prompt_tokens}+{t.total_completion_tokens} tokens · "
        f"{t.retry_count} retries · quote fidelity {t.quote_fidelity:.0%}",
        "-" * 78,
        f"  {DISCLAIMER}",
    ]
    return "\n".join(L)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exam-id")
    ap.add_argument("--task-type", choices=["task1", "task2"], default="task2")
    ap.add_argument("--prompt-file")
    ap.add_argument("--essay-file")
    ap.add_argument("--chart-file")
    ap.add_argument("--json-out")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    exam = build_exam(args)
    pipeline = EvaluationPipeline(verbose=not args.quiet)
    result = pipeline.evaluate(exam)

    print(render(result))
    if args.json_out:
        write_json(Path(args.json_out), result.model_dump())
        print(f"\nJSON written to {args.json_out}")


if __name__ == "__main__":
    main()
