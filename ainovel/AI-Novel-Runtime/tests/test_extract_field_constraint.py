"""test_extract_field_constraint.py — W12 extractor schema-field constraint.

Pins the layer that stops the LLM inventing near-miss field names (the dominant
un-mintable cause CLOSE-15 found): the prompt carries each type's declared slots,
and the extractor coerces a near-miss onto a real slot (singular/plural, case,
y→ies) or drops a field with no declared match — an invented field never reaches
reconcile/mint. Schema-driven + deterministic.
"""
from __future__ import annotations

from pathlib import Path

from runtime.candidates.extract import (
    declared_fields_by_type, build_extract_prompt, _coerce_field, LLMExtractor,
)

STANDARD = Path(__file__).resolve().parent.parent.parent / "AI-Novel-Standard"
SCHEMA_DIR = STANDARD / "phase-1" / "generated" / "json-schema"


def test_declared_fields_read_real_slots_and_exclude_meta():
    df = declared_fields_by_type(SCHEMA_DIR)
    chr_fields = df["Character"]
    assert "possessions" in chr_fields and "abilities" in chr_fields
    # structural/meta fields prose never asserts are excluded
    assert "id" not in chr_fields and "fact_version" not in chr_fields
    assert "statement" in df["WorldRule"]  # not "rule"
    assert "summary" in df["Event"]        # not "description"


def test_prompt_carries_declared_field_block():
    df = declared_fields_by_type(SCHEMA_DIR)
    draft = {"body": "正文", "provenance": {"derived_from": []}}
    prompt = build_extract_prompt(draft, [], df)
    assert "- Character：" in prompt
    assert "possessions" in prompt
    # without declared fields the block degrades, backward-compatible
    bare = build_extract_prompt(draft, [])
    assert "未提供字段约束" in bare


def test_coerce_field_maps_near_miss_or_drops():
    allowed = ["abilities", "possessions", "physical_facts", "status", "name"]
    assert _coerce_field("possession", allowed) == "possessions"   # plural
    assert _coerce_field("ability", allowed) == "abilities"         # y→ies
    assert _coerce_field("abilities", allowed) == "abilities"       # exact
    assert _coerce_field("Possessions", allowed) == "possessions"   # case
    # dotted leaf preserved when the object prefix is declared
    assert _coerce_field("physical_facts.eye_color", allowed) == "physical_facts.eye_color"
    # a truly invented field has no declared match → dropped
    assert _coerce_field("family", allowed) is None


class _FakeModel:
    """Returns a fixed candidate JSON, exercising the extractor's coerce/drop."""
    model_id = "fake"

    def __init__(self, payload):
        self._payload = payload

    def generate(self, prompt):
        class _Out:
            text = self._payload
        return _Out()


def test_extractor_coerces_and_drops_against_declared_fields():
    df = declared_fields_by_type(SCHEMA_DIR)
    payload = (
        '{"candidates": ['
        '{"target_type": "Character", "field": "possession", "value": "钥匙",'
        ' "matched_entity_id": "CHR-00001", "evidence": "e", "confidence": 1},'
        '{"target_type": "Character", "field": "family", "value": "妹妹",'
        ' "matched_entity_id": "CHR-00001", "evidence": "e", "confidence": 1}'
        ']}'
    )
    draft = {"body": "正文", "provenance": {"derived_from": []}}
    cands = LLMExtractor(_FakeModel(payload)).extract(
        draft, known_entities=[], declared_fields=df)
    fields = [c.field for c in cands]
    assert "possessions" in fields   # possession corrected onto the real slot
    assert "family" not in fields    # invented field dropped, never reaches mint
    assert len(cands) == 1
