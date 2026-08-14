"""Benchmark harness: run the pipeline over the dataset and report measured quality."""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from src.core.config import PIPELINE_VERSION, settings as default_settings
from src.core.schemas import EvaluationResult, ExamItem
from src.evaluation.dataset import write_json
from src.evaluation.metrics import percentile, score_block
from src.llm.prompts.builders import PROMPT_VERSION
from src.pipeline.pipeline import EvaluationPipeline

ALL_CRITERIA = ("TA", "TR", "CC", "LR", "GRA")


def run_benchmark(
    exams: list[ExamItem],
    pipeline: EvaluationPipeline | None = None,
    *,
    out_dir: Path | None = None,
    verbose: bool = True,
) -> dict:
    pipe = pipeline or EvaluationPipeline(verbose=verbose)
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:4]

    results: list[EvaluationResult] = []
    failures: list[dict] = []
    started = time.perf_counter()

    for idx, exam in enumerate(exams, 1):
        if verbose:
            gold = exam.gold.overall if exam.gold else "?"
            print(f"[{idx}/{len(exams)}] {exam.exam_id} (gold {gold})", flush=True)
        try:
            results.append(pipe.evaluate(exam))
        except Exception as exc:
            print(f"    ERROR: {type(exc).__name__}: {exc}", flush=True)
            failures.append({"exam_id": exam.exam_id, "error": f"{type(exc).__name__}: {exc}"})

    wall = time.perf_counter() - started
    metrics = compute_metrics(exams, results, failures, run_id, wall)

    if out_dir:
        base = Path(out_dir) / run_id
        write_json(base / "raw_results.json", [r.model_dump() for r in results])
        write_json(base / "metrics.json", metrics)
        (base / "report.md").write_text(render_report(metrics), encoding="utf-8")
        if verbose:
            print(f"\nWrote {base}")

    return {"run_id": run_id, "metrics": metrics, "results": results}


# --------------------------------------------------------------------------- #
def compute_metrics(
    exams: list[ExamItem],
    results: list[EvaluationResult],
    failures: list[dict],
    run_id: str,
    wall_s: float,
) -> dict:
    by_id = {e.exam_id: e for e in exams}

    overall_pred, overall_gold, per_item = [], [], []
    crit_pairs: dict[str, tuple[list[float], list[float]]] = {
        c: ([], []) for c in ALL_CRITERIA
    }
    latencies, calls_ok, calls_total = [], 0, 0
    first_try_ok, quotes_total, quotes_ok = 0, 0, 0
    prompt_tok, completion_tok, degraded, empty_evidence, crit_total = 0, 0, 0, 0, 0

    for r in results:
        exam = by_id[r.exam_id]
        latencies.append(r.telemetry.total_latency_s)
        for c in r.telemetry.calls:
            calls_total += 1
            calls_ok += int(c.ok)
            first_try_ok += int(c.ok and c.attempts == 1)
            prompt_tok += c.prompt_tokens
            completion_tok += c.completion_tokens
        quotes_total += r.telemetry.quotes_total
        quotes_ok += r.telemetry.quotes_verified
        degraded += int(r.partial)

        for code, sc in r.criteria.items():
            crit_total += 1
            if not sc.evidence:
                empty_evidence += 1
            if exam.gold and code in exam.gold.criteria and sc.band is not None:
                crit_pairs[code][0].append(sc.band)
                crit_pairs[code][1].append(exam.gold.criteria[code])

        if exam.gold:
            overall_pred.append(r.overall_band)
            overall_gold.append(exam.gold.overall)
            per_item.append(
                {
                    "exam_id": r.exam_id,
                    "task_type": r.task_type,
                    "gold": exam.gold.overall,
                    "pred": r.overall_band,
                    "error": round(r.overall_band - exam.gold.overall, 2),
                    "raw_overall": r.raw_overall,
                    "length_penalty": r.length_penalty,
                    "criteria": {
                        c: {"pred": s.band, "gold": exam.gold.criteria.get(c)}
                        for c, s in r.criteria.items()
                    },
                    "latency_s": r.telemetry.total_latency_s,
                    "quote_fidelity": round(r.telemetry.quote_fidelity, 3),
                }
            )

    task1 = [p for p in per_item if p["task_type"] == "task1"]
    task2 = [p for p in per_item if p["task_type"] == "task2"]

    return {
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "pipeline_version": PIPELINE_VERSION,
        "prompt_version": PROMPT_VERSION,
        "model": default_settings.ollama_model,
        "temperature": default_settings.llm_temperature,
        "enable_thinking": default_settings.llm_enable_thinking,
        "n_exams": len(exams),
        "n_completed": len(results),
        "failures": failures,
        "wall_clock_s": round(wall_s, 1),
        "quality": {
            "overall": score_block(overall_pred, overall_gold),
            "task1": score_block(
                [p["pred"] for p in task1], [p["gold"] for p in task1]
            ),
            "task2": score_block(
                [p["pred"] for p in task2], [p["gold"] for p in task2]
            ),
            "per_criterion": {
                c: score_block(p, g) for c, (p, g) in crit_pairs.items() if p
            },
        },
        "system": {
            "json_parse_rate": round(calls_ok / calls_total, 4) if calls_total else 0,
            "first_attempt_parse_rate": (
                round(first_try_ok / calls_total, 4) if calls_total else 0
            ),
            "quote_fidelity": round(quotes_ok / quotes_total, 4) if quotes_total else 0,
            "quotes_total": quotes_total,
            "empty_evidence_rate": (
                round(empty_evidence / crit_total, 4) if crit_total else 0
            ),
            "degraded_rate": round(degraded / len(results), 4) if results else 0,
            "llm_calls": calls_total,
            "p50_latency_s": round(percentile(latencies, 0.50), 1),
            "p95_latency_s": round(percentile(latencies, 0.95), 1),
            "mean_latency_s": (
                round(sum(latencies) / len(latencies), 1) if latencies else 0
            ),
            "prompt_tokens_total": prompt_tok,
            "completion_tokens_total": completion_tok,
            "tokens_per_essay": (
                round((prompt_tok + completion_tok) / len(results)) if results else 0
            ),
        },
        "per_item": per_item,
    }


# --------------------------------------------------------------------------- #
def render_report(m: dict) -> str:
    q, s = m["quality"], m["system"]
    o = q["overall"]

    lines = [
        f"# Benchmark Report — {m['run_id']}",
        "",
        f"- Model: `{m['model']}` · temperature `{m['temperature']}` · "
        f"enable_thinking `{m['enable_thinking']}`",
        f"- Pipeline: `{m['pipeline_version']}` · Prompts: `{m['prompt_version']}`",
        f"- Exams: {m['n_completed']}/{m['n_exams']} completed · "
        f"wall clock {m['wall_clock_s']}s",
        "",
        "## Scoring quality (overall band vs gold)",
        "",
        "| Metric | Value |",
        "| --- | --- |",
    ]
    for k in ("n", "mae", "rmse", "bias", "within_0.5", "within_1.0",
              "spearman_rho", "pred_std", "gold_std", "std_ratio"):
        lines.append(f"| `{k}` | {o.get(k)} |")

    lines += ["", "## By task type", "", "| Task | n | MAE | bias | within_0.5 | rho |",
              "| --- | --- | --- | --- | --- | --- |"]
    for name in ("task1", "task2"):
        b = q[name]
        if b.get("n"):
            lines.append(
                f"| {name} | {b['n']} | {b['mae']} | {b['bias']} | "
                f"{b['within_0.5']} | {b['spearman_rho']} |"
            )

    lines += ["", "## Per criterion", "",
              "| Criterion | n | MAE | bias | within_0.5 | std_ratio |",
              "| --- | --- | --- | --- | --- | --- |"]
    for c, b in q["per_criterion"].items():
        lines.append(
            f"| {c} | {b['n']} | {b['mae']} | {b['bias']} | "
            f"{b['within_0.5']} | {b['std_ratio']} |"
        )

    lines += ["", "## System quality", "", "| Metric | Value |", "| --- | --- |"]
    for k, v in s.items():
        lines.append(f"| `{k}` | {v} |")

    lines += ["", "## Per item", "",
              "| Exam | Gold | Pred | Error | Raw | Penalty | Latency | Quote fidelity |",
              "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for p in m["per_item"]:
        lines.append(
            f"| {p['exam_id']} | {p['gold']} | {p['pred']} | {p['error']:+.1f} | "
            f"{p['raw_overall']} | {p['length_penalty']} | {p['latency_s']}s | "
            f"{p['quote_fidelity']} |"
        )

    if m["failures"]:
        lines += ["", "## Failures", ""]
        lines += [f"- `{f['exam_id']}`: {f['error']}" for f in m["failures"]]

    return "\n".join(lines) + "\n"
