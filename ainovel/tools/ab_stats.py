"""ab_stats.py — A/B 实验用的配对检验(不依赖 scipy)。

本仓库环境没有 scipy(已验证 `import scipy` 失败),所以这里自实现两个检验:

  * exact_mcnemar  — 章级二元结果的精确 McNemar(二项检验)
  * wilcoxon       — 配对连续量的签名秩检验(小样本精确,大样本正态近似+并列校正)

为什么两个都要:零膨胀的计数(多数章 0 次、少数章 2-6 次)不能用签名秩,
必须降为章级二元 + McNemar;而篇幅这类连续量则该用签名秩,它比符号检验
功效更高(`tools/ab_craft_v13.py` 原来只有 sign_p,白扔功效)。
"""
from __future__ import annotations

import math
from itertools import product


def exact_mcnemar(b: int, c: int) -> float:
    """精确 McNemar 的双尾 p 值。

    b = 仅 A 臂出现的配对数,c = 仅 B 臂出现的配对数。
    一致配对(两臂都出现/都不出现)不携带信息,不参与检验 —— 这正是
    McNemar 的要点。在 H0 下不一致配对服从 Binomial(b+c, 0.5)。
    """
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def mcnemar_min_discordant(alpha: float = 0.05) -> int:
    """在 c=0 的最好情况下,达到显著所需的最小 b。

    这是判据的现实约束:b=5 时 p=0.0625 仍不显著,必须 b>=6。
    实验设计若期望的不一致配对数低于此,则功效先天不足。
    """
    b = 1
    while b < 1000:
        if exact_mcnemar(b, 0) < alpha:
            return b
        b += 1
    return -1


def _rank_abs(values: list[float]) -> tuple[list[float], list[int]]:
    """|d| 的平均秩 + 并列组大小(用于方差校正)。"""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    tie_sizes: list[int] = []
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0          # 平均秩(1-based)
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        if j > i:
            tie_sizes.append(j - i + 1)
        i = j + 1
    return ranks, tie_sizes


def _norm_sf(z: float) -> float:
    """标准正态的上尾概率。"""
    return 0.5 * math.erfc(z / math.sqrt(2.0))


def wilcoxon(x: list[float], y: list[float], *, exact_max_n: int = 18) -> dict:
    """配对 Wilcoxon 签名秩检验(双尾)。

    检验 y-x 的分布是否对称于 0。零差值按标准做法剔除(Wilcoxon 原始处理)。
    n <= exact_max_n 时枚举全部 2^n 符号组合得精确 p;更大时用正态近似,
    并对并列秩做方差校正 —— 篇幅数据几乎无并列,但泄漏计数会有很多。
    """
    diffs = [float(b) - float(a) for a, b in zip(x, y)]
    nonzero = [d for d in diffs if d != 0.0]
    n_zero = len(diffs) - len(nonzero)
    n = len(nonzero)
    if n == 0:
        return {"n_pairs": len(diffs), "n_used": 0, "n_zero": n_zero,
                "w_plus": 0.0, "p_value": 1.0, "method": "degenerate(all-ties)"}

    abs_d = [abs(d) for d in nonzero]
    ranks, tie_sizes = _rank_abs(abs_d)
    w_plus = sum(r for d, r in zip(nonzero, ranks) if d > 0)
    w_minus = sum(r for d, r in zip(nonzero, ranks) if d < 0)

    if n <= exact_max_n:
        # 精确:枚举每个 |d| 的符号,统计 W+ 的零分布。
        #
        # 注意 |d| 有并列时这条路径**依然精确**:符号翻转枚举是条件于观测 |d|
        # 的置换检验,并列只让查表临界值失效,不让枚举失效。早先这里多了个
        # `and not tie_sizes`,结果 |d| 全并列的数据(差值恒定,例如每章都
        # 恰好长 1 字)被踢到正态近似,教科书例 n=10 全正差值算出 0.001565
        # 而非精确的 0.001953 —— 精确路径实际从未被走到。
        total = 2 ** n
        stat = min(w_plus, w_minus)
        count = 0
        for signs in product((0, 1), repeat=n):
            wp = sum(r for s, r in zip(signs, ranks) if s)
            if min(wp, sum(ranks) - wp) <= stat:
                count += 1
        p = min(1.0, count / total)
        method = "exact"
    else:
        mean = n * (n + 1) / 4.0
        var = n * (n + 1) * (2 * n + 1) / 24.0
        var -= sum(t ** 3 - t for t in tie_sizes) / 48.0
        if var <= 0:
            return {"n_pairs": len(diffs), "n_used": n, "n_zero": n_zero,
                    "w_plus": w_plus, "p_value": 1.0, "method": "degenerate(zero-var)"}
        z = (w_plus - mean) / math.sqrt(var)
        p = min(1.0, 2 * _norm_sf(abs(z)))
        method = f"normal-approx(z={z:.4f}, tie-corrected)"

    return {"n_pairs": len(diffs), "n_used": n, "n_zero": n_zero,
            "w_plus": w_plus, "w_minus": w_minus,
            "p_value": p, "method": method}


def sign_test(wins: int, compared: int) -> float:
    """符号检验双尾 p(保留作对照,功效低于签名秩)。"""
    if compared <= 0:
        return 1.0
    tail = sum(math.comb(compared, i) for i in range(wins, compared + 1)) / 2 ** compared
    return min(1.0, 2 * tail)
