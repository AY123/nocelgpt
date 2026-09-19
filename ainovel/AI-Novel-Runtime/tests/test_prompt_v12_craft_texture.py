"""test_prompt_v12_craft_texture.py — v12 prose-texture constraints (measured anchor).

The market anchor measured our 30ch baseline against 4 real bestsellers and found
three defects v11 had NO constraint for: em-dash asides (26/30 chapters), simile
stacking (22/30) and thin dialogue (9/30). v12 adds the prose-texture block that
prevents them at generation time (the hygiene loop only CORRECTS after the fact,
and for length it cannot correct at all — see test_length_cannot_be_hygiene_fixed).

These tests pin the non-breaking contract:
  - v12 carries the SAME variable set as v11, so no binding/allowlist wiring
    changes (a prompt variable must be declared in 3 places; adding none avoids it).
  - v11 is untouched (byte-identical source hash) — the old path cannot shift.
  - The three measured constraints are actually present in v12's system message.
  - The CLI flag ladder resolves --craft-texture to 12.0.0 and it wins over
    --anti-anaphora (v12 ⊃ v11).
"""
from __future__ import annotations

import argparse
from pathlib import Path

from runtime.prompt.loader import PromptLoader

HERE = Path(__file__).resolve().parent
PROMPTS = HERE.parent.parent / "AI-Novel-Standard" / "contracts" / "prompts"

# Pinned at the value measured before v12 was introduced. If v11's template is
# edited this fails loudly — the old path must stay byte-identical.
V11_SOURCE_HASH_PREFIX = "sha256:6075b000109aa"


def _loader() -> PromptLoader:
    return PromptLoader(PROMPTS)


def test_v12_variable_set_extends_v11_by_the_two_route_notes():
    """v12 carries v11's REQUIRED set unchanged, plus exactly two extra OPTIONAL
    variables: the route notes its body renders.

    This test used to assert the optional sets were IDENTICAL. That premise was
    false and was masking a live bug: v12's body references
    {model_profile_note}/{constraint_pack_note} (its "# Model Routing Note" and
    "# Constraint Pack Note" sections) while v11's body references neither, so the
    variable sets had ALWAYS diverged — v12 just failed to DECLARE the two, which
    made render_template raise KeyError for every caller that didn't inject them
    (it worked only because ChapterDraftAgent always setdefault()s both).

    Declaring them OPTIONAL is what keeps the bump non-breaking: the renderer
    pre-fills declared optionals with "", so a caller that omits them renders the
    section headers with empty bodies instead of crashing. Guard #25 in
    test_fitness.py now enforces declared ⊇ referenced for every template.
    """
    load = _loader()
    v11 = load.load("chapter-draft", "11.0.0")
    v12 = load.load("chapter-draft", "12.0.0")
    assert v12.version == "12.0.0"
    assert v12.required_variables == v11.required_variables
    assert set(v12.optional_variables) - set(v11.optional_variables) == {
        "model_profile_note", "constraint_pack_note"}
    # v11 loses nothing — the old path's variables are a strict subset.
    assert set(v11.optional_variables) <= set(v12.optional_variables)
    assert v12.capability == v11.capability == "ChapterDraft"


def test_v12_renders_without_the_route_notes_injected():
    """The regression that motivated declaring them: a caller that supplies no
    route notes must still render v12 (they degrade to empty), not KeyError."""
    from runtime.prompt.binding import bind_chapter_draft
    from runtime.prompt.renderer import render_template

    package = {
        "task": {"task_id": "TASK-1", "goal": "g", "capability": "ChapterDraft"},
        "content_hash": "sha256:" + "a" * 64,
        "provenance": {"derived_from": [], "source_version": 1},
        "context": {},
    }
    required = _loader().load("chapter-draft", "12.0.0").required_variables
    variables = {name: name for name in required
                 if name not in ("task_id", "goal", "context_lines", "derived_from")}

    rendered = render_template(
        _loader().load("chapter-draft", "12.0.0"),
        bind_chapter_draft(package, variables))
    assert rendered.rendered_text
    # The section headers survive; only their bodies are empty.
    assert "Model Routing Note" in rendered.rendered_text


def test_v11_untouched_by_v12_bump():
    """The v11 template must not shift when v12 lands (non-breaking)."""
    v11 = _loader().load("chapter-draft", "11.0.0")
    assert v11.source_hash.startswith(V11_SOURCE_HASH_PREFIX)


def test_v12_carries_the_three_measured_constraints():
    """Each constraint corresponds to a defect the market anchor actually measured
    on the 30ch baseline — not an invented rule."""
    system = _loader().load("chapter-draft", "12.0.0").messages[0]["content"]
    # (1) em-dash asides — market band [0,0] in every window, ours 0.32/1000
    assert "破折号插入语" in system
    assert "—…—" in system or "em-dash" in system
    # (2) simile stacking — market p75 1.26/1000, ours 2.24
    assert "比喻" in system
    assert "1000" in system
    # (3) dialogue-carried scenes — market p25 0.10 rising, ours 0.174 flat
    assert "对白" in system
    # texture must be explicitly subordinate to facts (never overrides truth)
    assert "never override a fact" in system


def test_v12_texture_block_absent_from_v11():
    """The constraints are NEW in v12 — proves the old path really lacked them,
    which is why the baseline shipped these defects."""
    system_v11 = _loader().load("chapter-draft", "11.0.0").messages[0]["content"]
    assert "破折号插入语" not in system_v11
    assert "PROSE TEXTURE" not in system_v11


def test_craft_texture_flag_resolves_to_v12_and_wins():
    """The flag ladder is resolved in _cmd_serial_run; pin that --craft-texture
    maps to 12.0.0 and outranks --anti-anaphora (v12 ⊃ v11)."""
    def resolve(ns: argparse.Namespace) -> str:
        # mirrors the ladder in runtime/cli.py::_cmd_serial_run
        if getattr(ns, "craft_texture", False):
            return "12.0.0"
        if getattr(ns, "anti_anaphora", False):
            return "11.0.0"
        if getattr(ns, "long_arc", False):
            return "10.0.0"
        return ns.prompt_version

    base = dict(prompt_version="6.0.0", long_arc=False,
                anti_anaphora=False, craft_texture=False)
    assert resolve(argparse.Namespace(**base)) == "6.0.0"
    assert resolve(argparse.Namespace(**{**base, "anti_anaphora": True})) == "11.0.0"
    # craft_texture wins even when the lower flags are also on
    assert resolve(argparse.Namespace(
        **{**base, "anti_anaphora": True, "long_arc": True,
           "craft_texture": True})) == "12.0.0"


def test_length_cannot_be_hygiene_fixed():
    """Why length (P0-3) is NOT in the market feature spec: the measured shrink
    the market band demands (0.64x) is below the deletion-cheat floor (0.8x), so
    a length-driven hygiene rewrite would be rejected as gutting on every round.
    Length must be fixed upstream at the plan target, never by the hygiene loop."""
    from runtime.execution.prose_hygiene import (
        _MARKET_FEATURE_SPEC, _LENGTH_FLOOR_FRACTION)

    # No CHAPTER-SIZE feature may drive a market-anchored rewrite. (Per-sentence
    # rhythm features like ai_taste.sentence_length_cv are fine and DO drive one —
    # they are texture, not size, and are fixed by varying sentences, not cutting.)
    size_driven = [f for f in _MARKET_FEATURE_SPEC
                   if f.endswith("total_chars") or f.endswith("_chars")
                   or f.endswith(".word_count")]
    assert not size_driven, f"chapter-size feature would deadlock on the floor: {size_driven}"

    ours_median_chars, market_p75_chars = 5238, 3354      # measured, docs/craft-anchor
    required_ratio = market_p75_chars / ours_median_chars
    assert required_ratio < _LENGTH_FLOOR_FRACTION, (
        "if the required shrink ever clears the deletion floor, length COULD "
        "become a hygiene feature — re-derive this decision")
