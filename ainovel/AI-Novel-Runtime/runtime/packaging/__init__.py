"""Book packaging subdomain (规范 §3) — the FRONT of the commercial funnel.

The funnel is 点击 × 前三章留存 × 免费追读 × 付费转化 × 长期稳定. This project built
~30 modules for the last two terms and the prose texture, and had nothing for the
first two. `golden_three_contract` closed 前三章留存 on the generation side; this
package closes 点击 and the 承诺一致性 link between packaging and the opening chapters.

Two pieces, deliberately split by what can be known deterministically:

  loader.py  — the AUTHORED packaging (title / one-line pitch / blurb / tags /
               declared promises) at sources/book-packaging.yaml. Read-only here;
               never a fact (ADR-006), never a projection (ADR-008).
  delivery.py— the deterministic §3.3 check: are the packaging's promises actually
               honored by the chapters that were produced, within the window the
               author declared (default: the 黄金三章 window)?

DISCIPLINE:
  - EVALUATIVE, never gates (ADR-003). A packaging inconsistency is a signal for a
    human editor; it never blocks a build, a chapter, or a publish.
  - AUTHORITY = human (ADR-009). What a book ships under is an outward,
    hard-to-reverse commitment; the system drafts and checks, a human authorizes.
  - The delivery check reads AUTHORED evidence_terms rather than inferring meaning
    from blurb prose. Same lesson the genre-drift detector learned the hard way: a
    stock term list scored 20 hits in 177k chars of a real book and called 31/33
    chapters empty, because a book's promise lives in ITS OWN vocabulary.
"""

from .loader import (packaging_path, load_packaging, validate_packaging,
                     packaging_promises)
from .delivery import check_promise_delivery, PACKAGING_REVIEWER_ID

__all__ = ["packaging_path", "load_packaging", "validate_packaging",
           "packaging_promises", "check_promise_delivery",
           "PACKAGING_REVIEWER_ID"]
