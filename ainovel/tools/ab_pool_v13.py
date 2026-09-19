"""ab_pool_v13.py — v12-vs-v13 的池化判据(两个故事合并检验)。

为什么必须池化:单项目章数硬顶 33(`plan_chapters` 一事件一章,
`serialize/loop.py:211`,`max_chapters` 只能截断不能延长),所以设计文档要求的
n=60/臂在单一项目上物理不可达。改为**两个不同故事**各跑 v12/v13 双臂,
按 (故事, 章号) 配对池化 —— 样本量达标,且结论不绑死单一本书,泛化性更强。

统计上池化是合法的:精确 McNemar 只用**不一致配对**,把两个故事的
b(仅 v12 漏)与 c(仅 v13 漏)相加即得池化检验统计量(分层 Mantel-Haenszel
在二元配对下退化为此)。H1 则把两故事的配对差值合并做签名秩。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "AI-Novel-Runtime"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ab_craft_v13 import CONTROL, load_arm, med  # noqa: E402
from ab_stats import exact_mcnemar, mcnemar_min_discordant, wilcoxon  # noqa: E402

ALPHA = 0.05
STORIES = {"lingse": ("v13ab-lingse-v12", "v13ab-lingse-v13"),
           "guhai": ("v13ab-guhai-v12", "v13ab-guhai-v13")}


def pair_arm(a_dir: Path, b_dir: Path):
    """按真实章号内连接两臂,返回对齐后的 (v12, v13) 列表。"""
    ra, rb = load_arm(a_dir), load_arm(b_dir)
    by_a = {c["_index"]: c for c in ra}
    by_b = {c["_index"]: c for c in rb}
    common = sorted(set(by_a) & set(by_b))
    return ([by_a[i] for i in common], [by_b[i] for i in common], common,
            sorted(set(by_a) - set(by_b)), sorted(set(by_b) - set(by_a)))


def main() -> int:
    strata = {}
    pooled_b = pooled_c = pooled_conc = 0
    pooled_len_a: list[float] = []
    pooled_len_b: list[float] = []
    pooled_ctrl: dict[str, tuple[list[float], list[float]]] = {
        f: ([], []) for f in CONTROL
    }

    print("=== v12 vs v13 池化 A/B(两故事,按真实章号配对)===\n")
    for story, (ad, bd) in STORIES.items():
        arm_a, arm_b, common, only_a, only_b = pair_arm(ROOT / ad, ROOT / bd)
        n = len(common)
        bin_a = [bool(c["_meta_leak_any"]) for c in arm_a]
        bin_b = [bool(c["_meta_leak_any"]) for c in arm_b]
        b = sum(1 for i in range(n) if bin_a[i] and not bin_b[i])
        c = sum(1 for i in range(n) if bin_b[i] and not bin_a[i])
        conc = n - b - c
        pooled_b += b
        pooled_c += c
        pooled_conc += conc

        la = [float(x["_chars"]) for x in arm_a]
        lb = [float(x["_chars"]) for x in arm_b]
        pooled_len_a += la
        pooled_len_b += lb
        for f in CONTROL:
            for i in range(n):
                x, y = arm_a[i].get(f), arm_b[i].get(f)
                if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                    pooled_ctrl[f][0].append(float(x))
                    pooled_ctrl[f][1].append(float(y))

        strata[story] = {
            "paired": n, "unpaired_only_v12": only_a, "unpaired_only_v13": only_b,
            "v12_leak_chapters": sum(bin_a), "v13_leak_chapters": sum(bin_b),
            "v12_leak_rate": round(sum(bin_a) / n, 4) if n else None,
            "v13_leak_rate": round(sum(bin_b) / n, 4) if n else None,
            "discordant_b_only_v12": b, "discordant_c_only_v13": c,
            "concordant": conc,
            "exact_mcnemar_p": round(exact_mcnemar(b, c), 4),
            "v12_median_chars": med(la), "v13_median_chars": med(lb),
        }
        print(f"[{story}] 配对 {n} 章"
              + (f"  (未配对: 仅v12={only_a} 仅v13={only_b})" if only_a or only_b else ""))
        print(f"   章级泄漏率 v12 {sum(bin_a)}/{n} → v13 {sum(bin_b)}/{n}"
              f"   不一致 b={b} c={c}  p={exact_mcnemar(b, c):.4f}")
        print(f"   篇幅中位 {med(la)} → {med(lb)}")

    # ---- 池化 H2 --------------------------------------------------------
    p_pool = exact_mcnemar(pooled_b, pooled_c)
    n_pool = len(pooled_len_a)
    min_b = mcnemar_min_discordant(ALPHA)
    print(f"\n=== 池化 H2:元指代泄漏(v13 唯一新增约束)===")
    print(f"  池化配对数        : {n_pool}")
    print(f"  不一致配对        : b(仅v12漏)={pooled_b}  c(仅v13漏)={pooled_c}  一致={pooled_conc}")
    print(f"  精确 McNemar p    : {p_pool:.4f}  ({'显著' if p_pool < ALPHA else '不显著'} at α={ALPHA})")
    print(f"  显著所需最小 b    : {min_b} (当 c=0)")

    # ---- 池化 H1 --------------------------------------------------------
    wl = wilcoxon(pooled_len_a, pooled_len_b)
    print(f"\n=== 池化 H1:篇幅(v13 未约束篇幅,属副作用观察)===")
    print(f"  中位 {med(pooled_len_a)} → {med(pooled_len_b)}")
    print(f"  配对 Wilcoxon p={wl['p_value']:.4f}  n={wl['n_used']}  [{wl['method']}]")

    # ---- 池化天然对照 ----------------------------------------------------
    print(f"\n=== 池化天然对照(未被 v13 新增约束触及)===")
    ctrl_rows = []
    moved = []
    for f, (xa, xb) in pooled_ctrl.items():
        if not xa:
            continue
        w = wilcoxon(xa, xb)
        sig = w["p_value"] < ALPHA
        if sig:
            moved.append(f)
        ctrl_rows.append({"feature": f, "v12_median": med(xa), "v13_median": med(xb),
                          "wilcoxon_p": round(w["p_value"], 4), "significant": sig,
                          "n_used": w["n_used"]})
        print(f"  {'!!' if sig else 'ok'} {f:34s} {med(xa):>8} → {med(xb):<8} p={w['p_value']:.4f}")

    direction_ok = pooled_c < pooled_b
    testable = (pooled_b + pooled_c) > 0
    controls_clean = not moved
    supported = (p_pool < ALPHA) and direction_ok and controls_clean

    print(f"\n=== 判据 ===")
    print(f"  H2 可检验              : {testable}")
    print(f"  H2 方向正确(v13 更少)  : {direction_ok}")
    print(f"  H2 统计显著            : {p_pool < ALPHA}")
    print(f"  对照未系统性移动        : {controls_clean}" + (f" 移动={moved}" if moved else ""))
    print()
    if supported:
        print("  => v13 防泄漏约束【有证据支持】")
    elif not testable:
        print("  => 【不可判定】:零不一致配对,样本无信息")
    elif direction_ok:
        print(f"  => 【方向一致但未达显著】:b={pooled_b} c={pooled_c},"
              f"c=0 时需 b>={min_b}")
        print("     基线泄漏率过低导致不一致配对不足 —— 这是功效问题,"
              "不是 v13 无效的证据")
    else:
        print("  => 【不支持】")

    report = {
        "kind": "craft-ab-v12-vs-v13-pooled",
        "design": {
            "reason_for_pooling": (
                "单项目章数硬顶 33(plan_chapters 一事件一章),n=60/臂不可达;"
                "改双故事池化,兼得样本量与泛化性"
            ),
            "stories": list(STORIES),
            "pairing_unit": "(story, real chapter number)",
            "h2_test": "exact McNemar on chapter-level binary leak",
            "h1_test": "paired Wilcoxon signed-rank on chars",
            "hygiene": "OFF in both arms",
            "model": "gpt-5.6-sol via 92code (reasoning model)",
            "temperature_requested": 0.0,
            "temperature_recorded": None,
            "alpha": ALPHA,
        },
        "strata": strata,
        "pooled_h2": {
            "n_pairs": n_pool,
            "discordant_b_only_v12": pooled_b,
            "discordant_c_only_v13": pooled_c,
            "concordant": pooled_conc,
            "exact_mcnemar_p": round(p_pool, 4),
            "min_discordant_for_significance": min_b,
            "direction_ok": direction_ok,
            "significant": p_pool < ALPHA,
        },
        "pooled_h1_length": {
            "v12_median_chars": med(pooled_len_a),
            "v13_median_chars": med(pooled_len_b),
            "wilcoxon_p": round(wl["p_value"], 4),
            "method": wl["method"],
            "n_used": wl["n_used"],
            "significant": wl["p_value"] < ALPHA,
        },
        "pooled_controls": ctrl_rows,
        "verdict": {
            "h2_testable": testable,
            "h2_direction_ok": direction_ok,
            "h2_significant": p_pool < ALPHA,
            "controls_clean": controls_clean,
            "controls_that_moved": moved,
            "supported": supported,
        },
        "limitations": [
            "gpt-5.6-sol 是推理模型,temperature 未记录(reasoning_effort=xhigh),"
            "逐章非字节可复现;配对设计吸收采样噪声",
            "pricing 表无 92code:gpt-5.6-sol 键 => 成本折 null,"
            "--budget-limit 对本 provider 失效(loop.py:862 把 None 折 0)",
            "基线元指代泄漏率实测远低于设计文档假设的 35%,"
            "不一致配对不足是本轮功效的主要限制",
            "guhai-v13 ch21 撞硬红线被拦(ADR-003 合法 gate),该章整对丢弃",
        ],
    }
    out = ROOT / "docs" / "craft-ab-v12-v13-pooled.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {os.path.relpath(out, ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
