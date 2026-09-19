"""text_metrics.py — deterministic length metrics for chapter baselines.

The week-2 length work needs a single shared length vocabulary so baseline,
quality, and comparison artifacts can speak the same units. This helper keeps
that logic read-side and deterministic.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TextLengthMetrics:
    body_chars: int
    nonspace_chars: int
    line_count: int
    paragraph_count: int
    token_estimate: int

    def to_dict(self) -> dict:
        return {
            "body_chars": self.body_chars,
            "nonspace_chars": self.nonspace_chars,
            "line_count": self.line_count,
            "paragraph_count": self.paragraph_count,
            "token_estimate": self.token_estimate,
        }


def measure_text_length(text: str) -> TextLengthMetrics:
    body = text or ""
    lines = body.splitlines()
    paragraphs = [p for p in (part.strip() for part in body.split("\n\n")) if p]
    nonspace = sum(1 for ch in body if not ch.isspace())
    # Rough deterministic estimate used for comparisons / planning only.
    token_estimate = max(1, round(nonspace / 1.7)) if nonspace else 0
    return TextLengthMetrics(
        body_chars=len(body),
        nonspace_chars=nonspace,
        line_count=len(lines),
        paragraph_count=len(paragraphs),
        token_estimate=token_estimate,
    )
