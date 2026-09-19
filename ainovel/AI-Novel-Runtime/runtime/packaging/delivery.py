"""delivery.py — deterministic 承诺一致性 check (规范 §3.3).

§3.3: every promise the packaging makes must be cashed in the first three chapters
— promise a 金手指 and it must be used effectively at least once; promise 复仇 and
the target and the action must be named; promise 智斗 and the chapter's central
problem must not be solved by coincidence.

Nothing in this project checked that link. The packaging layer decides 点击 (whether
a reader opens the book) and its promises decide whether the opening chapters read
as honored or as bait — the two funnel terms with the most reader loss and, until
now, the least tooling.

WHAT IT MEASURES:
For each authored promise, whether its AUTHORED `evidence_terms` appear in the
bodies of the chapters up to `must_appear_by` (default 3). Three outcomes:
  delivered    — at least one evidence term appears in the window
  not_delivered— none appear, and the window has been fully produced
  uncheckable  — the promise declared no evidence terms, or the window has not
                 been produced yet

WHY AUTHORED TERMS (measured, not theorized):
The genre-drift detector tried stock per-genre vocabulary first. On the real
33-chapter baseline that scored 20 hits across ~177k chars and called 31/33
chapters genre-less, while the book's own coinages appeared ~1400 times. A book's
promise lives in ITS OWN words. So the author declares the terms; this module never
guesses at meaning and never claims semantic understanding.

HONEST LIMITATION:
Term presence is a PROXY for delivery. A chapter can name 梦晶 without doing
anything with it, and can honor a promise in words the author did not list. So a
finding points a human editor at a promise/chapter pair — it is not a verdict, and
`uncheckable` is reported as `info`, never as a failure.

DISCIPLINE:
  - DETERMINISTIC: substring counting over bodies. Same inputs => same findings.
  - EVALUATIVE, never gates (ADR-003). Reuses the ReviewReport shape
    (axis=evaluative, gating=False) like its detector siblings.
  - Reads only the draft bodies — no draft bytes change, so content_hash is
    untouched.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from ..execution.draft_review import ReviewReport, ReviewFinding
from .loader import packaging_promises

PACKAGING_REVIEWER_ID = "packaging-promise-delivery-v1"

# How many promise ids to name in one finding before summarizing.
MAX_LISTED_PROMISES = 4


def _window_bodies(bodies_by_chapter: Dict[int, str], upto: int) -> List[str]:
    """Bodies of chapters 1..upto that were actually produced (non-empty)."""
    return [bodies_by_chapter[n] for n in sorted(bodies_by_chapter)
            if n <= upto and (bodies_by_chapter.get(n) or "").strip()]


def _window_is_complete(bodies_by_chapter: Dict[int, str], upto: int) -> bool:
    """Whether every chapter in 1..upto has a produced body. A promise cannot be
    called undelivered while the window it was promised in is still being written."""
    return all((bodies_by_chapter.get(n) or "").strip() for n in range(1, upto + 1))


def check_promise_delivery(packaging: Optional[dict],
                           bodies_by_chapter: Optional[Dict[int, str]], *,
                           reviewer_id: str = PACKAGING_REVIEWER_ID) -> ReviewReport:
    """Check §3.3 packaging-promise delivery and return an ADVISORY report
    (ReviewReport: axis=evaluative, gating=False). Deterministic.

    `bodies_by_chapter` maps 1-based chapter number -> produced body. Absent
    packaging, absent promises, or an unproduced window all degrade to clean info
    notes; nothing here ever raises or blocks.
    """
    findings: List[ReviewFinding] = []
    promises = packaging_promises(packaging)
    bodies = {k: v for k, v in (bodies_by_chapter or {}).items()
              if isinstance(k, int) and not isinstance(k, bool)}

    if not packaging:
        findings.append(ReviewFinding(
            "packaging-promise", "info",
            "未撰写 sources/book-packaging.yaml，跳过包装承诺一致性检查"))
        return ReviewReport(reviewer=reviewer_id, findings=findings)

    if not promises:
        findings.append(ReviewFinding(
            "packaging-promise", "info",
            "包装未声明 promises，跳过承诺一致性检查"
            "（§3.3 要求包装承诺在前三章兑现，建议补上 promises 与 evidence_terms）"))
        return ReviewReport(reviewer=reviewer_id, findings=findings)

    if not bodies:
        findings.append(ReviewFinding(
            "packaging-promise", "info",
            f"尚无已产出章节，{len(promises)} 条包装承诺暂无法核对"))
        return ReviewReport(reviewer=reviewer_id, findings=findings)

    delivered: List[str] = []
    missing: List[dict] = []
    uncheckable: List[str] = []
    pending: List[str] = []

    for p in promises:
        pid, upto = p["promise_id"], p["must_appear_by"]
        terms = p["evidence_terms"]
        if not terms:
            uncheckable.append(pid)
            continue
        window = _window_bodies(bodies, upto)
        hit = any(t in body for body in window for t in terms)
        if hit:
            delivered.append(pid)
        elif _window_is_complete(bodies, upto):
            missing.append(p)
        else:
            pending.append(pid)

    # 1. The defect §3.3 exists to catch: a promise whose window closed unhonored.
    if missing:
        shown = "、".join(
            f"{p['promise_id']}（{p['statement'][:24]}，应在第 {p['must_appear_by']} 章前兑现）"
            for p in missing[:MAX_LISTED_PROMISES])
        more = f" 等 {len(missing)} 条" if len(missing) > MAX_LISTED_PROMISES else ""
        findings.append(ReviewFinding(
            "packaging-promise", "warning",
            f"包装承诺未在约定窗口内兑现：{shown}{more}。"
            f"正文未出现该承诺的任何证据词，读者会认为简介与正文不符——"
            f"这是点击进来后立刻流失的主要原因之一，建议改正文或改包装"))

    # 2. Promises the author left uncheckable. Info, not warning: an unlisted term
    #    is a gap in the packaging file, not evidence that the book failed.
    if uncheckable:
        shown = "、".join(uncheckable[:MAX_LISTED_PROMISES])
        more = f" 等 {len(uncheckable)} 条" if len(uncheckable) > MAX_LISTED_PROMISES else ""
        findings.append(ReviewFinding(
            "packaging-promise", "info",
            f"{shown}{more}未声明 evidence_terms，无法自动核对兑现情况"
            f"（本检查只数作者声明的证据词，不猜测语义）"))

    if pending:
        findings.append(ReviewFinding(
            "packaging-promise", "info",
            f"{len(pending)} 条承诺的兑现窗口尚未产出完，暂不判定"))

    if not missing:
        checked = len(delivered)
        if checked:
            findings.append(ReviewFinding(
                "packaging-promise", "info",
                f"{checked}/{len(promises)} 条包装承诺已在约定窗口内见到证据词"))
    return ReviewReport(reviewer=reviewer_id, findings=findings)
