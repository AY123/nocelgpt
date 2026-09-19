#!/usr/bin/env python3
"""ab3_cross_model_report.py — 三臂跨模型工艺实验报告。

臂：
  A = ab3-ds-v12   DeepSeek + v12
  B = ab3-gpt-v11  GPT-5.4  + v11   （GPT 上的对照臂）
  C = ab3-gpt-v12  GPT-5.4  + v12

两个正交问题：
  Q1 工艺约束是否跨模型通用？  B vs C（同模型、只差 prompt 版本）
  Q2 哪个模型更贴市场带？      A vs C（同 prompt、只差模型）= MM-01 探针

相对上轮双臂实验修掉的两个设计缺陷：
  1. **阴性对照无效**（天花板/地板效应）。上轮选的 anaphora_run（已在带下沿 2.0）
     和 sentence_length_cv（已在带内）本就没有移动空间，"对照未动"不携带信息。
     本轮对照改用**有移动空间**的未约束特征：hook.* 布尔标志 + 元指代。
     判据：一个有效对照必须自身可移动（带外或跨臂有方差）。
  2. **功效不足**。上轮 n=10，单特征需 ~9/10 配对胜局才显著。n=30 时约 20/30 即可。

纪律：
  - 三臂都不开 --hygiene（否则事后纠正会掩盖 prompt 的预防效果）。
  - temp=0.0；同一 registry / 同一 outline / 同一 30 章序列 → 逐章配对可比。
  - 只用确定性检测器，不用已被证伪的判官绝对分。
  - 篇幅新 directive 在三臂**都**生效，故篇幅是受控变量；同时报告它是否被遵守。
"""
from __future__ import annotations

import json
import math
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "AI-Novel-Runtime"))

from runtime.reference.measure import measure_reference_chapter  # noqa: E402
from runtime.execution.meta_reference import meta_reference_summary  # noqa: E402

ARMS = {"A_ds_v12": "ab3-ds-v12", "B_gpt_v11": "ab3-gpt-v11", "C_gpt_v12": "ab3-gpt-v12"}

# v12 直接约束的特征 → 缺陷侧
TARGETED = {
    "ai_taste.dash_aside_per_1000": "above",
    "density.simile_per_1000": "above",
    "density.opening_simile_per_1000": "above",
    "density.dialogue_ratio": "below",
}
# v12 未约束、且**有移动空间**的特征 —— 有效阴性对照
CONTROL = {
    "hook.has_question": None,
    "hook.has_turn": None,
    "hook.has_closure": None,
    "_meta_leak": "above",
}

# 每个特征该用哪个统计量。
#
# ⚠️ 实测抓到的真实 bug：中位数对**稀疏计数型**特征是错的统计量。元指代逐章
# [0,1,0,0,1,1,0] 的中位数是 0，把 3/7 的命中章全藏进零里——抽查 GPT 正文时
# 明明读到「上一章夜禁前药棚外那场乱」，报告却显示 _meta_leak 中位 0。
# 破折号夹注同样稀疏（多数章 0.0），两臂中位都是 0.0 → Δ=0 → 看起来"无信息"，
# 实际是统计量掩盖了差异。
#
#   continuous — 中位数有意义（密度类连续量）
#   sparse     — 多数章为 0 的计数：报「命中章率 + 总计」，中位数无意义
#   bool       — 0/1 标志：报命中率
FEATURE_KIND = {
    "ai_taste.dash_aside_per_1000": "sparse",
    "density.simile_per_1000": "continuous",
    "density.opening_simile_per_1000": "continuous",
    "density.dialogue_ratio": "continuous",
    "hook.has_question": "bool",
    "hook.has_turn": "bool",
    "hook.has_closure": "bool",
    "_meta_leak": "sparse",
}


def stat(vals: list, kind: str):
    """按特征类型选统计量，返回 (数值, 展示串)。数值用于 Δ，展示串给人读。"""
    nums = [v for v in vals if isinstance(v, (int, float))]
    if not nums:
        return None, "-"
    n = len(nums)
    if kind == "sparse":
        hits = sum(1 for v in nums if v > 0)
        return round(hits / n, 3), f"{hits}/{n} 章 tot={round(sum(nums), 2)}"
    if kind == "bool":
        rate = sum(1 for v in nums if v > 0) / n
        return round(rate, 3), f"{sum(1 for v in nums if v > 0)}/{n} 章"
    return round(statistics.median(nums), 4), str(round(statistics.median(nums), 4))
# 受控变量（三臂同款新 directive），单独报告是否被遵守
LENGTH_TARGET, LENGTH_CEILING, MARKET_P75 = 3333, 4166, 3287


def _find_body(payload) -> str:
    if isinstance(payload, str):
        return payload if len(payload) > 200 else ""
    if not isinstance(payload, dict):
        return ""
    for key in ("body", "text", "final_text", "content"):
        v = payload.get(key)
        if isinstance(v, str) and len(v) > 200:
            return v
    for key in ("draft", "artifact", "chapter_draft", "chapter_final"):
        got = _find_body(payload.get(key) or {})
        if got:
            return got
    return ""


def load_arm(project: Path) -> list:
    out = []
    d = project / "registry" / "derived" / "drafts"
    if not d.exists():
        return out
    for i, p in enumerate(sorted(d.glob("*.json")), start=1):
        body = _find_body(json.loads(p.read_text(encoding="utf-8")))
        if not body:
            continue
        feats = measure_reference_chapter(body)
        if not feats:
            continue
        prose = "\n".join(l for l in body.splitlines() if not l.strip().startswith("#"))
        s = meta_reference_summary(prose)
        feats["_meta_leak"] = (s or {}).get("meta_reference_count", 0)
        feats["_index"], feats["_chars"] = i, len(body)
        out.append(feats)
    return out


def med(vals):
    nums = [v for v in vals if isinstance(v, (int, float))]
    return round(statistics.median(nums), 4) if nums else None


def sign_p(k: int, n: int) -> float:
    """Two-tailed exact binomial sign test (n excludes ties)."""
    if n <= 0:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(k, n + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def paired(a: list, b: list, feature: str, defect):
    """b 相对 a 在该特征上更靠非缺陷方向的章数。defect=None => 只统计变化。"""
    n = min(len(a), len(b))
    wins = losses = ties = 0
    for i in range(n):
        x, y = a[i].get(feature), b[i].get(feature)
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            continue
        if x == y:
            ties += 1
        elif defect is None:
            losses += 1                      # 仅表示"有变化"
        elif (y < x) if defect == "above" else (y > x):
            wins += 1
        else:
            losses += 1
    return wins, losses, ties, n


def compare(label: str, a: list, b: list, arms: str, rows: list):
    # 中位数必须与配对比较落在**同一样本集**上。曾经的 bug：med 用全臂、paired 只用
    # 前 min(n) 章，臂长不齐时给出自相矛盾的读数（Δ=0.5 却 changed 0/2）。三臂都跑满
    # 30 章时该 bug 会被掩盖，但只要有一臂 skip 就会静默误导，故在此对齐。
    n = min(len(a), len(b))
    a, b = a[:n], b[:n]
    print(f"\n{'=' * 78}\n{label}  ({arms})  n={n} 配对章\n{'=' * 78}")
    for group, spec in (("TARGETED by v12", TARGETED), ("CONTROL (v12 未约束)", CONTROL)):
        print(f"\n-- {group} --")
        print(f"  {'feature':30s} {'kind':10s} {'armA':>14} {'armB':>14} "
              f"{'Δ':>8}  paired      p")
        for feat, defect in spec.items():
            kind = FEATURE_KIND.get(feat, "continuous")
            va, sa = stat([c.get(feat) for c in a], kind)
            vb, sb = stat([c.get(feat) for c in b], kind)
            if va is None or vb is None:
                continue
            # `pn` (paired n) must NOT shadow the outer sample size `n`.
            w, l, t, pn = paired(a, b, feat, defect)
            comp = w + l
            p = sign_p(w, comp) if defect else 1.0
            delta = round(vb - va, 4)
            if defect:
                improved = (delta < 0) if defect == "above" else (delta > 0)
                # A feature sitting on the FLOOR in both arms carries no
                # information — flag it rather than reading Δ=0 as "no effect".
                floor = (va == 0 and vb == 0)
                mark = "--" if floor else ("OK" if improved else "!!")
                pr = ("floor — 无信息" if floor else f"{w}/{comp}  p={p:.3f}")
            else:
                improved, floor, mark = None, False, "  "
                pr = f"changed {comp}/{pn}"
            print(f"  {mark}{feat:29s} {kind:10s} {sa:>14} {sb:>14} "
                  f"{delta:>8}  {pr}")
            rows.append({"comparison": label, "group": group, "feature": feat,
                         "stat_kind": kind, "arm_a": va, "arm_a_display": sa,
                         "arm_b": vb, "arm_b_display": sb,
                         "defect_side": defect, "delta": delta,
                         "paired_b_better": w, "paired_compared": comp,
                         "ties": t, "sign_test_p": round(p, 4),
                         "on_floor_both_arms": floor,
                         "significant": bool(defect) and p < 0.05 and not floor,
                         "improved": improved})


def length_section(data: dict) -> dict:
    print(f"\n{'=' * 78}\n篇幅：新 directive 是否被遵守（三臂同款，受控变量）\n{'=' * 78}")
    print(f"  目标 {LENGTH_TARGET} / 上限 {LENGTH_CEILING} / 市场 p75 {MARKET_P75}")
    out = {}
    for name, arm in data.items():
        if not arm:
            continue
        lens = [c["_chars"] for c in arm]
        m = med(lens)
        over = sum(1 for x in lens if x > LENGTH_CEILING)
        out[name] = {"median": m, "n": len(lens), "over_ceiling": over,
                     "vs_ceiling": round(m / LENGTH_CEILING, 3),
                     "vs_market_p75": round(m / MARKET_P75, 3)}
        print(f"  {name:12s} 中位 {m:>7}  ={m / MARKET_P75:.2f}x市场p75  "
              f"超上限 {over}/{len(lens)} 章")
    print("  参照：v11/v12 双臂旧读数 5101 / 5427（1.55x / 1.65x），无上限 directive")
    return out


def main() -> int:
    data = {k: load_arm(ROOT / v) for k, v in ARMS.items()}
    print("chapters measured:", {k: len(v) for k, v in data.items()})
    if not all(data.values()):
        print("\n!! 有臂尚无数据，报告不完整", file=sys.stderr)

    rows: list = []
    A, B, C = data["A_ds_v12"], data["B_gpt_v11"], data["C_gpt_v12"]
    if B and C:
        compare("Q1 工艺约束跨模型是否通用", B, C, "armA=GPT-v11  armB=GPT-v12", rows)
    if A and C:
        compare("Q2 哪个模型更贴市场带 (MM-01)", A, C, "armA=DeepSeek-v12  armB=GPT-v12", rows)

    length = length_section(data)

    # 对照有效性：一个对照只有自身能移动时才携带信息
    ctl = [r for r in rows if r["group"].startswith("CONTROL")]
    ctl_moved = [r["feature"] for r in ctl if r["delta"] != 0]
    print(f"\n{'=' * 78}\n结论\n{'=' * 78}")
    print(f"  阴性对照可移动的项 : {ctl_moved or '无 —— 对照仍无效'}")
    for label in {r["comparison"] for r in rows}:
        tg = [r for r in rows if r["comparison"] == label and r["group"] == "TARGETED by v12"]
        if not tg:
            continue
        allm = all(r["improved"] for r in tg)
        sig = [r["feature"] for r in tg if r["significant"]]
        print(f"\n  {label}")
        print(f"    定向 4 项方向全对 : {allm}")
        print(f"    达 p<0.05 的项    : {sig or '无'}")

    out = ROOT / "docs" / "craft-ab3-cross-model-report.json"
    out.write_text(json.dumps({
        "kind": "craft-ab3-cross-model",
        "arms": {"A": "deepseek + v12", "B": "gpt-5.4 + v11", "C": "gpt-5.4 + v12"},
        "questions": {"Q1": "B vs C — 工艺约束跨模型是否通用",
                      "Q2": "A vs C — 哪个模型更贴市场带 (MM-01)"},
        "method": {"hygiene": "OFF in all arms", "temperature": 0.0,
                   "paired": "per-chapter, same registry/outline",
                   "control_fix": "改用有移动空间的未约束特征（hook.* + 元指代），"
                                  "上轮对照在地板/带内故无效",
                   "length": "新 directive 三臂同款 → 受控变量"},
        "chapters": {k: len(v) for k, v in data.items()},
        "rows": rows, "length": length,
        "control_features_that_moved": ctl_moved,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nwrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
