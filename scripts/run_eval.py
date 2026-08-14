"""Run the benchmark over the exam dataset.

    python -m scripts.run_eval --out data/reports
    python -m scripts.run_eval --filter task2 --limit 3
"""

from __future__ import annotations

import argparse
import sys

from src.core.config import settings
from src.evaluation.dataset import load_exams
from src.evaluation.harness import run_benchmark

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(settings.reports_dir))
    ap.add_argument("--filter", choices=["task1", "task2"])
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()

    exams = load_exams(task_filter=args.filter, limit=args.limit)
    print(f"Benchmarking {len(exams)} exams with {settings.ollama_model}\n")

    out = run_benchmark(exams, out_dir=args.out)
    q = out["metrics"]["quality"]["overall"]
    s = out["metrics"]["system"]

    print("\n" + "=" * 60)
    print(f"  MAE {q.get('mae')}  ·  bias {q.get('bias'):+}  ·  "
          f"rho {q.get('spearman_rho')}")
    print(f"  within 0.5: {q.get('within_0.5'):.0%}  ·  "
          f"within 1.0: {q.get('within_1.0'):.0%}")
    print(f"  parse rate {s['json_parse_rate']:.0%}  ·  "
          f"quote fidelity {s['quote_fidelity']:.0%}  ·  "
          f"p50 {s['p50_latency_s']}s")
    print("=" * 60)


if __name__ == "__main__":
    main()
