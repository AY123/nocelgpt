"""test_prompt_v14_genre_contract.py — v14 genre-drift PREVENTION.

The prevention half of the loop whose detection half is
scene/serial_genre_drift.check_serial_genre_drift. v14 adds one variable
(genre_contract) carrying the discriminant requirement the declared genre cannot
lose, its degradation symptoms, and the book's own coined terms.

This bump is intentionally narrow:
  - v13 stays unchanged and remains the old path (byte-identical binding).
  - v14 adds ONLY the genre_contract variable + its instruction.
  - the runtime wiring must render the real prompt end-to-end.
  - a prompt variable must be registered in all THREE places (template yaml /
    binding.py / the serial feed) — a past bug shipped one of the three.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from runtime.prompt.loader import PromptLoader
from runtime.prompt.binding import bind_chapter_draft
from runtime.prompt.renderer import render_template
from runtime.genre_taxonomy import (contract_for_genre, render_genre_contract)

HERE = Path(__file__).resolve().parent
PROMPTS = HERE.parent.parent / "AI-Novel-Standard" / "contracts" / "prompts"


def _package() -> dict:
    return {
        "task": {"task_id": "TASK-1", "goal": "推进剧情", "capability": "ChapterDraft"},
        "content_hash": "sha256:" + "a" * 64,
        "provenance": {"derived_from": ["OUTLINE-0001"], "source_version": 1},
        "context": {"characters": [{"id": "CHR-00001", "name": "主角", "summary": ""}]},
    }


def _base_extra() -> dict:
    """Every v13 variable, so v14 differs by exactly one."""
    return dict(
        story_state="前情", narrative_mandate="强制令", chapter_ir="IR",
        scene_plan="分镜", character_runtime="运行时", chapter_objective="目标",
        director_brief="简报", speech_profiles="语言", recent_openings="开篇",
        long_arc="长弧", model_profile_note="", constraint_pack_note="",
        approved_state="", style="中文",
    )


# --------------------------------------------------------------------------- #
# The template bump is exactly one variable wide                               #
# --------------------------------------------------------------------------- #
def test_v14_adds_only_the_genre_contract_variable():
    loader = PromptLoader(PROMPTS)
    v13 = loader.load("chapter-draft", "13.0.0")
    v14 = loader.load("chapter-draft", "14.0.0")

    assert v14.version == "14.0.0"
    assert set(v14.required_variables) - set(v13.required_variables) == {"genre_contract"}
    assert set(v13.required_variables) - set(v14.required_variables) == set()
    assert v14.optional_variables == v13.optional_variables


def test_v13_does_not_carry_the_genre_instruction():
    """v13 must be untouched — the old path stays the old path."""
    loader = PromptLoader(PROMPTS)
    system_v13 = loader.load("chapter-draft", "13.0.0").messages[0]["content"]
    assert "GENRE CONTRACT" not in system_v13
    assert "genre_contract" not in " ".join(
        m["content"] for m in loader.load("chapter-draft", "13.0.0").messages)


def test_v14_system_message_states_the_drift_mechanism():
    """The instruction must explain WHY (the degradation gradient), not just what —
    a bare 'follow the genre' line is what the model already fails to do."""
    loader = PromptLoader(PROMPTS)
    system = loader.load("chapter-draft", "14.0.0").messages[0]["content"]
    assert "GENRE CONTRACT" in system
    # names the gradient and its endpoint
    assert "东方玄幻" in system and "升级爽文" in system
    # says the slide is locally invisible — the reason a per-chapter constraint
    # is needed at all rather than a one-off outline note
    assert "INVISIBLE" in system or "invisible" in system
    # keeps the ADR-shaped precedence: never overrides facts/mandate/objective
    assert "never overrides a fact" in system


def test_v14_user_message_has_the_slot():
    loader = PromptLoader(PROMPTS)
    user = loader.load("chapter-draft", "14.0.0").messages[1]["content"]
    assert "{genre_contract}" in user
    assert "题材契约" in user


# --------------------------------------------------------------------------- #
# Binding — place 2 of 3                                                       #
# --------------------------------------------------------------------------- #
def test_binding_registers_genre_contract_when_supplied():
    b = bind_chapter_draft(_package(), dict(_base_extra(), genre_contract="契约"))
    assert "genre_contract" in b.variables
    assert b.variables["genre_contract"].value == "契约"


def test_binding_omits_genre_contract_when_absent_keeping_v13_byte_identical():
    """The non-breaking discipline every prior bump followed: absent => not bound,
    so a v13 render's binding payload is unchanged by this variable existing."""
    without = bind_chapter_draft(_package(), _base_extra())
    with_gc = bind_chapter_draft(_package(), dict(_base_extra(), genre_contract="契约"))
    assert "genre_contract" not in without.variables
    assert set(with_gc.variables) - set(without.variables) == {"genre_contract"}
    # The v13 payload itself must be identical, not merely key-compatible.
    assert without.hash_payload() == bind_chapter_draft(
        _package(), _base_extra()).hash_payload()


# --------------------------------------------------------------------------- #
# End-to-end render                                                            #
# --------------------------------------------------------------------------- #
def test_v14_renders_end_to_end_with_the_contract_inline():
    loader = PromptLoader(PROMPTS)
    contract = render_genre_contract("高武世界", authored_markers=["梦墟"])
    rendered = render_template(
        loader.load("chapter-draft", "14.0.0"),
        bind_chapter_draft(_package(), dict(_base_extra(), genre_contract=contract)))
    text = rendered.rendered_text
    assert "段位即社会货币" in text          # the discriminant requirement
    assert "退化成东方玄幻换皮" in text        # a degradation symptom
    assert "梦墟" in text                    # the book's own coined term
    assert "{genre_contract}" not in text    # actually substituted


def test_v13_and_v14_renders_differ_only_by_the_contract():
    loader = PromptLoader(PROMPTS)
    r13 = render_template(loader.load("chapter-draft", "13.0.0"),
                          bind_chapter_draft(_package(), _base_extra()))
    r14 = render_template(
        loader.load("chapter-draft", "14.0.0"),
        bind_chapter_draft(_package(), dict(_base_extra(), genre_contract="X")))
    assert r13.rendered_hash != r14.rendered_hash
    assert r13.binding_hash != r14.binding_hash
    # v13's own hash must be reproducible — proof it was not perturbed.
    again = render_template(loader.load("chapter-draft", "13.0.0"),
                            bind_chapter_draft(_package(), _base_extra()))
    assert again.rendered_hash == r13.rendered_hash


# --------------------------------------------------------------------------- #
# The rendered contract itself                                                 #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("genre", ["东方玄幻", "异世大陆", "王朝争霸", "高武世界",
                                    "都市生活", "都市异能", "异术超能", "青春校园",
                                    "娱乐明星", "商战职场",
                                    "玄幻", "仙侠", "武侠", "奇幻", "都市",
                                    "历史", "游戏", "科幻", "诸天无限"])
def test_every_documented_genre_has_a_contract(genre):
    c = contract_for_genre(genre)
    assert c.get("must"), f"{genre} must state a discriminant requirement"
    assert c.get("forbid"), f"{genre} must list degradation symptoms"
    rendered = render_genre_contract(genre)
    assert genre in rendered and c["must"][:8] in rendered


def test_contract_names_coined_terms_so_it_targets_the_measured_signal():
    """The detector counts the book's coined terms, so the prevention side must
    name those same terms — otherwise the two halves measure different things."""
    rendered = render_genre_contract("玄幻", authored_markers=["梦墟", "梦晶"])
    assert "梦墟" in rendered and "梦晶" in rendered


def test_unknown_genre_degrades_to_a_stable_sentinel():
    """A bound slot must never be empty, or the template renders a hole."""
    out = render_genre_contract("没听过的类型XYZ")
    assert out.strip()
    assert "不受额外约束" in out


def test_unknown_genre_still_carries_coined_terms():
    out = render_genre_contract(None, authored_markers=["梦墟"])
    assert "梦墟" in out


@pytest.mark.parametrize("junk", [None, "", "   "])
def test_blank_genre_never_raises(junk):
    assert render_genre_contract(junk).strip()


def test_whitespace_only_markers_are_dropped():
    out = render_genre_contract("玄幻", authored_markers=["  ", ""])
    assert "「」" not in out and "「  」" not in out


# --------------------------------------------------------------------------- #
# Place 3 of 3 — the serial feed, and the CLI flag that reaches it             #
# --------------------------------------------------------------------------- #
def test_serial_actually_feeds_the_contract_into_generation(tmp_path):
    """BUILT != LIVE, proven by a real run rather than a source grep.

    A variable registered in the template and binding but never fed by the serial
    renders a sentinel forever — this repo has shipped that defect 7+ times. Drive
    the real run_serial at v14 and assert the genre's discriminant requirement
    reached the persisted prompt/run artifacts.
    """
    from tests.test_serial import _scaffold_project, _run, _write_outline
    from runtime.outline.writer import load_project_outline

    _scaffold_project(tmp_path, n_events=3)
    _write_outline(tmp_path, [
        {"chapter_no": i, "goal": f"第{i}章目标", "reward_if_any": "实力突破"}
        for i in (1, 2, 3)])
    outline = load_project_outline(tmp_path)
    outline["genre"] = ["高武世界"]

    result = _run(tmp_path, outline=outline, prompt_version="14.0.0")
    assert result.produced == 3 and all(c.ok for c in result.chapters)

    # 高武世界's discriminant requirement must appear in the persisted artifacts —
    # i.e. it really was rendered into the prompt, not merely bindable.
    carriers = [p for p in tmp_path.rglob("*.json")
                if "段位即社会货币" in p.read_text(encoding="utf-8")]
    assert carriers, "the genre contract never reached any persisted artifact"


def test_serial_does_not_feed_the_contract_below_v14(tmp_path):
    """The version gate must hold: a v13 run stays a v13 run."""
    from tests.test_serial import _scaffold_project, _run, _write_outline
    from runtime.outline.writer import load_project_outline

    _scaffold_project(tmp_path, n_events=2)
    _write_outline(tmp_path, [{"chapter_no": i, "goal": f"第{i}章"} for i in (1, 2)])
    outline = load_project_outline(tmp_path)
    outline["genre"] = ["高武世界"]

    _run(tmp_path, outline=outline, prompt_version="13.0.0")
    leaked = [p for p in tmp_path.rglob("*.json")
              if "段位即社会货币" in p.read_text(encoding="utf-8")]
    assert not leaked, "v13 must not carry the v14 contract"


def test_cli_exposes_the_v14_flag():
    src = (HERE.parent / "runtime" / "cli.py").read_text(encoding="utf-8")
    assert "--genre-contract" in src
    assert '"14.0.0"' in src


def test_cli_version_precedence_is_monotone():
    """v14 ⊃ v13: the new flag must win, or --genre-contract silently renders v13."""
    src = (HERE.parent / "runtime" / "cli.py").read_text(encoding="utf-8")
    gc = src.index('genre_contract", False')
    mr = src.index('meta_reference", False')
    assert gc < mr, "the v14 branch must be checked before the v13 branch"
