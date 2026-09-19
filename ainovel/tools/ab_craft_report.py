#!/usr/bin/env python3
"""ab_craft_report.py — v11 vs v12 工艺约束双臂 A/B 报告。

被检验的假设：v12 新增的三条实测工艺约束（破折号夹注 / 比喻密度 / 对白占比）
能在**生成侧**降低对应缺陷，而不只是靠 hygiene 事后纠正。

方法纪律（针对已知的方法论陷阱）：
  - 两臂都**不开 --hygiene**：hygiene 会纠正这三项，会掩盖 prompt 自身效果。
  - temp=0.0 压低生成方差，使差异更可归因于 prompt。
  - 逐章配对比较（chapter N vs chapter N），不只比全臂均值——跨臂计数在
    非确定性生成下会混淆（memory: beat-enrichment 教训）。
  - 用与生成侧完全相同的确定性检测器测量，不引入判官分（已被证伪）。
  - 同时报告**未被 v12 约束的特征**（同头排比 / 句长CV）作为阴性对照：
    若它们也大幅移动，说明差异可能来自生成噪声而非约束本身。
"""
from __future__ import annotations

import json
import math
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "AI-Novel-Runtime"))

from runtime.reference.measure import measure_reference_chapter  # noqa: E402

# v12 直接约束的三项（缺陷方向：dash/simile 偏高为病，dialogue 偏低为病）
TARGETED = {
    "ai_taste.dash_aside_per_1000": "above",
    "density.simile_per_1000": "above",
    "density.opening_simile_per_1000": "above",
    "density.dialogue_ratio": "below",
}
# v12 未约束 —— 阴性对照。
#
# ⚠️ 已知构造性缺陷（2026-07-29 实测暴露）：这两项都已处于带内/地板，本就没有
# 移动空间（anaphora v11=v12=2.0 已在带下沿且检测器阈值同为 3；cv 已在带内无缺陷
# 压力）。因此"对照未动"**不能**证明定向组的移动来自约束——那是天花板/地板效应，
# 不是证据。真正有移动空间的未约束特征（元指代，见 META_LEAK_RE）在两臂间动了
# 12→3，证明未受约束的特征同样可以大幅波动。下一轮必须改用有移动空间的对照。
CONTROL = {
    "ai_taste.anaphora_run": "above",
    "ai_taste.sentence_length_cv": "below",
}

# 元指代泄漏：正文里出现"上一章/第5章/前文"这类叙事外指代——读者读的是小说，
# 不该看到章节编号当作剧情内的引用。抽查 A/B 正文时发现，**没有任何现有检测器
# 覆盖它**（text_integrity pass、hygiene 只报对白占比）。它既是一个新缺陷类，
# 也是本次唯一有移动空间的真阴性对照。
META_LEAK_RE = re.compile(r"上一章|下一章|前文|第[0-9一二三四五六七八九十]+章")


def load_arm(project: Path) -> list:
    """从 chapter-final（或 drafts）读出逐章正文并测量。"""
    chapters = []
    for kind in ("chapter-final", "drafts"):
        d = project / "registry" / "derived" / kind
        if not d.exists():
            continue
        for p in sorted(d.glob("*.json")):
            payload = json.loads(p.read_text(encoding="utf-8"))
            body = _find_body(payload)
            if body and len(body) > 200:
                chapters.append((p.stem, body))
        if chapters:
            break
    out = []
    for i, (name, body) in enumerate(chapters, start=1):
        feats = measure_reference_chapter(body)
        if feats:
            feats["_index"] = i
            feats["_name"] = name
            feats["_chars"] = len(body)
            # 元指代只算正文（剔除 # 标题行，否则 "# 第9章" 会被误计）
            prose = "\n".join(l for l in body.splitlines()
                              if not l.strip().startswith("#"))
            feats["_meta_leak"] = len(META_LEAK_RE.findall(prose))
            out.append(feats)
    return out


def _find_body(payload) -> str:
    """正文可能在 body / draft.body / artifact.body（envelope 兄弟字段结构）。"""
    if isinstance(payload, str):
        return payload
    if not isinstance(payload, dict):
        return ""
    for key in ("body", "text", "final_text", "content"):
        v = payload.get(key)
        if isinstance(v, str) and len(v) > 200:
            return v
    for key in ("draft", "artifact", "chapter_draft", "chapter_final"):
        v = payload.get(key)
        if isinstance(v, (dict, str)):
            got = _find_body(v)
            if got:
                return got
    return ""


def med(vals: list):
    nums = [v for v in vals if isinstance(v, (int, float))]
    return round(statistics.median(nums), 4) if nums else None


def sign_p(k: int, n: int) -> float:
    """Two-tailed exact binomial sign test, H0: p=0.5. n excludes ties.

    Reported so the A/B cannot be read as "direction looks right => it worked":
    with n=10 chapters a single feature needs ~9/10 to clear p<0.05, so any
    per-feature claim here is underpowered BY CONSTRUCTION."""
    if n <= 0:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(k, n + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def band(anchor: dict, feature: str, window="first10"):
    b = (anchor.get("windows", {}).get(window, {}) or {}).get(feature)
    return (b.get("p25"), b.get("p75")) if b else (None, None)


def main() -> int:
    a11 = load_arm(ROOT / "ab-craft-v11")
    a12 = load_arm(ROOT / "ab-craft-v12")
    if not a11 or not a12:
        print(f"missing arm data (v11={len(a11)}, v12={len(a12)})", file=sys.stderr)
        return 1
    print(f"chapters measured: v11={len(a11)}  v12={len(a12)}\n")

    anchor_p = ROOT / "docs" / "craft-anchor-measured.json"
    anchor = json.loads(anchor_p.read_text(encoding="utf-8")) if anchor_p.exists() else {}

    rows = []
    n = min(len(a11), len(a12))

    def section(title, spec):
        print(f"== {title} ==")
        print(f"  {'feature':34s} {'v11':>9} {'v12':>9} {'Δ':>9}  {'mkt band':>16}  paired better")
        for feat, defect in spec.items():
            v11 = med([c[feat] for c in a11 if feat in c])
            v12 = med([c[feat] for c in a12 if feat in c])
            if v11 is None or v12 is None:
                continue
            delta = round(v12 - v11, 4)
            # 逐章配对：v12 在该章是否比 v11 更靠"非缺陷"方向
            wins = ties = 0
            for i in range(n):
                x, y = a11[i].get(feat), a12[i].get(feat)
                if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
                    continue
                if x == y:
                    ties += 1
                elif (y < x) if defect == "above" else (y > x):
                    wins += 1
            lo, hi = band(anchor, feat)
            bd = f"[{lo},{hi}]" if lo is not None else "-"
            improved = (delta < 0) if defect == "above" else (delta > 0)
            mark = "OK" if improved else "!!"
            compared = n - ties
            p = sign_p(wins, compared)
            # did the arm actually reach the market band, or just move toward it?
            in_band = (lo is not None and lo <= v12 <= hi)
            print(f"  {mark} {feat:31s} {v11:>9} {v12:>9} {delta:>9}  {bd:>16}  "
                  f"{wins}/{compared} p={p:.3f} {'IN-BAND' if in_band else 'out'}")
            rows.append({"feature": feat, "defect_side": defect, "group": title,
                         "v11_median": v11, "v12_median": v12, "delta": delta,
                         "market_band": [lo, hi], "paired_v12_better": wins,
                         "paired_compared": compared, "ties": ties,
                         "sign_test_p": round(p, 4), "significant": p < 0.05,
                         "v12_in_market_band": in_band,
                         "improved": improved})
        print()

    section("TARGETED by v12", TARGETED)
    section("CONTROL (not constrained by v12)", CONTROL)

    # --- 元指代：抽查正文时发现的新缺陷类，同时是唯一有移动空间的真阴性对照
    leak11 = [c["_meta_leak"] for c in a11]
    leak12 = [c["_meta_leak"] for c in a12]
    lw = lt = 0
    for x, y in zip(leak11, leak12):
        if x == y:
            lt += 1
        elif y < x:
            lw += 1
    leak_n = min(len(leak11), len(leak12)) - lt
    leak_p = sign_p(lw, leak_n)
    print("== META-LEAK 元指代泄漏（无检测器覆盖；唯一有移动空间的对照）==")
    print(f"  v11 per-chapter: {leak11}  total={sum(leak11)}")
    print(f"  v12 per-chapter: {leak12}  total={sum(leak12)}")
    print(f"  paired v12 better {lw}/{leak_n} (ties {lt})  p={leak_p:.3f}")
    print("  !! 这是 v12 未约束的特征，却从 %d 降到 %d —— 说明未受约束的特征同样能"
          % (sum(leak11), sum(leak12)))
    print("     大幅波动，因此本轮『对照未动』不足以把定向组的改善归因于约束。\n")

    # --- side effect: length. v12 does NOT constrain length, so any move here is
    # an uninvited side effect and must be reported beside the wins.
    len11 = med([c["_chars"] for c in a11])
    len12 = med([c["_chars"] for c in a12])
    lo_l, hi_l = band(anchor, "_chars")
    print("== SIDE EFFECT: length (not constrained by v12) ==")
    print(f"  v11 median chars: {len11}"
          + (f"  ({len11 / hi_l:.2f}x market p75)" if hi_l else ""))
    print(f"  v12 median chars: {len12}"
          + (f"  ({len12 / hi_l:.2f}x market p75)" if hi_l else ""))
    length_worse = len12 > len11
    if length_worse:
        print(f"  !! v12 is {len12 - len11:.0f} chars LONGER — overshoot worsened")

    # --- verdict. Stated so the run cannot be read as a success it isn't.
    targeted = [r for r in rows if r["group"] == "TARGETED by v12"]
    control = [r for r in rows if r["group"].startswith("CONTROL")]
    all_moved = all(r["improved"] for r in targeted)
    any_sig = any(r["significant"] for r in targeted)
    control_still = not any(r["improved"] for r in control)
    reached = [r["feature"] for r in targeted if r["v12_in_market_band"]]
    pattern_p = 0.5 ** len(targeted) if all_moved else None

    # 对照是否**有效**：只有当对照特征本身有移动空间（不在带内地板）时，
    # "对照未动" 才构成证据。本轮两项都在带内/地板 → 对照无效。
    control_valid = any(not r["v12_in_market_band"] for r in control)
    leak_moved = sum(leak12) != sum(leak11)

    print("\n== VERDICT ==")
    print(f"  targeted all moved correctly : {all_moved} ({len(targeted)}/{len(targeted)})")
    print(f"  any single feature p<0.05    : {any_sig}")
    if pattern_p:
        print(f"  pattern-level P(all correct by chance) = {pattern_p:.4f}")
    print(f"  reached market band          : {len(reached)}/{len(targeted)} {reached}")
    print(f"  negative control VALID?      : {control_valid}"
          f"{'  (floor/ceiling — carries no information)' if not control_valid else ''}")
    print(f"  unconstrained feature moved  : {leak_moved} (meta-leak "
          f"{sum(leak11)}→{sum(leak12)})")

    verdict = ("DIRECTIONAL ONLY — all 4 targeted features moved the right way, but "
               "no single feature reaches p<0.05 at n=10, 3/4 remain OUT of the market "
               "band, the negative control is invalid (floor/ceiling), and an "
               "UNCONSTRAINED feature (meta-leak) moved just as much. Cannot attribute "
               "the improvement to the v12 constraints.")
    if any_sig and all_moved and control_valid and not leak_moved:
        verdict = "CONFIRMED — significant, with a valid unmoved control"
    print(f"  => {verdict}")

    out = ROOT / "docs" / "craft-ab-v11-v12-report.json"
    out.write_text(json.dumps({
        "kind": "craft-ab-v11-vs-v12",
        "hypothesis": "v12 的三条实测工艺约束在生成侧降低对应缺陷",
        "method": {
            "hygiene": "OFF in both arms (would mask the prompt effect)",
            "temperature": 0.0,
            "provider": "deepseek",
            "paired": "per-chapter N vs N",
            "instruments": "same deterministic detectors as generation side",
            "negative_control": list(CONTROL),
        },
        "chapters": {"v11": len(a11), "v12": len(a12)},
        "rows": rows,
        "length_side_effect": {
            "v11_median_chars": len11, "v12_median_chars": len12,
            "market_p75": hi_l, "worsened": length_worse,
            "note": "v12 does not constrain length; overshoot is an unaddressed P0-3",
        },
        "meta_leak": {
            "v11_per_chapter": leak11, "v12_per_chapter": leak12,
            "v11_total": sum(leak11), "v12_total": sum(leak12),
            "paired_v12_better": lw, "paired_compared": leak_n,
            "sign_test_p": round(leak_p, 4),
            "detector_coverage": "NONE — text_integrity passes, hygiene only flags "
                                 "dialogue ratio; this is a NEW uncovered defect class",
            "role": "the only unconstrained feature WITH room to move; it moved as "
                    "much as the targeted ones, which is why attribution fails",
        },
        "verdict": {
            "targeted_all_moved_correctly": all_moved,
            "control_unmoved": control_still,
            "control_valid": control_valid,
            "control_invalid_reason": (None if control_valid else
                                       "both control features sit in-band/at floor, "
                                       "so they had no room to move — 'unmoved' "
                                       "carries no information"),
            "any_single_feature_significant": any_sig,
            "pattern_level_p": pattern_p,
            "reached_market_band": reached,
            "unconstrained_feature_moved": leak_moved,
            "conclusion": verdict,
            "caveat": "n=10 per arm: a single feature needs ~9/10 paired wins for "
                      "p<0.05, so per-feature claims are underpowered by design. "
                      "Do NOT report this as 'the craft gap is fixed'.",
        },
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nwrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
