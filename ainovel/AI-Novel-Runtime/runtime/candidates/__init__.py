"""candidates/ — the Fact Candidate Pipeline (roadmap Phase 5).

The PREPARATION half of prose→fact evolution: extract candidate facts from a
produced ChapterDraft, reconcile each against the current Registry, and stage a
plan for human review. It stops at the ADR-009 boundary — it NEVER writes
registry/facts/ and never mints. Minting (writing facts + bumping fact_version)
and the derived recompute it triggers are separate, human-authorized workflows.

  extract.py    — extraction seam (deterministic stub + LLM drop-in)
  reconcile.py  — DETERMINISTIC 5-class reconciliation (the anti-rot core)
  plan.py       — stage the reconciled candidates as a derived artifact
"""
