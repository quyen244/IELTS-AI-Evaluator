"""Deterministic text analysis.

Runs before any LLM call and costs nothing. Its output is injected into every scoring
prompt as ground truth, which removes a whole class of errors that a 4B model makes
reliably: counting. See docs/01-architecture/system-architecture.md § 3.1.
"""

from __future__ import annotations

import re
from collections import Counter

from src.core.config import settings as default_settings
from src.core.schemas import TextFeatures
from src.pipeline.lexicon import COHESIVE_DEVICES, STOPWORDS

WORD_RE = re.compile(r"\b[\w'-]+\b", re.UNICODE)
SENTENCE_SPLIT_RE = re.compile(r"[.!?]+(?:\s|$)")
PARAGRAPH_SPLIT_RE = re.compile(r"\n\s*\n")


def tokenize(text: str) -> list[str]:
    return WORD_RE.findall(text)


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in SENTENCE_SPLIT_RE.split(text) if s.strip()]


def split_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in PARAGRAPH_SPLIT_RE.split(text.strip()) if p.strip()]


def find_cohesive_devices(text: str) -> list[str]:
    lowered = text.lower()
    found = []
    for device in COHESIVE_DEVICES:
        if " " in device:
            if device in lowered:
                found.append(device)
        elif re.search(rf"\b{re.escape(device)}\b", lowered):
            found.append(device)
    return found


def repeated_content_words(
    words: list[str], *, min_len: int = 4, min_count: int = 3, top_n: int = 10
) -> list[tuple[str, int]]:
    counts = Counter(
        w.lower() for w in words if len(w) >= min_len and w.lower() not in STOPWORDS
    )
    return [(w, n) for w, n in counts.most_common(top_n) if n >= min_count]


def extract_features(essay: str, task_type: str, settings=None) -> TextFeatures:
    s = settings or default_settings
    words = tokenize(essay)
    sentences = split_sentences(essay)
    paragraphs = split_paragraphs(essay)

    word_count = len(words)
    sentence_count = len(sentences)
    unique = len({w.lower() for w in words})
    min_required = s.min_words(task_type)
    deficit = max(0.0, (min_required - word_count) / min_required)

    return TextFeatures(
        word_count=word_count,
        sentence_count=sentence_count,
        paragraph_count=len(paragraphs),
        avg_sentence_length=word_count / sentence_count if sentence_count else 0.0,
        unique_words=unique,
        type_token_ratio=unique / word_count if word_count else 0.0,
        repeated_content_words=repeated_content_words(words),
        cohesive_devices_found=find_cohesive_devices(essay),
        min_words_required=min_required,
        meets_min_words=word_count >= min_required,
        length_deficit_ratio=round(deficit, 4),
    )
