#!/usr/bin/env python3
"""measure_craft_anchor.py — 从真实爆款正文中测出起点工艺数字锚。

背景：ANOVEL 规划文档 25 次提到"首订"却给出 0 个数字阈值（审核评级 F）。
本工具拒绝"编数字"，改为用**与生成侧完全相同的确定性仪器**（density /
ai_taste / hook / length）去测量真实市场验证过的爆款正文，把工艺目标
从"修辞"变成"可复算的区间"。

纪律：
  - 只读参考语料，不写 registry/facts（ADR-006）。
  - 纯确定性：同输入同输出，不调任何模型。
  - 产出是 advisory 工艺锚，never gates（ADR-003）。
  - 分章段测量（黄金三章 / 前10章 / 前30章），因为起点工艺是**位置函数**，
    不是全书常量——这正是旧文档"通用三幕"最大的缺陷。
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "AI-Novel-Runtime"))

from runtime.reference.segment import segment_reference_novel  # noqa: E402
from runtime.reference.measure import measure_reference_chapter  # noqa: E402

# 起点工艺的分段窗口：这三个窗口对应真实商业决策点。
WINDOWS = (("golden3", 1, 3), ("first10", 1, 10), ("first30", 1, 30))


def _read(path: Path) -> str:
    """参考小说可能是 GBK（历史 bug：GBK 曾导致 source loading 崩溃）。"""
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            return path.read_text(encoding=enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return path.read_text(encoding="utf-8", errors="ignore")


def _stats(values: list) -> dict:
    nums = [v for v in values if isinstance(v, (int, float))]
    if not nums:
        return {}
    out = {
        "n": len(nums),
        "mean": round(statistics.mean(nums), 3),
        "median": round(statistics.median(nums), 3),
        "min": round(min(nums), 3),
        "max": round(max(nums), 3),
    }
    if len(nums) > 1:
        out["stdev"] = round(statistics.stdev(nums), 3)
        qs = statistics.quantiles(nums, n=4)
        out["p25"], out["p75"] = round(qs[0], 3), round(qs[2], 3)
    return out


def measure_novel(path: Path, max_ch: int = 30) -> dict:
    chapters = segment_reference_novel(path.stem, _read(path))[:max_ch]
    per_ch = []
    for ch in chapters:
        feats = measure_reference_chapter(ch.body)
        if feats:
            feats["_index"] = ch.index
            feats["_chars"] = len(ch.body)
            per_ch.append(feats)
    return {"source": path.stem, "chapters_measured": len(per_ch), "per_chapter": per_ch}


def fold_windows(novels: list) -> dict:
    """把逐章特征折叠成分窗口区间——这就是工艺锚。"""
    keys = set()
    for nv in novels:
        for ch in nv["per_chapter"]:
            keys.update(k for k in ch if not k.startswith("_"))
    keys.add("_chars")

    anchor = {}
    for name, lo, hi in WINDOWS:
        window = {}
        for key in sorted(keys):
            vals = [ch[key] for nv in novels for ch in nv["per_chapter"]
                    if lo <= ch["_index"] <= hi and key in ch]
            st = _stats(vals)
            if st:
                window[key] = st
        anchor[name] = window
    return anchor


def main() -> int:
    src = ROOT / "novel-lingse" / "sources" / "reference-novels"
    files = sorted(src.glob("*.txt"))
    if not files:
        print(f"no reference novels under {src}", file=sys.stderr)
        return 1

    novels = [measure_novel(f) for f in files]
    for nv in novels:
        print(f"  {nv['source'][:28]:30s} chapters={nv['chapters_measured']}")

    report = {
        "kind": "qidian-craft-anchor",
        "discipline": "deterministic; comparison-only; never gates (ADR-003)",
        "sources": [{"id": nv["source"], "chapters": nv["chapters_measured"]} for nv in novels],
        "windows": fold_windows(novels),
    }
    out = ROOT / "docs" / "craft-anchor-measured.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nwrote {out.relative_to(ROOT)}")

    for name, _, _ in WINDOWS:
        w = report["windows"][name]
        print(f"\n== {name} ==")
        for k in ("_chars", "density.dialogue_ratio", "ai_taste.anaphora_run",
                  "ai_taste.sentence_length_cv", "density.simile_per_1000",
                  "hook.has_question", "hook.has_suspension", "hook.has_turn"):
            if k in w:
                s = w[k]
                print(f"  {k:34s} median={s['median']:>9} p25={s.get('p25','-'):>9} p75={s.get('p75','-'):>9}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
