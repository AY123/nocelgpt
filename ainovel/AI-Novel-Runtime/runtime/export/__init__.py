"""Export subdomain (ANES v2, roadmap P20 — SOP stages 15/16).

Turns the pipeline's products into human-facing deliverables:

  - Book export (stage 15): fold ordered chapter drafts into one manuscript,
    rendered to markdown / plain text.
  - IP bible (stage 16): fold the Story State projection (characters, timeline,
    relationships, items, world) into a reference bible for adaptation.

DISCIPLINE:
  - PURE read-side: every exporter is a fold over products that already exist
    (draft index + envelopes, or StoryState). It writes deliverables under
    workspace/exports/, never into registry/ and never a fact (ADR-006).
  - Never gates (ADR-003).
  - ADR-009 (Human Authority Boundary): exporting to a local file is PREPARATION
    / staging, not the outward publish transition. The exporter never pushes to a
    platform and never writes the published log. Book export DEFAULTS to
    scope="published" — only chapters a human already authorized in the published
    log — so the natural output honors the authorization boundary; scope="produced"
    (all drafts, author's working copy) is an explicit opt-in.
  - assemble_* (fold to a model) is separated from render_* (model to bytes), so
    a new format (epub/docx) is just a new renderer over the same model — no
    rework of the fold.
"""
from .book import assemble_book, render_markdown, render_txt, BookModel
from .ipbible import assemble_ip_bible, render_ip_markdown, IPBible

__all__ = [
    "assemble_book", "render_markdown", "render_txt", "BookModel",
    "assemble_ip_bible", "render_ip_markdown", "IPBible",
]
