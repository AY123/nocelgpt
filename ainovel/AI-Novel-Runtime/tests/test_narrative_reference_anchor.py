from runtime.narrative import project_narrative_state


class _Reg:
    version = 1
    facts = {}


def test_narrative_state_includes_reference_anchor(tmp_path):
    project = tmp_path
    (project / "registry" / "derived").mkdir(parents=True)
    ref_dir = project / "registry" / "derived" / "reference-abstract"
    ref_dir.mkdir(parents=True, exist_ok=True)
    (ref_dir / "REFABSTRACT-001.json").write_text(
        """
{
  "id": "REFABSTRACT-001",
  "kind": "reference_lm_abstraction",
  "schema_version": "1.0",
  "source_ids": ["REF-00001"],
  "market_positioning": {
    "genre": "玄幻/仙侠",
    "reader_target": "中文商业网文核心读者",
    "core_promise": "强钩子开局",
    "commercial_thesis": "开篇强钩子"
  },
  "structural_patterns": {"opening": "强钩子开局"},
  "character_patterns": {"protagonist": "目标驱动", "supporting": "功能配角", "relationship": "关系张力"},
  "world_patterns": {"rules": "边界", "progression": "升级", "constraints": "成本"},
  "commercial_cadence": {"opening": "开局", "mid_arc": "每个小周期均有显性回报", "chapter_end": "留钩子", "long_run": "百章可持续"},
  "transferable_abstractions": ["反差开局"],
  "prohibited_specifics": ["具体人物名"],
  "evidence_spans": []
}
""",
        encoding="utf-8",
    )

    state = project_narrative_state(_Reg(), project)
    assert state.reference_anchor["id"] == "REFABSTRACT-001"
    assert state.reference_anchor["market_positioning"]["core_promise"] == "强钩子开局"
