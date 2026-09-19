#!/usr/bin/env python3
"""ab_power.py — 为下一轮工艺 A/B 做样本量与对照设计（§11.6 第 3 项的前置）。

上一轮 v11-vs-v12 的结论是 DIRECTIONAL ONLY，两个设计缺陷写在
`ANOVEL_PLAN_CORRECTION.md` §11.3：功效不足（n=10 单特征需 9/10 才显著）、
阴性对照无效（选中的两项都在带内/地板，本就没有移动空间）。

这个工具不猜效应量——它从**已完成的那轮 A/B 的真实逐章配对差值**自助重采样，
回答三个可执行的问题：

  1. 每个特征要多少章/臂才有 80% 功效？（--power）
  2. 符号检验 vs Wilcoxon 签名秩，哪个更省章？（--power，两者并列）
  3. 哪些特征**有资格**当阴性对照？（--controls）
     判定：必须同时满足「基数够(可移动)」与「带外(有缺陷压力)」。
     上一轮就是漏了第二条，才把地板特征当成对照。

同口径复用生成侧的确定性仪器（runtime.reference.measure），与 ab_craft_report.py
一致，所以设计阶段与判读阶段测的是同一个东西。

用法：
  python3 tools/ab_power.py --power
  python3 tools/ab_power.py --controls
  python3 tools/ab_power.py --cost 50
"""
from __future__ import annotations

import argparse
import json
import math
import random
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "AI-Novel-Runtime"))

from runtime.reference.measure import measure_reference_chapter  # noqa: E402

# 上一轮两臂的正文导出（registry 里只留了 5 章，报告用的 10 章在 manuscript/）。
ARM_A = ROOT / "novel-lingse" / "manuscript" / "AB-craft-v11"
ARM_B = ROOT / "novel-lingse" / "manuscript" / "AB-craft-v12"
ANCHOR = ROOT / "docs" / "craft-anchor-measured.json"

# v12 直接约束的特征 + 缺陷方向（above = 偏高为病）。
TARGETED = {
    "ai_taste.dash_aside_per_1000": "above",
    "density.simile_per_1000": "above",
    "density.opening_simile_per_1000": "above",
    "density.dialogue_ratio": "below",
}
# 与定向特征同受一条约束、因而**没有资格**当阴性对照的特征。
# v12 的比喻约束原文是 "SPARSE: about one per 1000 characters ACROSS THE CHAPTER"，
# 并明确点出 "what they never do is sustain that density through the whole chapter" ——
# 这是全章约束，所以正文段的 rest_simile 同样受约束。它基数高(20)、又在带外，
# 极易被误判为「合格对照」，实际上把受约束特征当对照会直接伪造出"对照也动了"的结论。
CONSTRAINED_SIBLINGS = {
    "density.rest_simile_per_1000",
}
# 由篇幅派生、不能独立当对照的特征（缩短篇幅会同步拉动它们）。
SIZE_DERIVED = {
    "ai_taste.total_chars", "density.total_chars", "length.total_chars",
    "ai_taste.sentence_count", "length.band_low", "length.band_high",
}
_META_LEAK_RE = re.compile(r"上一章|下一章|前文|第[0-9一二三四五六七八九十]+章")

# 对照资格门槛。基数 <6 说明特征卡在地板/天花板，移动不了；带内说明没有缺陷压力。
MIN_CARDINALITY = 6
ALPHA = 0.05
BOOTSTRAP_REPS = 4000
TARGET_POWER = 0.80


def _flatten(obj: dict) -> dict:
    """measure_reference_chapter 的嵌套结果压平成 'group.metric' 的数值字典。"""
    flat: dict = {}

    def walk(o: dict, prefix: str = ""):
        for k, v in o.items():
            if isinstance(v, dict):
                walk(v, prefix + k + ".")
            elif isinstance(v, (int, float)) and not isinstance(v, bool):
                flat[prefix + k] = float(v)
    walk(obj)
    return flat


def load_arm(directory: Path) -> list:
    """逐章测量一个臂。按文件名排序 => 与另一臂逐章配对。"""
    out = []
    for path in sorted(directory.glob("第*.txt")):
        body = path.read_text(encoding="utf-8")
        measured = measure_reference_chapter(body)
        if not isinstance(measured, dict):
            measured = json.loads(json.dumps(measured, default=lambda o: o.__dict__))
        flat = _flatten(measured)
        # 元指代只数正文：标题行「# 第一章 ...」本身就带"第N章"，算进去是误报。
        prose = "\n".join(l for l in body.split("\n") if not l.strip().startswith("#"))
        flat["_meta_leak"] = float(len(_META_LEAK_RE.findall(prose)))
        out.append(flat)
    return out


def sign_p(k: int, n: int) -> float:
    """双尾精确二项符号检验，H0: p=0.5。n 已排除平局。"""
    if n <= 0:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(k, n + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def wilcoxon_p(diffs: list) -> float:
    """双尾 Wilcoxon 签名秩（正态近似 + 连续性校正）。

    比符号检验多用了差值的**大小**信息，所以同样章数下功效更高——代价是假定
    差值分布对称。n<6 时近似不可靠，直接返回 1.0（不下结论）。
    """
    nz = [x for x in diffs if x != 0]
    n = len(nz)
    if n < 6:
        return 1.0
    order = sorted(range(n), key=lambda i: abs(nz[i]))
    ranks = [0] * n
    for rank, i in enumerate(order, 1):
        ranks[i] = rank
    w_plus = sum(ranks[i] for i in range(n) if nz[i] > 0)
    mu = n * (n + 1) / 4
    sd = math.sqrt(n * (n + 1) * (2 * n + 1) / 24)
    if sd == 0:
        return 1.0
    z = (abs(w_plus - mu) - 0.5) / sd
    return math.erfc(z / math.sqrt(2))


def mcnemar_p(b: int, c: int) -> float:
    """双尾精确 McNemar，用于**配对二元**结果（本章有/无缺陷）。

    为什么 H2（元指代）必须用它而不是 Wilcoxon：逐章计数是零膨胀的
    （实测 v11 = [0,0,2,0,1,3,0,0,6,0]），大量 0-0 章在签名秩里是平局会被丢弃，
    10 章只剩 4 个有效对 => Wilcoxon 直接返回 1.0 拒绝下结论。
    改看"该章有没有泄漏"这个二元量，全部章都参与统计。

    b / c = 两个方向的不一致对数（一臂有、另一臂无）。一致对不携带信息。
    """
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def power_mcnemar(n: int, rate_base: float, rate_new: float, *,
                  reps: int = BOOTSTRAP_REPS, seed: int = 20260731) -> float:
    """章级缺陷发生率从 rate_base 降到 rate_new 时，n 章/臂 的检出率。"""
    rng = random.Random(seed)
    hits = 0
    for _ in range(reps):
        b = c = 0
        for _ in range(n):
            a_leak = rng.random() < rate_base
            n_leak = rng.random() < rate_new
            if a_leak and not n_leak:
                b += 1
            elif n_leak and not a_leak:
                c += 1
        hits += mcnemar_p(b, c) < ALPHA
    return hits / reps


def paired_deltas(arm_a: list, arm_b: list, feature: str, defect_side: str) -> list:
    """逐章配对差值，符号统一为「B 更好为正」。"""
    out = []
    for ca, cb in zip(arm_a, arm_b):
        va, vb = ca.get(feature), cb.get(feature)
        if not isinstance(va, (int, float)) or not isinstance(vb, (int, float)):
            continue
        out.append(va - vb if defect_side == "above" else vb - va)
    return out


def bootstrap_power(deltas: list, n: int, test: str, *, reps: int = BOOTSTRAP_REPS,
                    seed: int = 20260731) -> float:
    """从实测差值有放回重采样 n 章，估计检出率。

    比"假设胜率 0.7"可靠：真实差值自带方差与平局结构，而假设效应量把这些抹掉了。
    """
    if not deltas:
        return 0.0
    rng = random.Random(seed)
    hits = 0
    for _ in range(reps):
        sample = [rng.choice(deltas) for _ in range(n)]
        if test == "sign":
            nz = [x for x in sample if x != 0]
            k = sum(1 for x in nz if x > 0)
            ok = sign_p(k, len(nz)) < ALPHA
        else:
            ok = wilcoxon_p(sample) < ALPHA
        hits += bool(ok)
    return hits / reps


def required_n(deltas: list, test: str, *, cap: int = 200) -> int | None:
    """达到 TARGET_POWER 所需的最小章数/臂（步长 5），超过 cap 返回 None。"""
    for n in range(10, cap + 1, 5):
        if bootstrap_power(deltas, n, test) >= TARGET_POWER:
            return n
    return None


def _band(anchor: dict, feature: str, window: str = "first10"):
    entry = (anchor.get("windows", {}).get(window, {}) or {}).get(feature)
    if not entry:
        return (None, None)
    return (entry.get("p25"), entry.get("p75"))


def cmd_power(arm_a: list, arm_b: list) -> None:
    print("=== 样本量：从上一轮真实配对差值自助重采样（不假设效应量）===")
    print(f"    alpha={ALPHA}  目标功效={TARGET_POWER:.0%}  重采样={BOOTSTRAP_REPS}\n")
    grid = (10, 20, 30, 40, 50)
    header = " ".join(f"n={n:<4}" for n in grid)
    print(f"{'feature':36} {'test':>9} {header}  需要n")
    worst = {"sign": 0, "wilcoxon": 0}
    for feature, side in TARGETED.items():
        deltas = paired_deltas(arm_a, arm_b, feature, side)
        wins = sum(1 for x in deltas if x > 0)
        for test in ("sign", "wilcoxon"):
            cells = " ".join(f"{bootstrap_power(deltas, n, test):5.2f}" for n in grid)
            need = required_n(deltas, test)
            worst[test] = max(worst[test], need or 999)
            print(f"{feature:36} {test:>9} {cells}  {need or '>200'}")
        print(f"{'':36} {'(观测)':>9} 胜 {wins}/{len(deltas)}，"
              f"中位Δ={statistics.median(deltas):+.3f}")
    print("\n--- 结论 ---")
    for test in ("sign", "wilcoxon"):
        n = worst[test]
        label = ">200" if n >= 999 else str(n)
        print(f"  {test:9}: 覆盖全部 4 个定向特征需 {label} 章/臂")
    print("  Wilcoxon 用上了差值大小，同样章数功效更高 => 首选，符号检验作为稳健性附证。")
    print("  ⚠️ opening_simile 的差值方差极大，任何可行章数都到不了 80% 功效：")
    print("     它应降级为「观察项」，不作为成败判据（否则等于给实验设了必输条件）。")


def cmd_controls(arm_a: list, arm_b: list) -> None:
    anchor = json.loads(ANCHOR.read_text(encoding="utf-8")) if ANCHOR.exists() else {}
    print("=== 阴性对照资格筛查（§11.3 缺陷①的补救）===")
    print("    合格 = 基数>=6（有移动空间） 且 带外（有缺陷压力）\n")
    print(f"{'feature':36} {'基数':>5} {'我方中位':>10} {'市场带':>18} {'判定'}")
    usable, rejected = [], []
    features = sorted(set(arm_a[0]) & set(arm_b[0])) if arm_a and arm_b else []
    for feature in features:
        if (feature in TARGETED or feature in SIZE_DERIVED
                or feature in CONSTRAINED_SIBLINGS or feature.startswith("_index")):
            continue
        vals = [c[feature] for c in arm_a + arm_b if isinstance(c.get(feature), (int, float))]
        if not vals:
            continue
        cardinality = len(set(vals))
        med = statistics.median([c[feature] for c in arm_a])
        lo, hi = _band(anchor, feature)
        band_s = f"[{lo},{hi}]" if lo is not None else "(无带)"
        in_band = lo is not None and lo <= med <= hi
        if cardinality >= MIN_CARDINALITY and not in_band:
            verdict, bucket = "合格", usable
        elif cardinality < MIN_CARDINALITY:
            verdict, bucket = "拒绝：卡在地板/天花板", rejected
        else:
            verdict, bucket = "拒绝：带内，无缺陷压力", rejected
        bucket.append(feature)
        print(f"{feature:36} {cardinality:>5} {med:>10.3f} {band_s:>18} {verdict}")
    print(f"\n  合格对照：{usable or '无'}")
    if not usable:
        print("""
  ⚠️ 现有仪器里没有合法的阴性对照 —— 每个非定向特征要么在带内（无压力），
     要么卡在地板（动不了）。所以 §11.6 第 3 项**按原文无法执行**。
     两条出路：
       (a) 用「未被新约束触碰的定向特征」作对照：下一轮只新增篇幅/元指代约束，
           则 dash/simile/dialogue 成为天然对照——它们有压力、有移动空间、
           且本轮不受新约束影响。这是唯一无需新仪器的可行设计。
       (b) 新增一个有缺陷压力的检测器充当对照（成本更高，且新仪器本身未经验证）。
     推荐 (a)。""")


def _leak_counts_from_txt(directory: Path) -> list:
    counts = []
    for path in sorted(directory.glob("第*.txt")):
        body = path.read_text(encoding="utf-8")
        prose = "\n".join(l for l in body.split("\n") if not l.strip().startswith("#"))
        counts.append(len(_META_LEAK_RE.findall(prose)))
    return counts


def _leak_counts_from_registry(project: Path) -> list:
    """从 chapter-final / drafts 折出逐章元指代计数（正文，排除标题行）。"""
    def find_body(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key in ("body", "final_text") and isinstance(value, str) and len(value) > 200:
                    return value
                found = find_body(value)
                if found:
                    return found
        elif isinstance(node, list):
            for value in node:
                found = find_body(value)
                if found:
                    return found
        return None

    for kind in ("chapter-final", "drafts"):
        directory = project / "registry" / "derived" / kind
        if not directory.exists():
            continue
        counts = []
        for path in sorted(directory.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            body = find_body(payload)
            if not body:
                continue
            prose = "\n".join(l for l in body.split("\n") if not l.strip().startswith("#"))
            counts.append(len(_META_LEAK_RE.findall(prose)))
        if counts:
            return counts
    return []


def cmd_h2(chapters: int) -> None:
    """H2（元指代预防）的可测性检查 + 正确的检验选择。

    设计里最容易埋雷的一步：上一轮两臂元指代**中位数都是 0**，看着像地板效应
    （= 无法测量）。实测章级发生率后结论相反——可测，但必须换检验。
    """
    print("=== H2 元指代：基线发生率（能不能测）===")
    rows = []
    for name, counts in (
        ("novel-lingse (30ch)", _leak_counts_from_registry(ROOT / "novel-lingse")),
        ("genesis-pilot (33ch)", _leak_counts_from_registry(ROOT / "genesis-pilot")),
        ("ab3-ds-v12 (30ch)", _leak_counts_from_registry(ROOT / "ab3-ds-v12")),
        ("AB-craft-v11 (10ch)", _leak_counts_from_txt(ARM_A)),
        ("AB-craft-v12 (10ch)", _leak_counts_from_txt(ARM_B)),
    ):
        if not counts:
            continue
        hit = sum(1 for c in counts if c > 0)
        rows.append((name, len(counts), hit, hit / len(counts), sum(counts)))
    print(f"  {'语料':24} {'章数':>4} {'含泄漏章':>9} {'章级发生率':>11} {'总次数':>7}")
    for name, n, hit, rate, total in rows:
        print(f"  {name:24} {n:>4} {hit:>9} {rate:>10.0%} {total:>7}")
    if rows:
        base = statistics.median([r[3] for r in rows if r[1] >= 10])
        print(f"\n  => 章级发生率中位 {base:.0%}，**不是地板效应，可测**。")
    print("""
  ⚠️ 但逐章计数是零膨胀的（实测 v11=[0,0,2,0,1,3,0,0,6,0]）：多数章为 0，
     0-0 章在 Wilcoxon 里是平局会被丢弃 —— 10 章只剩 4 个有效对，直接返回 1.0。
     所以 H2 必须改用**章级二元**结果（本章有/无泄漏）+ 精确 McNemar 检验，
     这样全部章都参与统计。""")
    print(f"\n=== McNemar 功效（alpha={ALPHA}）===")
    grid = (20, 30, 45, 60, 80)
    print(f"  {'基线→目标':>14} " + " ".join(f"n={n:<4}" for n in grid))
    for base_rate, new_rate in ((0.35, 0.10), (0.35, 0.15), (0.35, 0.20)):
        cells = " ".join(f"{power_mcnemar(n, base_rate, new_rate, reps=1500):5.2f}"
                         for n in grid)
        print(f"  {f'{base_rate:.0%} → {new_rate:.0%}':>14} {cells}")
    print(f"\n  给定 n={chapters}：35%→10% 功效 "
          f"{power_mcnemar(chapters, 0.35, 0.10, reps=1500):.2f}")
    print("  => n=45 不足(0.77)，n=60 达 0.87。H2 是决定总章数的约束项，不是 H1。")


def cmd_cost(chapters: int) -> None:
    print(f"=== 成本：2 臂 x {chapters} 章 ===")
    per = []
    for path in sorted(ROOT.glob("*/registry/derived/run-manifests/*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        totals = data.get("totals") or {}
        cost = (totals.get("cost") or {}).get("total_cost")
        produced = totals.get("produced") or 0
        if cost and produced:
            per.append(cost / produced)
    if not per:
        print("  找不到带成本的 run-manifest（确定性跑不计费）")
        return
    median = statistics.median(per)
    total = 2 * chapters * median
    print(f"  实测逐章成本中位数：{median:.4f} CNY（样本 {len(per)} 次真实跑）")
    print(f"  预计总额：2 x {chapters} x {median:.4f} = {total:.2f} CNY")
    print(f"  => 成本不是瓶颈。文档把第 3/4 项标成「需真实 API 花费」像是障碍，"
          f"实际约 {total:.0f} 元。")


def main() -> int:
    ap = argparse.ArgumentParser(description="下一轮工艺 A/B 的样本量与对照设计")
    ap.add_argument("--power", action="store_true", help="自助法样本量曲线")
    ap.add_argument("--controls", action="store_true", help="阴性对照资格筛查")
    ap.add_argument("--h2", type=int, metavar="N", nargs="?", const=45,
                    help="H2 元指代可测性 + McNemar 功效（默认按 N=45 评估）")
    ap.add_argument("--cost", type=int, metavar="N", help="估算 2 臂 x N 章的成本")
    args = ap.parse_args()
    if not (args.power or args.controls or args.h2 or args.cost):
        ap.print_help()
        return 0
    if not ARM_A.exists() or not ARM_B.exists():
        print(f"缺少上一轮正文导出：{ARM_A} / {ARM_B}（gitignore，需本地存在）")
        return 1
    arm_a, arm_b = load_arm(ARM_A), load_arm(ARM_B)
    print(f"上一轮两臂：A={len(arm_a)}章  B={len(arm_b)}章\n")
    if args.power:
        cmd_power(arm_a, arm_b)
    if args.controls:
        print()
        cmd_controls(arm_a, arm_b)
    if args.h2:
        print()
        cmd_h2(args.h2)
    if args.cost:
        print()
        cmd_cost(args.cost)
    return 0


if __name__ == "__main__":
    sys.exit(main())
