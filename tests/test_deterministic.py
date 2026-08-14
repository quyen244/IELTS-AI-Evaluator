"""Tests for the deterministic half of the system.

These must never be flaky: no LLM, no GPU, no network. If anything here fails, the
arithmetic that the whole scoring system rests on is wrong.
"""

from __future__ import annotations

import pytest

from src.core.schemas import ExamItem
from src.evaluation.dataset import load_exams
from src.evaluation.metrics import bias, mae, spearman_rho, within
from src.pipeline.aggregate import (
    aggregate_overall,
    clamp,
    length_penalty,
    round_to_half,
    snap_band,
)
from src.pipeline.preprocess import extract_features
from src.pipeline.verify import normalize, quote_in_essay


# --------------------------------------------------------------------- rounding
@pytest.mark.parametrize(
    "value,expected",
    [
        (6.0, 6.0), (6.1, 6.0), (6.24, 6.0),
        (6.25, 6.5),   # IELTS rounds the midpoint UP, unlike Python's round()
        (6.4, 6.5), (6.5, 6.5), (6.74, 6.5),
        (6.75, 7.0),   # ditto
        (6.9, 7.0), (5.875, 6.0), (4.875, 5.0),
    ],
)
def test_round_to_half(value, expected):
    assert round_to_half(value) == expected


def test_round_to_half_beats_banker_rounding():
    # Python's round(6.25, 1) == 6.2 (banker's); IELTS requires 6.5.
    assert round_to_half(6.25) == 6.5
    assert round_to_half(7.25) == 7.5


def test_clamp():
    assert clamp(0.2) == 1.0
    assert clamp(12.0) == 9.0
    assert clamp(6.5) == 6.5


@pytest.mark.parametrize(
    "raw,band,coerced",
    [(6.5, 6.5, False), (6.3, 6.5, True), (11.0, 9.0, True), (0.0, 1.0, True)],
)
def test_snap_band(raw, band, coerced):
    assert snap_band(raw) == (band, coerced)


# --------------------------------------------------------------------- penalty
@pytest.mark.parametrize(
    "deficit,expected",
    [(0.0, 0.0), (0.06, 0.0), (0.15, 0.0), (0.16, 0.5), (0.30, 0.5), (0.41, 1.0)],
)
def test_length_penalty(deficit, expected):
    assert length_penalty(deficit) == expected


def test_aggregate_overall():
    band, raw, partial = aggregate_overall([6.0, 6.5, 6.0, 5.5])
    assert (band, partial) == (6.0, False)
    assert raw == 6.0


def test_aggregate_rounds_up_at_quarter():
    band, raw, _ = aggregate_overall([6.5, 6.5, 6.0, 6.0])
    assert raw == 6.25 and band == 6.5


def test_aggregate_flags_partial_when_a_criterion_is_missing():
    band, _, partial = aggregate_overall([6.0, None, 6.0, 6.0])
    assert partial is True and band == 6.0


def test_aggregate_all_missing():
    assert aggregate_overall([None, None]) == (0.0, 0.0, True)


# ------------------------------------------------------------------ preprocess
SAMPLE = (
    "The government should invest in education. Education is the key to growth.\n\n"
    "However, education alone is not enough. For example, health matters too."
)


def test_extract_features_counts():
    f = extract_features(SAMPLE, "task2")
    assert f.paragraph_count == 2
    assert f.sentence_count == 4
    assert f.word_count == len(SAMPLE.split())
    assert 0 < f.type_token_ratio <= 1


def test_extract_features_detects_cohesive_devices():
    f = extract_features(SAMPLE, "task2")
    assert "however" in f.cohesive_devices_found
    assert "for example" in f.cohesive_devices_found


def test_extract_features_repeated_words_excludes_stopwords():
    f = extract_features(SAMPLE, "task2")
    words = dict(f.repeated_content_words)
    assert words.get("education") == 3
    assert "the" not in words


def test_length_deficit_and_minimum():
    f = extract_features("word " * 100, "task2")
    assert f.min_words_required == 250
    assert f.meets_min_words is False
    assert f.length_deficit_ratio == pytest.approx(0.6)


# ---------------------------------------------------------------------- quotes
def test_quote_verification_exact_and_normalised():
    essay = "The  government   should invest in “education” — heavily."
    norm = normalize(essay)
    assert quote_in_essay("the government should invest", norm)
    assert quote_in_essay('"education"', norm)          # smart quotes normalised
    assert quote_in_essay('"education" - heavily', norm)  # em dash normalised


def test_quote_verification_requires_contiguous_text():
    # Skipping over intervening characters must NOT count as a match.
    norm = normalize('invest in "education" - heavily')
    assert not quote_in_essay("education - heavily", norm)


def test_quote_verification_rejects_fabrication():
    norm = normalize("The government should invest in education.")
    assert not quote_in_essay("The government must abolish taxation", norm)


def test_quote_verification_rejects_trivially_short_quotes():
    norm = normalize("The government should invest in education.")
    assert not quote_in_essay("in", norm)


# --------------------------------------------------------------------- metrics
def test_metric_basics():
    pred, gold = [6.0, 7.0, 5.0], [6.5, 7.0, 4.5]
    assert mae(pred, gold) == pytest.approx(1.0 / 3)
    assert bias(pred, gold) == pytest.approx(0.0)
    assert within(pred, gold, 0.5) == 1.0


def test_spearman_detects_perfect_and_inverted_ranking():
    assert spearman_rho([1, 2, 3, 4], [2, 4, 6, 8]) == pytest.approx(1.0)
    assert spearman_rho([1, 2, 3, 4], [8, 6, 4, 2]) == pytest.approx(-1.0)


def test_spearman_handles_ties():
    rho = spearman_rho([5.0, 5.0, 7.0, 8.0], [5.0, 6.0, 7.0, 8.0])
    assert 0.8 <= rho <= 1.0


# --------------------------------------------------------------------- dataset
def test_dataset_loads_and_is_internally_consistent():
    exams = load_exams()
    assert len(exams) == 10
    assert sum(e.task_type == "task1" for e in exams) == 5
    assert sum(e.task_type == "task2" for e in exams) == 5

    for e in exams:
        assert isinstance(e, ExamItem)
        assert e.gold is not None, f"{e.exam_id} has no gold label"
        expected = {"TA", "CC", "LR", "GRA"} if e.task_type == "task1" else {
            "TR", "CC", "LR", "GRA"
        }
        assert set(e.gold.criteria) == expected, e.exam_id
        for band in e.gold.criteria.values():
            assert 1.0 <= band <= 9.0 and band * 2 == int(band * 2)
        # Gold overall must be the rounded mean of its own criteria, or the
        # dataset contradicts the aggregation rule the pipeline is measured against.
        mean = sum(e.gold.criteria.values()) / 4
        assert e.gold.overall == round_to_half(mean), (
            f"{e.exam_id}: overall {e.gold.overall} != round({mean:.3f})"
        )


def test_dataset_covers_the_band_range():
    golds = [e.gold.overall for e in load_exams()]
    assert min(golds) <= 5.0 and max(golds) >= 7.5
