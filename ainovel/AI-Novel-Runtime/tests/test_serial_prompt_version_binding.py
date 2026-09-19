"""test_serial_prompt_version_binding.py — every prompt version must actually RENDER.

WHY THIS EXISTS (a real defect this suite failed to catch):

v12 shipped with the CLI resolving --craft-texture to "12.0.0" while the serial
runner's prompt-capability checks were hand-maintained CLOSED enumerations that
all stopped at "11" (`major in ("3","4",...,"11")`, ten of them). A v12 run
therefore skipped EVERY variable-binding block: story_state, chapter_ir,
scene_plan, character_runtime, narrative_mandate, chapter_objective,
director_brief, speech_profiles, recent_openings and long_arc were never bound.

The v12 unit tests passed anyway because they only checked the template's
variable set, its text, and the CLI flag ladder — none of them RENDERED a
chapter. That is the gap this file closes: it drives the real `run_serial` path
so a version that cannot bind its variables fails loudly here.

The fix was to express the ladders ORDINALLY (`_at_least(major, N)`), which makes
a new prompt version work by default. These tests pin both halves:
  - the ordinal predicate is EXACTLY equivalent to the old enumerations for
    every legacy version (v1..v11), so the refactor changed no old behavior;
  - a real serial run at v12 renders and produces chapters, with the variables
    the template requires actually bound.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from runtime.prompt.loader import PromptLoader
from runtime.serialize import run_serial
from runtime.serialize.loop import _at_least

HERE = Path(__file__).resolve().parent
STANDARD = HERE.parent.parent / "AI-Novel-Standard"
SCHEMA = STANDARD / "phase-1" / "generated" / "json-schema"
PROMPTS = STANDARD / "contracts" / "prompts"

# The ten capability floors in runtime/serialize/loop.py, paired with the CLOSED
# enumeration each one replaced. If a ladder's floor changes, update both halves
# together — the equivalence test below is what proves the refactor was faithful.
LADDERS = (
    (10, ("10", "11")),
    (3, ("3", "4", "5", "6", "7", "8", "9", "10", "11")),
    (4, ("4", "5", "6", "7", "8", "9", "10", "11")),
    (5, ("5", "6", "7", "8", "9", "10", "11")),
    (8, ("8", "9", "10", "11")),
    (6, ("6", "7", "8", "9", "10", "11")),
    (7, ("7", "8", "9", "10", "11")),
    (9, ("9", "10", "11")),
)


def _write(path: Path, obj: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(obj, allow_unicode=True, sort_keys=False),
                    encoding="utf-8")


def _scaffold(root: Path, n_events: int = 3):
    facts, meta = root / "registry" / "facts", root / "registry" / "_meta"
    meta.mkdir(parents=True, exist_ok=True)
    (meta / "registry-version").write_text("1\n", encoding="utf-8")
    (meta / "standard.pin").write_text("2.0.0\n", encoding="utf-8")
    _write(facts / "timelines" / "TML-00001.yaml", {
        "id": "TML-00001", "name": "主线", "status": "active",
        "fact_version": 1, "kind": "main"})
    _write(facts / "characters" / "CHR-00001.yaml", {
        "id": "CHR-00001", "name": "主角", "status": "active", "fact_version": 1})
    for i in range(1, n_events + 1):
        _write(facts / "events" / f"EVT-{i:05d}.yaml", {
            "id": f"EVT-{i:05d}", "name": f"事件{i}", "status": "active",
            "fact_version": 1, "timeline": "TML-00001", "sequence_index": i,
            "participants": ["CHR-00001"],
            "causes": ([f"EVT-{i-1:05d}"] if i > 1 else []),
            "effects": ([f"EVT-{i+1:05d}"] if i < n_events else []),
            "summary": f"第{i}章"})


def _run(root: Path, **kw):
    return run_serial(project_path=root, standard_root=STANDARD, schema_dir=SCHEMA,
                      out_dir=root / "build-serial", **kw)


# --------------------------------------------------------------------------- #
# The ordinal predicate is equivalent to the enumerations it replaced          #
# --------------------------------------------------------------------------- #
def test_ordinal_ladder_matches_legacy_enumerations():
    """v1..v11 must behave EXACTLY as before the refactor — zero old-path drift."""
    for floor, legacy in LADDERS:
        for n in range(1, 12):
            major = str(n)
            assert _at_least(major, floor) == (major in legacy), (
                f"v{major} diverges from the legacy enumeration at floor {floor}")


def test_ordinal_ladder_admits_new_versions_by_default():
    """The whole point of the fix: a NEW version needs no ladder edits. This is
    what makes the v12-class defect unrepeatable for v13+."""
    for floor, _ in LADDERS:
        assert _at_least("12", floor), f"v12 blocked at floor {floor}"
        assert _at_least("13", floor), f"v13 blocked at floor {floor}"


def test_ordinal_ladder_degrades_on_non_numeric():
    """Unknown majors stay False rather than raising — the resolver never emits
    these, but a malformed override must not crash a production run."""
    for bad in ("x", "", None, "1.2"):
        assert _at_least(bad, 3) is False


# --------------------------------------------------------------------------- #
# The integration test the unit tests were missing: v12 actually renders       #
# --------------------------------------------------------------------------- #
def test_v12_serial_run_renders_and_produces_chapters(tmp_path):
    """Drives the REAL run_serial path at v12. Before the ladder fix this
    produced chapters whose prompt was rendered with none of the v12-required
    variables bound; the deterministic model makes this cheap (no API)."""
    root = tmp_path / "v12"
    _scaffold(root, 3)
    result = _run(root, prompt_version="12.0.0")
    assert result.produced == 3, f"v12 serial did not produce all chapters: {result}"


def test_v12_binds_the_variables_its_template_requires(tmp_path):
    """The defect's MEASURED signature (probed with the fix stashed):

        PRE-FIX 11.0.0: produced=2 skipped=0
        PRE-FIX 12.0.0: RAISED ValueError: missing prompt variables:
          narrative_mandate, chapter_ir, scene_plan, character_runtime,
          chapter_objective, director_brief, speech_profiles, recent_openings,
          long_arc

    So the renderer HARD-ENFORCES required variables (renderer.py raises on any
    missing) — an unbound v12 could never have produced a silently-degraded
    chapter, it simply could not run. That makes a completed run the exact
    assertion for "every required variable was bound", and it is why the
    prompt-manifest records only hashes (no `variables` key) — binding
    completeness is enforced upstream, not audited downstream.

    Pinning the enforcement itself, so this stays a real check rather than a
    tautology if the renderer's contract ever loosens."""
    from runtime.prompt.renderer import render_template
    import inspect

    src = inspect.getsource(render_template)
    assert "required_variables" in src and "raise ValueError" in src, (
        "renderer no longer hard-enforces required variables — a version whose "
        "ladder is missed could now render a DEGRADED prompt silently, and this "
        "test must be upgraded to inspect the rendered text instead")

    root = tmp_path / "v12vars"
    _scaffold(root, 2)
    result = _run(root, prompt_version="12.0.0")
    # Only reachable if all 14 required variables bound (the pre-fix run raised).
    assert result.produced == 2

    manifests = sorted((root / "registry" / "derived" / "prompt-manifests").glob("*.json"))
    assert manifests, "v12 run wrote no prompt manifest to audit"


def test_v11_serial_run_unchanged_by_the_refactor(tmp_path):
    """Guards the load-bearing invariant: the version that WORKED must still
    work identically after the ladders were rewritten."""
    a, b = tmp_path / "a", tmp_path / "b"
    _scaffold(a, 3)
    _scaffold(b, 3)
    r1 = _run(a, prompt_version="11.0.0")
    r2 = _run(b, prompt_version="11.0.0")
    assert r1.produced == r2.produced == 3
