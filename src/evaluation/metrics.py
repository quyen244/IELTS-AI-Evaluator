"""Scoring metrics.

Pure Python, no numpy/scipy dependency — these are small samples and the formulas are
short enough that adding a dependency would cost more than it saves.

Read `spearman_rho` before `mae`. See docs/03-evaluation/evaluation-protocol.md § 3.2
for why ranking quality matters more than absolute error at this stage.
"""

from __future__ import annotations

import math
from statistics import mean, pstdev


def mae(pred: list[float], gold: list[float]) -> float:
    return mean(abs(p - g) for p, g in zip(pred, gold))


def rmse(pred: list[float], gold: list[float]) -> float:
    return math.sqrt(mean((p - g) ** 2 for p, g in zip(pred, gold)))


def bias(pred: list[float], gold: list[float]) -> float:
    """Signed error. Positive means the system scores more generously than gold."""
    return mean(p - g for p, g in zip(pred, gold))


def within(pred: list[float], gold: list[float], tol: float) -> float:
    if not pred:
        return 0.0
    return sum(abs(p - g) <= tol + 1e-9 for p, g in zip(pred, gold)) / len(pred)


def _rank(values: list[float]) -> list[float]:
    """Average ranks, handling ties."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def spearman_rho(pred: list[float], gold: list[float]) -> float:
    """Rank correlation via Pearson on ranks (correct in the presence of ties)."""
    if len(pred) < 3:
        return float("nan")
    rp, rg = _rank(pred), _rank(gold)
    mp, mg = mean(rp), mean(rg)
    num = sum((a - mp) * (b - mg) for a, b in zip(rp, rg))
    den = math.sqrt(sum((a - mp) ** 2 for a in rp) * sum((b - mg) ** 2 for b in rg))
    return num / den if den else float("nan")


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    idx = min(len(s) - 1, max(0, int(round(q * (len(s) - 1)))))
    return s[idx]


def score_block(pred: list[float], gold: list[float]) -> dict:
    if not pred:
        return {"n": 0}
    gs = pstdev(gold) if len(gold) > 1 else 0.0
    ps = pstdev(pred) if len(pred) > 1 else 0.0
    return {
        "n": len(pred),
        "mae": round(mae(pred, gold), 3),
        "rmse": round(rmse(pred, gold), 3),
        "bias": round(bias(pred, gold), 3),
        "within_0.5": round(within(pred, gold, 0.5), 3),
        "within_1.0": round(within(pred, gold, 1.0), 3),
        "spearman_rho": round(spearman_rho(pred, gold), 3),
        "pred_std": round(ps, 3),
        "gold_std": round(gs, 3),
        # < 1 means the system compresses the band range (central tendency bias)
        "std_ratio": round(ps / gs, 3) if gs else None,
    }
