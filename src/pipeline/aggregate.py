"""Arithmetic. No LLM involvement — see docs/adr/0003-deterministic-band-aggregation.md."""

from __future__ import annotations

import math

BAND_MIN, BAND_MAX = 1.0, 9.0


def clamp(value: float, low: float = BAND_MIN, high: float = BAND_MAX) -> float:
    return max(low, min(high, value))


def round_to_half(value: float) -> float:
    """Round to the nearest 0.5, rounding .25/.75 UP as IELTS does.

    Python's built-in round() uses banker's rounding, which gets midpoints wrong here,
    so the arithmetic is done explicitly.
    """
    return math.floor(value * 2 + 0.5) / 2


def snap_band(value: float) -> tuple[float, bool]:
    """Clamp to [1, 9] and snap to a multiple of 0.5. Returns (band, was_coerced)."""
    snapped = round_to_half(clamp(value))
    return snapped, abs(snapped - value) > 1e-9


def length_penalty(deficit_ratio: float) -> float:
    """Penalty applied to the Task Achievement / Task Response band only.

    Real examiners absorb under-length into TA/TR rather than deducting from the
    overall band, so applying it here avoids double-counting. The scoring prompt for
    TA/TR is explicitly told not to deduct for length itself.
    """
    if deficit_ratio > 0.40:
        return 1.0
    if deficit_ratio > 0.15:
        return 0.5
    return 0.0


def aggregate_overall(bands: list[float | None]) -> tuple[float, float, bool]:
    """Return (overall_band, raw_mean, partial).

    `partial` is True when at least one criterion is missing, so a degraded run is
    never silently presented as a complete one.
    """
    present = [b for b in bands if b is not None]
    if not present:
        return 0.0, 0.0, True
    raw = sum(present) / len(present)
    return round_to_half(clamp(raw)), round(raw, 4), len(present) < len(bands)
