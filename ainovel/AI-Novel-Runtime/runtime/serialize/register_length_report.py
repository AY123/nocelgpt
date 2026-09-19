"""register_length_report.py — product-grade baseline report (清单 item 7).

Folds a produced serial run's chapter drafts into the two statistics Week-1's
收口 changes were meant to move — 中文语域稳定性 (register lock) and 长度区间
达标 (role-bound length bands) — plus the hard-gate pass rate. It answers a
product question the stage/cost rollup in live_baseline_report cannot: did the
register lock actually hold, and did chapters land inside their function-bound
length band?

Read-side projection (ADR-008): reads produced draft bodies + chapter-run
artifacts, writes nothing to facts (ADR-006), never gates (ADR-003). Same body +
same run => same report.
"""
from __future__ import annotations

import re

from ..text_metrics import count_cjk_chars
from ..chapter_length import role_length, infer_chapter_role

REPORT_KIND = "register_length_baseline"
REPORT_VERSION = "1.0"

# The SAME latin-block signal the language_drift gate keys on (text_integrity
# _ASCII_WORD_RE): a run of >=4 latin letters inside the body is a register-lock
# leak (a stray English word block in Chinese prose). Measured here as a count so
# the report reads "how leaky", not just the gate's pass/fail. Headings are not
# excluded here on purpose — a report STAT should see everything; the GATE (which
# does exclude headings) remains the authority for pass/fail.
_LATIN_BLOCK_RE = re.compile(r"[A-Za-z]{4,}")


def measure_register(body: str) -> dict:
    """Per-chapter register (语域) shape. cjk_chars is the Han count; latin_blocks
    is the number of >=4-letter latin runs (the register-lock leak signal);
    latin_ratio is latin-letter chars over (cjk + latin) so a fully-Chinese body
    reads ~0.0. clean=True means no latin leak block at all."""
    text = body or ""
    cjk = count_cjk_chars(text)
    latin_blocks = _LATIN_BLOCK_RE.findall(text)
    latin_chars = sum(len(b) for b in latin_blocks)
    denom = cjk + latin_chars
    latin_ratio = round(latin_chars / denom, 4) if denom else 0.0
    return {
        "cjk_chars": cjk,
        "latin_blocks": len(latin_blocks),
        "latin_chars": latin_chars,
        "latin_ratio": latin_ratio,
        "clean": len(latin_blocks) == 0,
    }


def measure_length(body: str, *, target: int, role: str) -> dict:
    """Per-chapter length-vs-band shape. Uses the SAME role band as the live
    length_check (chapter_length.role_length) so the report and the per-chapter
    advisory cannot disagree. in_band=True means the char count sits within the
    role's [band_low, band_high]·target window."""
    total = len(body or "")
    rl = role_length(role)
    low = int(target * rl["band_low"])
    high = int(target * rl["band_high"])
    return {
        "role": role,
        "total_chars": total,
        "target_chars": target,
        "ratio": round(total / target, 3) if target else None,
        "band_low_chars": low,
        "band_high_chars": high,
        "in_band": low <= total <= high,
        "below_band": total < low,
        "above_band": total > high,
    }


def _stdev(values: list[float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    var = sum((v - mean) ** 2 for v in values) / n
    return round(var ** 0.5, 2)


def build_register_length_report(
    *,
    baseline_id: str,
    chapters: list[dict],
    target_wordcount: int,
) -> dict:
    """Fold produced chapters into the register + length + gate baseline.

    Each chapter dict is expected to carry: index, task_id, role (or a body to
    infer it from), body, and the text-integrity status. Deterministic.
    """
    per_chapter: list[dict] = []
    for ch in chapters:
        body = ch.get("body", "") or ""
        role = ch.get("role") or infer_chapter_role(body)
        reg = measure_register(body)
        length = measure_length(body, target=target_wordcount, role=role)
        per_chapter.append({
            "index": ch.get("index"),
            "task_id": ch.get("task_id"),
            "role": role,
            "integrity_status": ch.get("integrity_status"),
            "register": reg,
            "length": length,
        })

    n = len(per_chapter)
    lengths = [c["length"]["total_chars"] for c in per_chapter]
    register_clean = sum(1 for c in per_chapter if c["register"]["clean"])
    in_band = sum(1 for c in per_chapter if c["length"]["in_band"])
    integrity_pass = sum(1 for c in per_chapter
                         if c["integrity_status"] == "pass")

    register_summary = {
        # 语域稳定性: chapters with ZERO latin leak / total, plus the worst leak
        "clean_chapters": register_clean,
        "clean_rate": round(register_clean / n, 3) if n else None,
        "max_latin_ratio": max((c["register"]["latin_ratio"]
                                for c in per_chapter), default=0.0),
        "total_latin_blocks": sum(c["register"]["latin_blocks"]
                                  for c in per_chapter),
    }
    length_summary = {
        # 长度稳定性: in-band rate + the spread of chapter lengths (收敛 signal)
        "target_chars": target_wordcount,
        "in_band_chapters": in_band,
        "in_band_rate": round(in_band / n, 3) if n else None,
        "min_chars": min(lengths, default=0),
        "max_chars": max(lengths, default=0),
        "mean_chars": round(sum(lengths) / n) if n else 0,
        "stdev_chars": _stdev([float(x) for x in lengths]),
        "below_band": sum(1 for c in per_chapter if c["length"]["below_band"]),
        "above_band": sum(1 for c in per_chapter if c["length"]["above_band"]),
    }
    gate_summary = {
        "integrity_pass": integrity_pass,
        "integrity_pass_rate": round(integrity_pass / n, 3) if n else None,
        "chapter_count": n,
    }
    return {
        "kind": REPORT_KIND,
        "version": REPORT_VERSION,
        "baseline_id": baseline_id,
        "chapter_count": n,
        "register_summary": register_summary,
        "length_summary": length_summary,
        "gate_summary": gate_summary,
        "chapters": per_chapter,
        "gating": False,
    }
