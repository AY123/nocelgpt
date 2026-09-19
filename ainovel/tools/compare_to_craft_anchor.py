#!/usr/bin/env python3
"""compare_to_craft_anchor.py — 把我们的书按同一把尺子对到工艺锚上。

配合 measure_craft_anchor.py 使用：锚是真实爆款测出的区间，本工具测我们自己
的 30 章基线，逐特征给出"在带内 / 偏高 / 偏低"以及偏离方向。

这是审核报告"不知道写得好不好"（GAP-C）的**确定性**旁路：不依赖已被证伪的
LLM 判官绝对分，只靠同仪器同口径的市场区间对比。
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "AI-Novel-Runtime"))

from runtime.reference.measure import measure_reference_chapter  # noqa: E402

FOCUS = (
    "_chars",
    "density.dialogue_ratio",
    "density.simile_per_1000",
    "ai_taste.anaphora_run",
    "ai_taste.sentence_length_cv",
    "ai_taste.dash_aside_per_1000",
    "hook.has_question",
    "hook.has_turn",
)


def load_ours(book_dir: Path, limit: int = 30) -> list:
    """读我们自己的章节正文（manuscript/*.txt，排除 _全本）。"""
    files = sorted(p for p in book_dir.glob("第*.txt"))[:limit]
    out = []
    for i, p in enumerate(files, start=1):
        body = p.read_text(encoding="utf-8", errors="ignore").strip()
        feats = measure_reference_chapter(body)
        if feats:
            feats["_index"] = i
            feats["_chars"] = len(body)
            out.append(feats)
    return out


def _stats(vals: list) -> dict:
    nums = [v for v in vals if isinstance(v, (int, float))]
    if not nums:
        return {}
    out = {"n": len(nums), "median": round(statistics.median(nums), 3)}
    if len(nums) > 1:
        qs = statistics.quantiles(nums, n=4)
        out["p25"], out["p75"] = round(qs[0], 3), round(qs[2], 3)
    return out


def verdict(ours: dict, anchor: dict) -> tuple:
    """在带内(p25..p75)=in_band；否则给出方向与倍数。"""
    om, lo, hi = ours.get("median"), anchor.get("p25"), anchor.get("p75")
    if om is None or lo is None or hi is None:
        return "unknown", ""
    if lo <= om <= hi:
        return "in_band", ""
    if om > hi:
        ratio = f"{om / hi:.2f}×p75" if hi else "above"
        return "above_band", ratio
    ratio = f"{om / lo:.2f}×p25" if lo else "below"
    return "below_band", ratio


def main() -> int:
    anchor_path = ROOT / "docs" / "craft-anchor-measured.json"
    if not anchor_path.exists():
        print("run tools/measure_craft_anchor.py first", file=sys.stderr)
        return 1
    anchor = json.loads(anchor_path.read_text(encoding="utf-8"))

    book = ROOT / "novel-lingse" / "manuscript" / "30ch-baseline"
    ours = load_ours(book)
    if not ours:
        print(f"no chapters under {book}", file=sys.stderr)
        return 1
    print(f"our chapters measured: {len(ours)}\n")

    rows = []
    for name, lo, hi in (("golden3", 1, 3), ("first10", 1, 10), ("first30", 1, 30)):
        aw = anchor["windows"].get(name, {})
        print(f"== {name} (ours vs 4 real bestsellers) ==")
        print(f"  {'feature':32s} {'ours':>9} {'mkt_p25':>9} {'mkt_p75':>9}  verdict")
        for key in FOCUS:
            ov = _stats([c[key] for c in ours if lo <= c["_index"] <= hi and key in c])
            av = aw.get(key, {})
            if not ov or not av:
                continue
            v, note = verdict(ov, av)
            flag = "OK " if v == "in_band" else "!! "
            print(f"  {flag}{key:30s} {ov['median']:>9} {av.get('p25','-'):>9} "
                  f"{av.get('p75','-'):>9}  {v} {note}")
            rows.append({"window": name, "feature": key, "ours_median": ov["median"],
                         "market_p25": av.get("p25"), "market_p75": av.get("p75"),
                         "verdict": v, "note": note})
        print()

    out = ROOT / "docs" / "craft-gap-report.json"
    out.write_text(json.dumps(
        {"kind": "craft-gap-vs-market-anchor",
         "discipline": "deterministic; comparison-only; never gates",
         "our_book": "novel-lingse 30ch-baseline (RUN-00001)",
         "anchor_sources": anchor["sources"], "rows": rows},
        ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
