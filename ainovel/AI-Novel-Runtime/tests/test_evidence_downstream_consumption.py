import pytest

from runtime.genesis.brain_gen import build_brain, write_brain
from runtime.long_arc.plan import build_long_arc_plan


def _outline(with_evidence=True):
    merged = {"genre_signals": ["玄幻"]}
    if with_evidence:
        merged["narrative_evidence"] = {
            "id": "NEP-TEST-GENESIS",
            "patterns": [{"pattern_type": "bounded-payoff", "effects": ["早期可见回报", "受限能力增长"]}],
            "anti_patterns": [{"pattern_type": "flat-growth", "risk": ["无代价升级"]}],
            "constraints": ["能力必须有代价"],
        }
    return {
        "id": "OUTLINE-TEST",
        "genre": ["玄幻"],
        "logline": "少年用受限能力改变处境。",
        "core_hook": "少年用受限能力改变处境。",
        "market_position": {"channel": "男频", "sub_genre": "玄幻", "reader_promise": "持续成长"},
        "reward_loop": {"reward_types": ["突破"], "cadence_chapters": 3},
        "originality_delta": [],
        "power_system": {"tiers": ["淬体", "灵动"]},
        "provenance": {"analysis_summary": merged},
    }


def test_brain_consumes_evidence_effects_risks_and_constraints():
    brain = build_brain(_outline())
    assert "早期可见回报" in brain["target_reader"]["wants"]
    assert "无代价升级" in brain["target_reader"]["avoids"]
    assert "语料证据约束：能力必须有代价" in brain["forbidden_style"]


def test_brain_without_evidence_is_backward_compatible_and_author_file_wins(tmp_path):
    brain = build_brain(_outline(with_evidence=False))
    assert all("语料证据约束" not in item for item in brain["forbidden_style"])
    existing = tmp_path / "sources" / "novel-brain.yaml"
    existing.parent.mkdir(parents=True)
    existing.write_text("human: authored\n", encoding="utf-8")
    with pytest.raises(FileExistsError):
        write_brain(tmp_path, brain)
    assert existing.read_text(encoding="utf-8") == "human: authored\n"


def test_long_arc_consumes_evidence_without_overwriting_authored_axes():
    plan = build_long_arc_plan(_outline()).to_dict()
    axes = {item["axis"]: item["bands"] for item in plan["progression_ladders"]}
    assert axes["power"] == ["淬体", "灵动"]
    assert axes["corpus_evidence"] == ["早期可见回报", "受限能力增长"]
    assert "能力必须有代价" in plan["constraints"]
    assert plan["provenance"]["derived_from"]["narrative_evidence_pack_id"] == "NEP-TEST-GENESIS"
