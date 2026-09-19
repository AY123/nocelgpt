"""quality_snapshot.py — lightweight chapter quality snapshot helper.

This utility turns a chapter body into a small, structured quality snapshot
using the existing deterministic prose-hygiene detectors. It is advisory only
and intended for baseline comparison, not gating.
"""
from __future__ import annotations

from typing import Optional

from ..execution.prose_hygiene import hygiene_findings, _warning_count
from .text_metrics import measure_text_length
from .text_language import measure_text_language



QUALITY_SNAPSHOT_KIND = "quality_snapshot"
QUALITY_SNAPSHOT_VERSION = "1.0"


def build_quality_snapshot(*,
                           chapter_id: str,
                           body: str,
                           objective: Optional[dict] = None,
                           reference_profile: Optional[dict] = None) -> dict:
    artifact = {"body": body}
    findings = hygiene_findings(
        artifact,
        objective=objective,
        reference_profile=reference_profile,
    )
    length = measure_text_length(body)
    language = measure_text_language(body)
    return {
        "kind": QUALITY_SNAPSHOT_KIND,
        "version": QUALITY_SNAPSHOT_VERSION,
        "chapter_id": chapter_id,
        "warning_count": _warning_count(
            artifact,
            objective=objective,
            reference_profile=reference_profile,
        ),
        "length": {
            "body_chars": length.body_chars,
            "nonspace_chars": length.nonspace_chars,
            "line_count": length.line_count,
            "paragraph_count": length.paragraph_count,
            "token_estimate": length.token_estimate,
        },
        "language": {
            "body_chars": language.body_chars,
            "ascii_word_count": language.ascii_word_count,
            "chinese_char_count": language.chinese_char_count,
            "ascii_ratio": language.ascii_ratio,
            "chinese_ratio": language.chinese_ratio,
            "long_ascii_run": language.long_ascii_run,
            "english_dominant": language.english_dominant,
        },
        "findings": [
            {
                "check": f.check,
                "severity": f.severity,
                "message": f.message,
            }
            for f in findings
        ],
    }


def compare_quality_snapshots(left: dict, right: dict) -> dict:
    left_count = int(left.get("warning_count", 0) or 0)
    right_count = int(right.get("warning_count", 0) or 0)
    delta = right_count - left_count
    if delta < 0:
        verdict = "improved"
    elif delta > 0:
        verdict = "regressed"
    else:
        verdict = "unchanged"
    return {
        "kind": "quality_snapshot_comparison",
        "version": QUALITY_SNAPSHOT_VERSION,
        "left": {
            "chapter_id": left.get("chapter_id"),
            "warning_count": left_count,
        },
        "right": {
            "chapter_id": right.get("chapter_id"),
            "warning_count": right_count,
        },
        "delta": delta,
        "verdict": verdict,
        "shared_findings": [
            item for item in left.get("findings", [])
            if item in right.get("findings", [])
        ],
    }
