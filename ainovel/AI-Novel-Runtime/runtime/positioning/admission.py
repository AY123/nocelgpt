"""admission.py — the pre-book ADMISSION check (roadmap 4.5).

A DETERMINISTIC FOLD of three artifacts the project already holds — the authored
Market Position, the authored Novel Brain, and the derived Market Snapshot — into
an advisory recommendation (admit / revise / hold) on whether opening the book is
commercially sound. No new judgment model: every check is a deterministic read,
so the same inputs always yield the same verdict (fixture-validated, no live
model needed).

Two structural invariants, enforced here AND in market-admission.schema.json:
  - gating = False  -> NEVER blocks a build (ADR-003); it advises positioning.
  - authority = human -> opening/committing to a book is outward + hard to
    reverse (ADR-009), so the system recommends but a human commits.

Reads only; the writer (project_admission) persists under registry/derived/,
never under registry/facts/ (ADR-006).
"""
from __future__ import annotations

from typing import List, Optional

ADMISSION_VERSION = "1.0"

# The pre-book questions the positioning MUST answer. A missing one forces at
# least 'revise'; an entirely absent/empty positioning forces 'hold'.
_REQUIRED = (
    ("reader_segment", "primary"),
    ("trope_map", "leans_on"),
    ("commercial_promise", "pay_trigger"),
    ("commercial_promise", "first_30_hook"),
    ("commercial_promise", "sustainability_100"),
)


def _missing_answers(position: dict) -> List[str]:
    """Required positioning answers that are absent or empty. Deterministic."""
    missing: List[str] = []
    for block, key in _REQUIRED:
        val = (position.get(block) or {}).get(key)
        if val is None or (isinstance(val, (str, list, dict)) and len(val) == 0):
            missing.append(f"{block}.{key}")
    return missing


def _internal_basis(position: dict, brain: Optional[dict]) -> dict:
    """Deterministic Position/Brain agreement. When no Brain is authored the
    block degrades to brain_authored=False with no conflicts (nothing to disagree
    with) — never a false conflict."""
    block = {"brain_authored": brain is not None, "conflicts": []}
    if brain is None:
        return block

    conflicts: List[str] = []
    # channel agreement (only when both sides declare one)
    pos_channel = (position.get("channel") or "").strip()
    brain_channel = ((brain.get("genre") or {}).get("channel") or "").strip()
    if pos_channel and brain_channel:
        agrees = pos_channel == brain_channel
        block["channel_agrees"] = agrees
        if not agrees:
            conflicts.append(
                f"channel mismatch: position={pos_channel} vs brain={brain_channel}")

    # a Brain forbidden_style that the Position deliberately leans on is a real
    # contradiction (the commercial thesis relies on something the constitution
    # bans). Substring match both ways so '注水' matches '大量注水桥段'.
    forbidden = [str(f) for f in (brain.get("forbidden_style") or [])]
    leans = [str(t) for t in ((position.get("trope_map") or {}).get("leans_on") or [])]
    for f in forbidden:
        for t in leans:
            if f and t and (f in t or t in f):
                conflicts.append(f"trope '{t}' leaned on but brain forbids '{f}'")

    block["conflicts"] = conflicts
    return block


def _external_basis(position: dict, snapshot: Optional[dict]) -> dict:
    """Deterministic Position/Market-Snapshot agreement. Absent snapshot degrades
    to snapshot_present=False (advisory-only, never a conflict). A stale snapshot
    is surfaced but never gates."""
    block = {"snapshot_present": snapshot is not None,
             "alignments": [], "misalignments": []}
    if snapshot is None:
        return block

    block["snapshot_stale"] = bool(
        (snapshot.get("staleness") or {}).get("is_stale", False))

    pos_channel = (position.get("channel") or "").strip()
    channels = [c.get("channel") for c in (snapshot.get("channels") or [])]
    channel_in = pos_channel in channels if pos_channel else False
    block["channel_in_snapshot"] = channel_in

    alignments: List[str] = []
    misalignments: List[str] = []

    # trending-genre alignment: a leaned-on trope/genre that appears in the
    # snapshot's trending_genres is market-aligned.
    trending = [str(g) for g in
                ((snapshot.get("signals") or {}).get("trending_genres") or [])]
    leans = [str(t) for t in ((position.get("trope_map") or {}).get("leans_on") or [])]
    for t in leans:
        if any(t and g and (t in g or g in t) for g in trending):
            alignments.append(f"leaned-on '{t}' is trending in market")

    # drop-trigger informed by market common_drop_points
    common_drops = [str(d) for d in
                    ((snapshot.get("signals") or {}).get("common_drop_points") or [])]
    drop_trigs = [str(d) for d in
                  ((position.get("reader_segment") or {}).get("drop_triggers") or [])]
    for d in drop_trigs:
        if any(d and cd and (d in cd or cd in d) for cd in common_drops):
            alignments.append(f"drop_trigger '{d}' matches a market drop point")

    if pos_channel and not channel_in:
        misalignments.append(
            f"channel '{pos_channel}' has no signal in the market snapshot")

    block["alignments"] = alignments
    block["misalignments"] = misalignments
    return block


def _recommend(position: Optional[dict], completeness: dict,
               internal: dict, external: dict) -> tuple[str, str]:
    """Fold the three bases into a recommendation + rationale. Deterministic and
    monotone in severity: 'hold' > 'revise' > 'admit', and nothing may raise a
    recommendation above what completeness allows.

    - No positioning authored at all         -> hold (nothing to open on).
    - A required answer missing               -> revise (fixable gap).
    - An internal (Brain) conflict            -> revise (sharpen the thesis).
    - An external misalignment                -> revise (market says reconsider).
    - Everything present + consistent         -> admit.
    """
    if position is None:
        return "hold", "no market-position authored; nothing to admit — author sources/market-position.yaml first"

    reasons: List[str] = []
    rec = "admit"

    if completeness["missing"]:
        rec = "revise"
        reasons.append("missing positioning answers: " + ", ".join(completeness["missing"]))
    if internal["conflicts"]:
        rec = "revise"
        reasons.append("brain/position conflicts: " + "; ".join(internal["conflicts"]))
    if external.get("misalignments"):
        rec = "revise"
        reasons.append("market misalignments: " + "; ".join(external["misalignments"]))

    if rec == "admit":
        note = "positioning is complete and consistent"
        if external.get("snapshot_present"):
            aligns = external.get("alignments") or []
            note += (f"; {len(aligns)} market alignment(s)" if aligns
                     else "; no explicit market alignment (advisory)")
            if external.get("snapshot_stale"):
                note += "; NOTE market snapshot is stale (advisory)"
        else:
            note += "; no market snapshot (external checks advisory-only)"
        return "admit", note

    return rec, " | ".join(reasons)


def build_admission(position: Optional[dict], brain: Optional[dict],
                    snapshot: Optional[dict], *,
                    admission_id: str = "MADM-00001") -> dict:
    """Fold Position + Brain + Snapshot into a market-admission verdict dict that
    validates against market-admission.schema.json. Pure + deterministic; never
    gates (ADR-003); authority stays human (ADR-009)."""
    completeness = {
        "position_authored": position is not None,
        "missing": _missing_answers(position) if position else [],
    }
    internal = _internal_basis(position or {}, brain)
    external = _external_basis(position or {}, snapshot)
    recommendation, rationale = _recommend(position, completeness, internal, external)

    sources = {}
    if position and position.get("id"):
        sources["market_position_id"] = position["id"]
    if brain and brain.get("id"):
        sources["novel_brain_id"] = brain["id"]
    if snapshot and snapshot.get("id"):
        sources["market_snapshot_id"] = snapshot["id"]

    verdict = {
        "id": admission_id,
        "kind": "market_admission",
        "version": ADMISSION_VERSION,
        "authority": "human",   # structural invariant (ADR-009)
        "gating": False,        # structural invariant (ADR-003)
        "recommendation": recommendation,
        "basis": {"completeness": completeness, "internal": internal,
                  "external": external},
        "rationale": rationale,
    }
    if sources:
        verdict["sources"] = sources
    return verdict


def project_admission(project_path, *, standard_root=None) -> dict:
    """Load the project's authored Position + Brain and derived Market Snapshot,
    then fold them into an admission verdict. Reads only; never writes facts.
    Each source degrades gracefully when absent."""
    from .loader import load_position
    from ..brain import load_brain
    from ..market.writer import load_market_snapshot

    position = load_position(project_path)
    brain = load_brain(project_path)
    snapshot = load_market_snapshot(project_path)
    return build_admission(position, brain, snapshot)


def write_admission(project_path, verdict: dict) -> str:
    """Persist an admission verdict under registry/derived/market-admission/.
    A derived artifact (ADR-006), NEVER a fact. Returns the project-relative path."""
    import json
    from pathlib import Path

    project = Path(project_path)
    out_dir = project / "registry" / "derived" / "market-admission"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{verdict['id']}.json"
    path.write_text(json.dumps(verdict, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    return str(path.relative_to(project))
