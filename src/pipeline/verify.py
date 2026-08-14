"""Quote verification.

Every claim the model makes about the essay must be anchored to text that actually
exists in the essay. We check by exact substring match after normalisation — no fuzzy
matching. Fuzzy matching would hide the problem; we want an honest `quote_fidelity`
number telling us how often the model fabricates.
"""

from __future__ import annotations

import re

_SMART_QUOTES = str.maketrans(
    {
        "‘": "'", "’": "'", "“": '"', "”": '"',
        "–": "-", "—": "-", "…": "...", " ": " ",
    }
)
_WS_RE = re.compile(r"\s+")


def normalize(text: str) -> str:
    return _WS_RE.sub(" ", text.translate(_SMART_QUOTES).lower()).strip()


def quote_in_essay(quote: str, essay_normalized: str) -> bool:
    q = normalize(quote)
    # A one- or two-character "quote" would match trivially and tell us nothing.
    if len(q) < 4:
        return False
    return q in essay_normalized
