#!/usr/bin/env python3
"""ab_craft_v13.py — v13 工艺 A/B 报告（篇幅 + 元指代 + 旧工艺对照）。

This script is the v13 successor to `tools/ab_craft_report.py`.
It keeps the same deterministic measurement discipline, but it is configured for
v13's actual experiment framing:
  - v13 is the generation-side meta-reference prevention prompt.
  - H1 remains the length side effect / upstream length correction check.
  - H2 is the chapter-level meta-reference leak rate, which must be tested with
    a binary per-chapter outcome and exact McNemar.
  - dash / simile / dialogue remain the natural controls because they are not
    newly constrained by v13.

The tool is intentionally read-only and reproducible. It measures existing
chapter exports, compares paired chapters, and writes a JSON report.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "AI-Novel-Runtime"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from runtime.reference.measure import measure_reference_chapter  # noqa: E402

from ab_stats import exact_mcnemar, sign_test, wilcoxon  # noqa: E402
from meta_leak import count_meta_leaks  # noqa: E402

DEFAULT_ARM_A = ROOT / "novel-lingse" / "manuscript" / "AB-craft-v12"
DEFAULT_ARM_B = ROOT / "novel-lingse" / "manuscript" / "AB-craft-v13"
DEFAULT_ANCHOR = ROOT / "docs" / "craft-anchor-measured.json"
DEFAULT_OUT = ROOT / "docs" / "craft-ab-v12-v13-report.json"

# v13 相对 v12 的 diff 只有 8 行:一段"不得把章号/大纲/提示词等生产元信息
# 写进故事世界"的防泄漏指令(AI-Novel-Standard/contracts/prompts/
# chapter-draft.v13.prompt.yaml)。v13 ⊃ v12,所以 v12 的工艺约束
# (破折号夹注 / 比喻密度 / 对白承载)在两臂**同等施加**。
#
# 这决定了定向/对照的划分,而原来的划分是反的:
#   TARGETED 曾是 dash/simile/dialogue —— 但那是 v12 的约束,不是 v13 新增的。
#   把它们当作 v13 的定向指标,等于给 v13 记 v12 的功劳。
#
# 正确划分:v13 唯一新增的是元指代防泄漏 → 那才是唯一定向假设(H2)。
# dash/simile/dialogue 未被 v13 新增触及 → 天然对照:若它们也发生大幅
# 系统性移动,说明两臂差异不能归因于防泄漏约束(模型采样漂移的信号)。
TARGETED: dict[str, str] = {}          # H2 单独处理(章级二元 + 精确 McNemar)

CONTROL = {
    "ai_taste.dash_aside_per_1000": "above",
    "density.simile_per_1000": "above",
    "density.opening_simile_per_1000": "above",
    "density.dialogue_ratio": "below",
    "ai_taste.anaphora_run": "above",
    "ai_taste.sentence_length_cv": "below",
}

MIN_CARDINALITY = 6
ALPHA = 0.05


def _find_body(payload: Any) -> str:
    if isinstance(payload, str):
        return payload
    if not isinstance(payload, dict):
        return ""
    for key in ("body", "text", "final_text", "content"):
        value = payload.get(key)
        if isinstance(value, str) and len(value) > 200:
            return value
    for key in ("draft", "artifact", "chapter_draft", "chapter_final"):
        value = payload.get(key)
        if isinstance(value, (dict, str)):
            found = _find_body(value)
            if found:
                return found
    return ""


def load_arm(project: Path) -> list[dict[str, Any]]:
    chapters: list[tuple[str, str]] = []
    for kind in ("chapter-final", "drafts"):
        directory = project / "registry" / "derived" / kind
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            body = _find_body(payload)
            if body and len(body) > 200:
                chapters.append((path.stem, body))
        if chapters:
            break

    out: list[dict[str, Any]] = []
    for idx, (name, body) in enumerate(chapters, start=1):
        feats = measure_reference_chapter(body)
        if not isinstance(feats, dict):
            continue
        # _index 必须是**真实章号**(从 TASK-000NN 解析),不能是位置序。
        #
        # 原来这里用 enumerate 的位置序,一旦某臂少一章就会静默错位:本轮
        # guhai-v13 的 ch21 撞硬红线被拦(ADR-003 唯一合法的确定性 gate),
        # v13 臂只有 32 章,于是位置 21 起 v12-ch21 被拿去和 v13-ch22 比 ——
        # 12/33 对在拿不同章互比,配对设计被毁而报告看不出任何异常。
        m = re.search(r"(\d+)", name)
        feats["_index"] = int(m.group(1)) if m else idx
        feats["_name"] = name
        feats["_chars"] = len(body)
        # 元指代测量改走 tools/meta_leak.py。原来这里是一条把 `第N章` 一律
        # 算作泄漏的正则,而 `第N章` 同时命中章节标题(# / **粗体**)与章末
        # 完结标记(（第一章 完）)。实测 ab3-gpt-v12 因此从 9/30 虚报到
        # 24/30(80%),是设计文档 35% 基线的来源。剥离格式产物后才是真泄漏。
        leaks = count_meta_leaks(body)
        feats["_meta_leak"] = leaks["_total"]
        feats["_meta_leak_by_pattern"] = {k: v for k, v in leaks.items()
                                          if not k.startswith("_")}
        # H2 的检验单元:章级二元(计数零膨胀,不能用签名秩)
        feats["_meta_leak_any"] = leaks["_total"] > 0
        out.append(feats)
    return out


def med(vals: list[Any]):
    nums = [v for v in vals if isinstance(v, (int, float))]
    return round(statistics.median(nums), 4) if nums else None


def band(anchor: dict[str, Any], feature: str, window: str = "first10"):
    entry = (anchor.get("windows", {}).get(window, {}) or {}).get(feature)
    if not entry:
        return (None, None)
    return (entry.get("p25"), entry.get("p75"))


# 本地的 sign_p / mc_nemar_p 已删除,统一改用 tools/ab_stats.py:
#   - exact_mcnemar 与本地 mc_nemar_p 同式,但那份**定义了却从未被调用** ——
#     H2 实际跑的是 sign_p(计数符号检验),不是设计要求的章级二元 + 精确
#     McNemar。函数存在不等于在用,这是本仓库反复出现的 built≠live。
#   - wilcoxon 是新增能力:原工具只有符号检验,H1(篇幅)白扔功效。
#   ab_stats 的两个检验都对过教科书值(McNemar 6/6、Wilcoxon 精确路径
#   n=10 全正差值 p=0.001953)。


def main() -> int:
    ap = argparse.ArgumentParser(description="v13 A/B craft report")
    ap.add_argument("--arm-a", type=Path, default=DEFAULT_ARM_A, help="baseline arm directory")
    ap.add_argument("--arm-b", type=Path, default=DEFAULT_ARM_B, help="v13 arm directory")
    ap.add_argument("--anchor", type=Path, default=DEFAULT_ANCHOR, help="market anchor JSON")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT, help="report output path")
    args = ap.parse_args()

    if not args.arm_a.exists() or not args.arm_b.exists():
        print(f"missing arm data: {args.arm_a} / {args.arm_b}", file=sys.stderr)
        return 1

    raw_a = load_arm(args.arm_a)
    raw_b = load_arm(args.arm_b)
    if not raw_a or not raw_b:
        print(f"missing measurable chapters (v12={len(raw_a)}, v13={len(raw_b)})", file=sys.stderr)
        return 1

    # 按**真实章号内连接**,而不是按位置对齐两个列表。
    # 只有两臂都产出的章号才进入配对;任一臂缺失(如撞硬红线被拦)的章号
    # 整对丢弃并显式报告 —— 配对检验的前提是同一章的两个版本互比。
    by_a = {c["_index"]: c for c in raw_a}
    by_b = {c["_index"]: c for c in raw_b}
    common = sorted(set(by_a) & set(by_b))
    dropped_a = sorted(set(by_a) - set(by_b))     # v12 有、v13 无
    dropped_b = sorted(set(by_b) - set(by_a))     # v13 有、v12 无
    arm_a = [by_a[i] for i in common]
    arm_b = [by_b[i] for i in common]

    anchor = json.loads(args.anchor.read_text(encoding="utf-8")) if args.anchor.exists() else {}
    rows: list[dict[str, Any]] = []
    n = len(common)

    print(f"chapters measured: v12={len(raw_a)}  v13={len(raw_b)}")
    print(f"paired on real chapter number: {n}")
    if dropped_a or dropped_b:
        print(f"  dropped unpaired -> only-v12={dropped_a}  only-v13={dropped_b}")
    print()

    def section(title: str, spec: dict[str, str]):
        print(f"== {title} ==")
        print(f"  {'feature':34s} {'v12':>9} {'v13':>9} {'Δ':>9}  {'mkt band':>16}  paired better")
        for feat, defect in spec.items():
            v_a = med([c.get(feat) for c in arm_a if feat in c])
            v_b = med([c.get(feat) for c in arm_b if feat in c])
            if v_a is None or v_b is None:
                continue
            delta = round(v_b - v_a, 4)
            wins = ties = 0
            pa: list[float] = []
            pb: list[float] = []
            for i in range(n):
                x, y = arm_a[i].get(feat), arm_b[i].get(feat)
                if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
                    continue
                pa.append(float(x))
                pb.append(float(y))
                if x == y:
                    ties += 1
                elif (y < x) if defect == "above" else (y > x):
                    wins += 1
            lo, hi = band(anchor, feat)
            bd = f"[{lo},{hi}]" if lo is not None else "-"
            improved = (delta < 0) if defect == "above" else (delta > 0)
            compared = n - ties
            # 这些特征是连续量 → 用签名秩,它利用差值大小,功效高于只看方向的
            # 符号检验。符号检验仍算出来并列报,便于与旧报告对照。
            wil = wilcoxon(pa, pb)
            p = wil["p_value"]
            p_sign = sign_test(wins, compared)
            in_band = (lo is not None and lo <= v_b <= hi)
            print(f"  {'OK' if improved else '!!'} {feat:31s} {v_a:>9} {v_b:>9} {delta:>9}  {bd:>16}"
                  f"  {wins}/{compared} wilcoxon_p={p:.3f} {'IN-BAND' if in_band else 'out'}")
            rows.append({
                "feature": feat,
                "defect_side": defect,
                "group": title,
                "v12_median": v_a,
                "v13_median": v_b,
                "delta": delta,
                "market_band": [lo, hi],
                "paired_v13_better": wins,
                "paired_compared": compared,
                "ties": ties,
                # 键名如实反映用了哪个检验。原来这里叫 sign_test_p,现在装的是
                # 签名秩的 p —— 名不副实的键会让报告读者误判方法。
                "wilcoxon_p": round(p, 4),
                "wilcoxon_method": wil["method"],
                "wilcoxon_n_used": wil["n_used"],
                "sign_test_p": round(p_sign, 4),
                "significant": p < 0.05,
                "v13_in_market_band": in_band,
                "improved": improved,
            })
        print()

    section("TARGETED by v13", TARGETED)
    section("CONTROL (not constrained by v13)", CONTROL)

    # ---- H2:元指代泄漏(v13 唯一新增的定向约束)-------------------------
    # 检验单元是**章级二元**(本章有/无泄漏),而不是逐章计数。原因:计数是
    # 零膨胀的(多数章 0 次、少数章 2-6 次),签名秩在这种分布上失效。
    # 检验用精确 McNemar —— 只有不一致配对携带信息。
    leak_a = [c["_meta_leak"] for c in arm_a]
    leak_b = [c["_meta_leak"] for c in arm_b]
    bin_a = [bool(c["_meta_leak_any"]) for c in arm_a]
    bin_b = [bool(c["_meta_leak_any"]) for c in arm_b]

    n_pair = min(len(bin_a), len(bin_b))
    b_only_a = sum(1 for i in range(n_pair) if bin_a[i] and not bin_b[i])   # v12 漏、v13 不漏
    c_only_b = sum(1 for i in range(n_pair) if bin_b[i] and not bin_a[i])   # v13 漏、v12 不漏
    concordant = n_pair - b_only_a - c_only_b
    leak_p = exact_mcnemar(b_only_a, c_only_b)
    rate_a = sum(bin_a[:n_pair]) / n_pair if n_pair else 0.0
    rate_b = sum(bin_b[:n_pair]) / n_pair if n_pair else 0.0

    print("== H2 META-LEAK 元指代泄漏（v13 唯一新增约束）==")
    print(f"  章级泄漏率 v12: {sum(bin_a[:n_pair])}/{n_pair} = {rate_a:.1%}")
    print(f"  章级泄漏率 v13: {sum(bin_b[:n_pair])}/{n_pair} = {rate_b:.1%}")
    print(f"  不一致配对: b(仅v12漏)={b_only_a}  c(仅v13漏)={c_only_b}  一致={concordant}")
    print(f"  精确 McNemar p={leak_p:.4f}  ({'显著' if leak_p < ALPHA else '不显著'} at α={ALPHA})")
    if b_only_a + c_only_b == 0:
        print("  注意:零不一致配对 => 无信息,不可判定(非'无效果')")
    elif b_only_a < MIN_CARDINALITY and c_only_b == 0:
        print(f"  注意:c=0 时需 b>={MIN_CARDINALITY} 才可能 p<0.05,当前 b={b_only_a} => 功效受限")
    print(f"  (计数口径供参考: v12 total={sum(leak_a)}  v13 total={sum(leak_b)})")

    # ---- H1:篇幅(v13 未新增约束 → 副作用/观察项,不是 v13 的功劳)------
    len_a = med([c["_chars"] for c in arm_a])
    len_b = med([c["_chars"] for c in arm_b])
    lo_l, hi_l = band(anchor, "_chars")
    chars_a = [float(c["_chars"]) for c in arm_a[:n_pair]]
    chars_b = [float(c["_chars"]) for c in arm_b[:n_pair]]
    len_wil = wilcoxon(chars_a, chars_b)
    print("== H1 SIDE EFFECT: length（v13 diff 中无任何篇幅约束）==")
    print(f"  v12 median chars: {len_a}" + (f"  ({len_a / hi_l:.2f}x market p75)" if hi_l else ""))
    print(f"  v13 median chars: {len_b}" + (f"  ({len_b / hi_l:.2f}x market p75)" if hi_l else ""))
    print(f"  配对 Wilcoxon p={len_wil['p_value']:.4f}  n={len_wil['n_used']}  [{len_wil['method']}]")

    targeted = [r for r in rows if r["group"] == "TARGETED by v13"]
    control = [r for r in rows if r["group"].startswith("CONTROL")]

    # 判据围绕 H2 重建。原来它围绕 TARGETED 构建,而 TARGETED 现在是空集
    # (v13 唯一新增的约束就是防泄漏,已单独按章级二元检验),`all([])` 恒为
    # True,会打印出"targeted all moved correctly: True (0/0)"这种空洞真值 ——
    # 一个永远为真的判据比没有判据更危险。
    h2_significant = leak_p < ALPHA
    h2_direction_ok = rate_b < rate_a
    h2_testable = (b_only_a + c_only_b) > 0

    # 对照的作用:若未被 v13 新增触及的特征也发生**显著**系统性移动,
    # 则两臂差异不能干净地归因于防泄漏约束(模型采样漂移的信号)。
    control_moved = [r["feature"] for r in control if r["significant"]]
    control_clean = not control_moved

    h1_significant = len_wil["p_value"] < ALPHA
    h1_direction = ("shorter" if (len_b or 0) < (len_a or 0)
                    else "longer" if (len_b or 0) > (len_a or 0) else "same")

    print("\n== VERDICT ==")
    print(f"  H2 可检验(有不一致配对)     : {h2_testable}")
    print(f"  H2 泄漏率方向正确(v13更低)   : {h2_direction_ok}  ({rate_a:.1%} → {rate_b:.1%})")
    print(f"  H2 精确 McNemar 显著        : {h2_significant} (p={leak_p:.4f})")
    print(f"  H1 篇幅变化方向             : {h1_direction} (p={len_wil['p_value']:.4f}, "
          f"{'显著' if h1_significant else '不显著'})")
    print(f"  对照未系统性移动(可归因)     : {control_clean}"
          + (f"  移动的对照={control_moved}" if control_moved else ""))
    print()
    if h2_significant and h2_direction_ok and control_clean:
        print("  => v13 防泄漏约束【有证据支持】")
    elif not h2_testable:
        print("  => 【不可判定】:零不一致配对,样本无信息(不等于'v13 无效')")
    elif h2_direction_ok and not h2_significant:
        print(f"  => 【方向对但不显著】:c={c_only_b} 时需 b>={MIN_CARDINALITY},实得 b={b_only_a}")
    elif not control_clean:
        print("  => 【归因不干净】:对照同步移动,差异可能来自采样漂移而非 v13")
    else:
        print("  => 【不支持】:泄漏率未朝目标方向下降")

    report = {
        "kind": "craft-ab-v12-vs-v13",
        "hypothesis": (
            "v13 唯一新增的是生成侧元指代防泄漏(v12→v13 diff 仅 8 行)。"
            "H2 = 章级泄漏率下降(定向);H1 = 篇幅变化(副作用观察,v13 未约束篇幅)"
        ),
        "method": {
            "hygiene": "OFF in both arms",
            # 如实记录:CLI 传了 temperature=0.0,但 gpt-5.6-sol 是推理模型,
            # 产物 produced_by.llm.temperature 记为 None(reasoning_effort=xhigh
            # 取代了温度采样)。所以不能声称"逐章可复现",配对设计吸收采样噪声。
            "temperature_requested": 0.0,
            "temperature_recorded": None,
            "reasoning_effort": "xhigh",
            "paired": "per-chapter N vs N (pooled across stories)",
            "instrument": "runtime.reference.measure + tools/meta_leak.py",
            "h2_test": "chapter-level binary + exact McNemar (tools/ab_stats.py)",
            "h1_test": "paired Wilcoxon signed-rank (tools/ab_stats.py)",
            "natural_controls": list(CONTROL),
            "alpha": ALPHA,
        },
        "chapters": {
            "v12_measured": len(raw_a),
            "v13_measured": len(raw_b),
            "paired": n_pair,
            "paired_chapter_numbers": common,
            "unpaired_only_v12": dropped_a,
            "unpaired_only_v13": dropped_b,
        },
        "rows": rows,
        "length_side_effect": {
            "v12_median_chars": len_a,
            "v13_median_chars": len_b,
            "market_p75": hi_l,
            "worsened": (len_b or 0) > (len_a or 0),
            "wilcoxon_p": round(len_wil["p_value"], 4),
            "wilcoxon_method": len_wil["method"],
            "wilcoxon_n_used": len_wil["n_used"],
            "significant": h1_significant,
            "direction": h1_direction,
        },
        "meta_leak": {
            "v12_per_chapter_counts": leak_a,
            "v13_per_chapter_counts": leak_b,
            "v12_chapters_with_leak": sum(bin_a[:n_pair]),
            "v13_chapters_with_leak": sum(bin_b[:n_pair]),
            "v12_leak_rate": round(rate_a, 4),
            "v13_leak_rate": round(rate_b, 4),
            "discordant_b_only_v12": b_only_a,
            "discordant_c_only_v13": c_only_b,
            "concordant_pairs": concordant,
            "exact_mcnemar_p": round(leak_p, 4),
            "min_discordant_for_significance": MIN_CARDINALITY,
            "testable": h2_testable,
        },
        "verdict": {
            "h2_testable": h2_testable,
            "h2_direction_ok": h2_direction_ok,
            "h2_significant": h2_significant,
            "h1_direction": h1_direction,
            "h1_significant": h1_significant,
            "controls_clean": control_clean,
            "controls_that_moved": control_moved,
            "supported": bool(h2_significant and h2_direction_ok and control_clean),
        },
        "limitations": [
            "单项目章数硬顶 33(plan_chapters 一事件一章),故 n=60/臂不可达;"
            "改为双故事池化(lingse+guhai)得 66 配对",
            "gpt-5.6-sol 是推理模型,temperature 未被记录(reasoning_effort=xhigh),"
            "故逐章非字节可复现;配对设计吸收采样噪声",
            "pricing 表无 92code:gpt-5.6-sol 键 => 成本折 null,"
            "--budget-limit 对本 provider 失效(loop.py:862 把 None 折成 0)",
            "guhai 故事基线泄漏率 0% => 对 H2 不贡献不一致配对,"
            "H2 的统计功效实质来自 lingse 分层",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # 用 os.path.relpath 而不是 Path.relative_to:后者在 out 是相对路径时抛
    # ValueError,报告已写盘却以非零退出,看起来像整轮失败。
    try:
        shown = os.path.relpath(args.out.resolve(), ROOT)
    except ValueError:
        shown = str(args.out)
    print(f"\nwrote {shown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
