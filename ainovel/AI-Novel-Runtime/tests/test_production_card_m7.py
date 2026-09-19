"""test_production_card_m7.py — M7 vs the Production Card's read-side contract.

These tests pin the ARCHITECTURAL boundary the M8-01 cleanup restored:

  - The Production Card is a PURE read-side fold (production-card.schema.json,
    additionalProperties:false). It CITES the envelope's publish_readiness and
    NEVER recomputes M7. A chapter with no readiness on its envelope degrades to
    recommendation='unknown' — it must NOT be silently upgraded to 'recommend' by
    re-running the similarity check inside the card.
  - The card carries NO top-level `m7` field, and publish_readiness carries no
    nested `m7` — both frozen schemas forbid it (additionalProperties:false).
  - The raw M7 assessment is auditable, but it rides the DRAFT ENVELOPE as its own
    sibling `m7` (written by execution.run / serialize.loop), not the card.
"""
from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from runtime.publishing.card import build_production_card

STANDARD = Path(__file__).resolve().parent.parent.parent / "AI-Novel-Standard"
_CARD_SCHEMA = json.loads(
    (STANDARD / "contracts" / "production-card.schema.json").read_text(encoding="utf-8"))


def _scaffold_draft(tmp_path, task_id="TASK-00001",
                    body="少年推开门，雨夜里追查真相。", *, m7=None, publish=None):
    """Write a draft envelope + index entry. Optionally attach an M7 sibling block
    and/or a publish_readiness block, mirroring how run.py persists them."""
    drafts = tmp_path / "registry" / "derived" / "drafts"
    drafts.mkdir(parents=True, exist_ok=True)
    inner = {
        "artifact_format": "anes.v2", "kind": "prose", "capability": "ChapterDraft",
        "task_id": task_id,
        "content_hash": "sha256:" + "1" * 64,
        "body": body,
    }
    env = {"envelope_format": "runtime-draft/1.0", "draft": inner}
    if m7 is not None:
        env["m7"] = m7            # M7 rides the envelope as its own sibling
    if publish is not None:
        env["publish_readiness"] = publish
    rel = f"registry/derived/drafts/{task_id}.json"
    (tmp_path / rel).write_text(json.dumps(env, ensure_ascii=False), encoding="utf-8")
    index = {"artifacts": [{"id": task_id, "category": "drafts", "path": rel}]}
    meta = tmp_path / "registry" / "derived"
    meta.mkdir(parents=True, exist_ok=True)
    (meta / "_index.yaml").write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
    return tmp_path


def test_card_does_not_recompute_m7_and_degrades_to_unknown(tmp_path):
    # An envelope with NO publish_readiness (even though it carries a body a
    # similarity check could score) must degrade to 'unknown' — the card never
    # re-runs M7 to manufacture a recommendation.
    _scaffold_draft(tmp_path)
    card = build_production_card(tmp_path, "TASK-00001")
    assert card["publish_readiness"]["recommendation"] == "unknown"
    assert "publish-unknown" in card["flags"]


def test_card_carries_no_m7_field_and_validates(tmp_path):
    # The frozen production-card schema forbids a top-level `m7` (and a nested one
    # inside publish_readiness). The card must validate cleanly.
    _scaffold_draft(tmp_path, m7={"risk_level": "L3", "recommendation": "block",
                                  "redline_passed": True})
    card = build_production_card(tmp_path, "TASK-00001")
    assert "m7" not in card
    assert "m7" not in card["publish_readiness"]
    assert list(Draft202012Validator(_CARD_SCHEMA).iter_errors(card)) == []


def test_m7_detail_rides_the_envelope_sibling(tmp_path):
    # The legitimate audit intent: the raw M7 assessment is preserved — on the
    # draft envelope, where run.py/loop.py write it, not on the card.
    m7 = {"risk_level": "L3", "recommendation": "block", "redline_passed": True}
    _scaffold_draft(tmp_path, m7=m7)
    rel = tmp_path / "registry" / "derived" / "drafts" / "TASK-00001.json"
    env = json.loads(rel.read_text(encoding="utf-8"))
    assert env["m7"]["risk_level"] == "L3"
    assert env["m7"]["recommendation"] == "block"
