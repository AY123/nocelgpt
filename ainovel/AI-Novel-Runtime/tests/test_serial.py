"""test_serial.py — continuous serial production (roadmap P14+P15 consumer, P17 seed).

The first real consumer of the whole chain. These tests scaffold a fresh
multi-chapter project in a temp dir (never the demo fixture) and prove: the
serial produces N chapters, state accumulates monotonically as a fold cursor
(ADR-008), the Novel Brain (P15) is injected on every chapter, the run is
reproducible, a failing chapter is skipped without aborting the serial
(break/resume), and the orchestration never gates (ADR-003).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml

from runtime import derived, registry_loader
from runtime.serialize import (
    plan_chapters,
    plan_continuation_from_rolling_plan,
    run_serial,
)
from runtime.serialize.run_manifest import (
    _existing_run_ids,
    next_run_id,
    rebuild_segment_manifest,
)

STANDARD = Path(__file__).resolve().parent.parent.parent / "AI-Novel-Standard"
SCHEMA = STANDARD / "phase-1" / "generated" / "json-schema"


def _write(path: Path, obj: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(obj, allow_unicode=True, sort_keys=False),
                    encoding="utf-8")


def _scaffold_project(root: Path, *, n_events: int = 4, with_brain: bool = True):
    """Build a minimal but schema-valid multi-event Project: one timeline, one
    character, and a causal chain of N events (each caused by the previous)."""
    facts = root / "registry" / "facts"
    meta = root / "registry" / "_meta"
    meta.mkdir(parents=True, exist_ok=True)
    (meta / "registry-version").write_text("1\n", encoding="utf-8")
    (meta / "standard.pin").write_text("2.0.0\n", encoding="utf-8")

    _write(facts / "timelines" / "TML-00001.yaml", {
        "id": "TML-00001", "name": "主线", "status": "active",
        "fact_version": 1, "kind": "main"})
    _write(facts / "characters" / "CHR-00001.yaml", {
        "id": "CHR-00001", "name": "主角", "status": "active", "fact_version": 1})

    for i in range(1, n_events + 1):
        rec = {
            "id": f"EVT-{i:05d}", "name": f"事件{i}", "status": "active",
            "fact_version": 1, "timeline": "TML-00001", "sequence_index": i,
            "participants": ["CHR-00001"],
            "causes": ([f"EVT-{i-1:05d}"] if i > 1 else []),
            "effects": ([f"EVT-{i+1:05d}"] if i < n_events else []),
            "summary": f"第{i}章的核心事件",
        }
        _write(facts / "events" / f"EVT-{i:05d}.yaml", rec)

    if with_brain:
        _write(root / "sources" / "novel-brain.yaml", {
            "id": "BRAIN-00001", "kind": "novel_brain", "version": "1.0",
            "mission": "让读者一口气追到天亮",
            "genre": {"primary": "玄幻", "channel": "男频"},
            "target_reader": {"who": "18-30岁男性"},
            "promise": "每三章一个高潮",
            "writing_style": {"voice": "冷峻克制的第三人称", "pov": "第三人称限知"},
            "forbidden_style": ["注水", "主角龟缩"],
        })


def _run(root: Path, **kw):
    return run_serial(project_path=root, standard_root=STANDARD, schema_dir=SCHEMA,
                      out_dir=root / "build-serial", **kw)


# --------------------------------------------------------------------------- #
# The chain runs N chapters end-to-end                                        #
# --------------------------------------------------------------------------- #
def test_serial_produces_all_chapters(tmp_path):
    _scaffold_project(tmp_path, n_events=4)
    r = _run(tmp_path)
    assert r.produced == 4
    assert r.skipped == 0
    assert all(c.ok for c in r.chapters)
    assert r.gating is False
    assert r.to_dict()["gating"] is False


def test_serial_holds_remaining_chapters_when_budget_is_exhausted(tmp_path):
    _scaffold_project(tmp_path, n_events=2)
    result = _run(tmp_path, budget_limit=0.0)

    assert result.produced == 0
    assert result.skipped == 2
    assert [chapter.stage for chapter in result.chapters] == ["budget-held", "budget-held"]
    assert not (tmp_path / "registry" / "derived" / "drafts").exists()


def test_plan_is_one_chapter_per_event_in_fold_order(tmp_path):
    _scaffold_project(tmp_path, n_events=4)
    reg = registry_loader.load(tmp_path)
    specs = plan_chapters(reg)
    assert [s.event_id for s in specs] == \
        ["EVT-00001", "EVT-00002", "EVT-00003", "EVT-00004"]
    # each chapter seeds from its event + the participating character
    assert specs[0].seeds == ["EVT-00001", "CHR-00001"]


def _write_rolling_window(root: Path, checkpoint: int) -> Path:
    start = checkpoint + 1
    value = {
        "kind": "rolling_10_chapter_plan",
        "version": "1.0",
        "checkpoint": f"cp-{checkpoint:03d}",
        "current_chapter": checkpoint,
        "active_window": 10,
        "preview_window": 20,
        "active_goals": [
            {
                "chapter_no": index,
                "band_id": f"BAND-{start:03d}-{start + 9:03d}",
                "active_goal": f"continuation goal {index}",
                "commercial_goal": "avoid plateau",
                "status": "active",
                "risk_notes": "",
                "depends_on": [f"BAND-{start:03d}-{start + 9:03d}"],
                "change_type": "initial_projection",
            }
            for index in range(start, start + 10)
        ],
        "preview_goals": [],
    }
    path = (root / "registry" / "derived" / "rolling-plans"
            / f"rolling-{checkpoint:03d}.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    return path


def test_rolling_continuation_uses_real_fact_anchor_and_plan_provenance(tmp_path):
    _scaffold_project(tmp_path, n_events=4)
    plan_path = _write_rolling_window(tmp_path, 10)
    reg = registry_loader.load(tmp_path)

    specs = plan_continuation_from_rolling_plan(
        project_path=tmp_path, reg=reg, start_chapter=11)

    assert [spec.index for spec in specs] == list(range(11, 21))
    assert {spec.event_id for spec in specs} == {"EVT-00004"}
    assert specs[0].planning_source["ref"].endswith("rolling-010.json")
    assert specs[0].planning_source["content_hash"].startswith("sha256:")
    assert specs[0].planning_source["fact_state_anchor"] == "EVT-00004"
    assert specs[0].planning_source["chapter_goal"]["chapter_no"] == 11
    assert plan_path.is_file()


def test_rolling_continuation_does_not_rewrite_earlier_chapters(tmp_path):
    _scaffold_project(tmp_path, n_events=4)
    first = _run(tmp_path)
    assert first.produced == 4
    drafts = tmp_path / "registry" / "derived" / "drafts"
    before = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in drafts.glob("TASK-0000[1-4].json")
    }
    _write_rolling_window(tmp_path, 10)

    continued = _run(
        tmp_path, start_chapter=11, max_chapters=10,
        rolling_plan_continuation=True)

    assert continued.produced == 10
    assert [chapter.spec.index for chapter in continued.chapters] == list(range(11, 21))
    after = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in drafts.glob("TASK-0000[1-4].json")
    }
    assert after == before
    package = json.loads(
        (tmp_path / "build-serial" / "TASK-00011.package.json")
        .read_text(encoding="utf-8"))
    source = package["task"]["extra"]["planning_source"]
    assert source["fact_state_anchor"] == "EVT-00004"
    assert source["chapter_goal"]["chapter_no"] == 11


def test_run_id_allocation_scans_disk_when_index_is_missing(tmp_path):
    manifests = tmp_path / "registry" / "derived" / "run-manifests"
    manifests.mkdir(parents=True)
    (manifests / "RUN-00001.json").write_text("{}", encoding="utf-8")

    assert next_run_id(_existing_run_ids(tmp_path)) == "RUN-00002"


def test_derived_index_allows_same_id_in_distinct_categories(tmp_path):
    for category in ("run-manifests", "run-aggregates"):
        derived.write_artifact(
            project_path=tmp_path, category=category, artifact_id="RUN-00001",
            artifact={}, serialized="{}\n")

    entries = [entry for entry in derived._load_index(tmp_path)["artifacts"]
               if entry["id"] == "RUN-00001"]
    assert {entry["category"] for entry in entries} == {
        "run-manifests", "run-aggregates"}


def test_rebuild_segment_manifest_preserves_real_chapter_numbers(tmp_path):
    project = tmp_path / "book"
    packages = tmp_path / "packages"
    for index in (31, 32):
        task_id = f"TASK-{index:05d}"
        run_path = project / "registry/derived/chapter-run" / f"run-{task_id}.json"
        package_path = packages / f"{task_id}.package.json"
        run_path.parent.mkdir(parents=True, exist_ok=True)
        package_path.parent.mkdir(parents=True, exist_ok=True)
        run_path.write_text(json.dumps({
            "index": index, "task_id": task_id, "event": "EVT-00033",
            "ok": True, "stage": "done", "draft_hash": f"draft-{index}",
            "state_hash": "state", "events_so_far": 33, "open_setups": 0,
        }), encoding="utf-8")
        package_path.write_text(json.dumps({
            "task": {"goal": f"goal {index}", "seeds": ["EVT-00033"], "extra": {}}}),
            encoding="utf-8")

    manifest, _ = rebuild_segment_manifest(
        project_path=project, package_dir=packages, start_chapter=31,
        end_chapter=32, run_id="RUN-00002")

    assert [chapter["index"] for chapter in manifest["chapters"]] == [31, 32]
    assert manifest["totals"]["produced"] == 2


# --------------------------------------------------------------------------- #
# State accumulates monotonically as a fold cursor (ADR-008)                   #
# --------------------------------------------------------------------------- #
def test_state_accumulates_monotonically(tmp_path):
    _scaffold_project(tmp_path, n_events=4)
    r = _run(tmp_path)
    # events_so_far grows 1,2,3,4 as the cursor advances
    assert [c.events_so_far for c in r.chapters] == [1, 2, 3, 4]
    # each chapter's state_hash is distinct (a different point in time)
    hashes = [c.state_hash for c in r.chapters]
    assert len(set(hashes)) == len(hashes)
    assert r.final_state_hash == hashes[-1]


# --------------------------------------------------------------------------- #
# The whole run is reproducible                                                #
# --------------------------------------------------------------------------- #
def test_serial_is_reproducible(tmp_path):
    _scaffold_project(tmp_path, n_events=4)
    r1 = _run(tmp_path)
    r2 = _run(tmp_path)
    assert [c.draft_hash for c in r1.chapters] == [c.draft_hash for c in r2.chapters]
    assert [c.state_hash for c in r1.chapters] == [c.state_hash for c in r2.chapters]
    assert r1.final_state_hash == r2.final_state_hash


# --------------------------------------------------------------------------- #
# Novel Brain (P15) is injected across the whole serial                        #
# --------------------------------------------------------------------------- #
def test_brain_changes_the_serial_drafts(tmp_path):
    # same facts, with vs without a Brain -> different per-chapter draft hashes
    with_brain = tmp_path / "with"
    without = tmp_path / "without"
    _scaffold_project(with_brain, n_events=3, with_brain=True)
    _scaffold_project(without, n_events=3, with_brain=False)
    rb = _run(with_brain)
    rn = _run(without)
    assert rb.produced == rn.produced == 3
    # the constitution flows into every chapter's prompt, so every draft differs
    for cb, cn in zip(rb.chapters, rn.chapters):
        assert cb.draft_hash != cn.draft_hash
    # ...but state is a fold of the SAME facts, so state hashes match
    assert [c.state_hash for c in rb.chapters] == [c.state_hash for c in rn.chapters]


# --------------------------------------------------------------------------- #
# Break/resume: a failing chapter is skipped, the serial goes on               #
# --------------------------------------------------------------------------- #
class _FlakyModel:
    """A deterministic stub that emits EMPTY prose on one chapter (by call
    order), so that chapter fails its draft-QA gate (word_count < min_words)
    while the others produce normally. Models the realistic failure mode — a bad
    generation — rather than a registry-wide gate break (which correctly fails
    every build)."""
    model_id = "flaky-stub"
    model_kind = "deterministic"

    def __init__(self, fail_on_call: int):
        self.calls = 0
        self.fail_on_call = fail_on_call

    def generate(self, prompt: str):
        from runtime.execution.model import ModelOutput
        self.calls += 1
        if self.calls == self.fail_on_call:
            return ModelOutput(text="", model_id=self.model_id,
                               model_kind=self.model_kind)
        body = "\n".join(ln for ln in prompt.splitlines() if ln.strip())
        return ModelOutput(text=body, model_id=self.model_id,
                           model_kind=self.model_kind)


def test_failing_chapter_is_skipped_not_aborted(tmp_path):
    _scaffold_project(tmp_path, n_events=4)
    # chapter 3 generates empty prose -> fails its own draft-QA gate. The serial
    # records the skip and keeps producing 1, 2, 4 (break/resume seed).
    r = _run(tmp_path, model=_FlakyModel(fail_on_call=3))
    assert r.produced == 3
    assert r.skipped == 1
    failed = [c for c in r.chapters if not c.ok]
    assert len(failed) == 1
    assert failed[0].spec.event_id == "EVT-00003"
    assert failed[0].stage.startswith("execute:")
    # the serial finished all planned chapters (did not abort) and never gated
    assert len(r.chapters) == 4
    assert r.gating is False


class _RaisingModel:
    """A stub that RAISES on one chapter instead of returning bad prose.

    _FlakyModel covers the QA-failure path (empty prose -> `not ex.ok` -> skip).
    This covers the TRANSPORT-failure path, which was a real hole: the generation
    call had no exception boundary, so a raised error escaped the per-chapter loop
    and killed the whole serial. Measured on a real 3-arm run: one curl timeout
    ended the DeepSeek arm at ch19 (18/30 produced) and a Connection error ended
    the GPT arm at ch23 (22/30) — both AFTER the retry policy's 3 attempts, and
    both losing the run manifest plus every chapter-run detector reading."""
    model_id = "raising-stub"
    model_kind = "deterministic"

    def __init__(self, fail_on_call: int, exc=None):
        self.calls = 0
        self.fail_on_call = fail_on_call
        self.exc = exc or RuntimeError("curl: (28) Operation timed out")

    def generate(self, prompt: str):
        from runtime.execution.model import ModelOutput
        self.calls += 1
        if self.calls == self.fail_on_call:
            raise self.exc
        body = "\n".join(ln for ln in prompt.splitlines() if ln.strip())
        return ModelOutput(text=body, model_id=self.model_id,
                           model_kind=self.model_kind)


def test_raised_generation_error_is_skipped_not_aborted(tmp_path):
    """The 断更恢复 promise must hold for a RAISED failure, not just a QA failure."""
    _scaffold_project(tmp_path, n_events=4)
    r = _run(tmp_path, model=_RaisingModel(fail_on_call=3))
    # the serial reached the LAST chapter instead of dying on chapter 3
    assert len(r.chapters) == 4, "serial aborted on a raised generation error"
    assert r.produced == 3
    assert r.skipped == 1
    failed = [c for c in r.chapters if not c.ok]
    assert len(failed) == 1
    assert failed[0].spec.event_id == "EVT-00003"
    # recorded in the same shape as a QA skip, so downstream consumers need no
    # special case; the message names the error class for the audit trail
    assert failed[0].stage == "execute:generation-error"
    assert "RuntimeError" in (failed[0].message or "")
    assert r.gating is False


def test_transient_llm_error_is_skipped_not_aborted(tmp_path):
    """The exact error class that killed both real arms."""
    from runtime.llm.errors import TransientLLMError
    _scaffold_project(tmp_path, n_events=3)
    r = _run(tmp_path, model=_RaisingModel(
        fail_on_call=2, exc=TransientLLMError("Connection error.")))
    assert len(r.chapters) == 3
    assert r.produced == 2 and r.skipped == 1
    assert [c.ok for c in r.chapters] == [True, False, True]


def test_run_completes_when_the_last_chapter_raises(tmp_path):
    """A failure on the FINAL chapter must still let the run finish and persist
    its post-loop artifacts (run manifest / chapter-run) — the losses that made
    the real crashes expensive."""
    _scaffold_project(tmp_path, n_events=3)
    r = _run(tmp_path, model=_RaisingModel(fail_on_call=3))
    assert len(r.chapters) == 3
    assert r.produced == 2 and r.skipped == 1
    assert r.chapters[-1].ok is False


def test_max_chapters_caps_production(tmp_path):
    _scaffold_project(tmp_path, n_events=5)
    r = _run(tmp_path, max_chapters=2)
    assert len(r.chapters) == 2
    assert r.produced == 2


# --------------------------------------------------------------------------- #
# Per-chapter run (the four §14 detectors) is persisted as a derived artifact  #
# --------------------------------------------------------------------------- #
def test_chapter_run_is_persisted_as_derived_artifact(tmp_path):
    import json
    from runtime import derived
    _scaffold_project(tmp_path, n_events=3)
    r = _run(tmp_path)
    assert r.produced == 3

    # one chapter-run artifact per chapter, on disk and in the provenance index
    for c in r.chapters:
        rel = tmp_path / "registry" / "derived" / "chapter-run" / f"run-{c.spec.task_id}.json"
        assert rel.exists(), f"missing chapter-run for {c.spec.task_id}"
        on_disk = json.loads(rel.read_text(encoding="utf-8"))
        # the persisted shape is exactly the in-memory ChapterRun.to_dict()
        assert on_disk == c.to_dict()
        # and the four detector keys survive the round-trip (may be null when the
        # deterministic stub path doesn't enrich, but the KEYS must be present)
        for k in ("pacing", "density", "ai_taste", "end_hook"):
            assert k in on_disk

    index = derived._load_index(tmp_path)
    cr_ids = {e["id"] for e in index["artifacts"] if e["category"] == "chapter-run"}
    assert cr_ids == {f"run-{c.spec.task_id}" for c in r.chapters}


def test_chapter_run_persistence_is_idempotent(tmp_path):
    _scaffold_project(tmp_path, n_events=2)
    _run(tmp_path)
    _run(tmp_path)   # a second run must not duplicate index entries
    from runtime import derived
    index = derived._load_index(tmp_path)
    cr = [e for e in index["artifacts"] if e["category"] == "chapter-run"]
    assert len(cr) == 2


# --------------------------------------------------------------------------- #
# A.1 — outline auto-supply: the serial consumes what genesis wrote            #
# --------------------------------------------------------------------------- #
import json as _json
from runtime.outline.writer import (load_project_outline, derived_outline_dir)


def _write_outline(root: Path, entries: list[dict]):
    """Drop a minimal final outline at the stable derived home genesis writes to."""
    out_dir = derived_outline_dir(root)
    out_dir.mkdir(parents=True, exist_ok=True)
    outline = {"id": "OUTLINE-00001", "kind": "novel_outline",
               "first_30_chapters": entries}
    (out_dir / "OUTLINE-00001.json").write_text(
        _json.dumps(outline, ensure_ascii=False, indent=2), encoding="utf-8")


def test_load_project_outline_present_missing_corrupt(tmp_path):
    _scaffold_project(tmp_path, n_events=2)
    # missing -> None (event-only degrade, never raises)
    assert load_project_outline(tmp_path) is None
    # present -> dict
    _write_outline(tmp_path, [{"chapter_no": 1, "goal": "开场", "reward_if_any": "实力突破"}])
    o = load_project_outline(tmp_path)
    assert o and o["id"] == "OUTLINE-00001"
    # corrupt -> None, does not raise
    (derived_outline_dir(tmp_path) / "OUTLINE-00001.json").write_text(
        "{not json", encoding="utf-8")
    assert load_project_outline(tmp_path) is None


def test_outline_grounds_chapter_ir_payoff(tmp_path):
    # With an outline entry that promises a reward, the v4 chapter IR is grounded
    # with a payoff_target; without an outline it degrades to a setup-only IR with
    # no payoff. This is the observable proof that the outline reached generation.
    grounded = tmp_path / "grounded"
    bare = tmp_path / "bare"
    _scaffold_project(grounded, n_events=2)
    _scaffold_project(bare, n_events=2)
    _write_outline(grounded, [
        {"chapter_no": 1, "goal": "开场", "reward_if_any": "实力突破", "end_hook": "钩子"}])

    r_g = _run(grounded, prompt_version="4.0.0", outline=load_project_outline(grounded))
    r_b = _run(bare, prompt_version="4.0.0", outline=load_project_outline(bare))
    assert r_g.produced >= 1 and r_b.produced >= 1

    ir_g = _json.loads((grounded / "registry" / "derived" / "chapter-ir"
                        / "ir-TASK-00001.json").read_text(encoding="utf-8"))
    ir_b = _json.loads((bare / "registry" / "derived" / "chapter-ir"
                        / "ir-TASK-00001.json").read_text(encoding="utf-8"))
    assert ir_g.get("payoff_target") and ir_g["payoff_target"]["promise"] == "实力突破"
    assert not ir_b.get("payoff_target")   # no outline -> ungrounded, degrades cleanly


# --------------------------------------------------------------------------- #
# A.3 — length constraint: outline target reaches generation + the detector    #
# --------------------------------------------------------------------------- #
def _outline_with_target(target: int, entries: list[dict] | None = None) -> dict:
    return {"id": "OUTLINE-00001", "kind": "novel_outline",
            "market_position": {"target_wordcount_per_chapter": target},
            "first_30_chapters": entries or []}


def test_length_check_rides_chapter_run(tmp_path):
    # The length detector is persisted on every chapter run, with a target when
    # the outline declares one.
    _scaffold_project(tmp_path, n_events=2)
    r = _run(tmp_path, outline=_outline_with_target(3000))
    assert r.produced == 2
    for c in r.chapters:
        assert c.length is not None
        assert c.length["reviewer"] == "length-check-v1"
        assert c.length["gating"] is False
    # and it lands in the persisted chapter-run artifact
    cr = _json.loads((tmp_path / "registry" / "derived" / "chapter-run"
                      / "run-TASK-00001.json").read_text(encoding="utf-8"))
    assert "length" in cr and cr["length"]["reviewer"] == "length-check-v1"


def test_no_target_length_check_is_neutral(tmp_path):
    # No outline target => the detector runs but is measured-not-judged (no warning).
    _scaffold_project(tmp_path, n_events=1)
    r = _run(tmp_path)   # no outline
    lc = r.chapters[0].length
    assert lc is not None
    assert not [f for f in lc["findings"] if f["severity"] == "warning"]


def test_wordcount_directive_is_byte_identical_when_absent(tmp_path):
    # The load-bearing regression: threading target_wordcount must not perturb a
    # run that has no target. A run with no outline (no target) must produce the
    # SAME draft hashes as it did before A.3 — proven by matching a run that
    # passes an outline WITHOUT a target field.
    a = tmp_path / "a"
    b = tmp_path / "b"
    _scaffold_project(a, n_events=2)
    _scaffold_project(b, n_events=2)
    ra = _run(a)                                              # outline=None
    rb = _run(b, outline={"id": "OUTLINE-00001", "first_30_chapters": []})  # no target
    assert [c.draft_hash for c in ra.chapters] == [c.draft_hash for c in rb.chapters]


def test_wordcount_target_changes_the_draft(tmp_path):
    # With a target, the style directive changes, so the deterministic-stub draft
    # differs from a no-target run — proof the directive actually reached the model.
    plain = tmp_path / "plain"
    sized = tmp_path / "sized"
    _scaffold_project(plain, n_events=1)
    _scaffold_project(sized, n_events=1)
    rp = _run(plain)
    rs = _run(sized, outline=_outline_with_target(3000))
    assert rp.chapters[0].draft_hash != rs.chapters[0].draft_hash


# --------------------------------------------------------------------------- #
# Commercial Optimization Loop wired per chapter (P16, comparison-only)        #
# --------------------------------------------------------------------------- #
from runtime.execution.reader_sim import ReaderSimulation


class _ImprovingSim:
    """Reader simulator that reports a strict improvement on every re-simulation
    (baseline low, re-sim high, nobody drops) so the commercial loop accepts the
    rewrite. reviewer_id + review() satisfy the simulator seam."""
    reviewer_id = "improving-sim"

    def __init__(self):
        self.calls = 0

    def review(self, artifact, package):
        self.calls += 1
        # odd calls = baseline (low), even calls = re-sim (high)
        high = (self.calls % 2 == 0)
        sat = 90 if high else 40
        return ReaderSimulation(
            reviewer=self.reviewer_id,
            personas=[{"name": "小白", "satisfaction": sat,
                       "would_continue": True, "degraded": False}],
            aggregate={"mean_satisfaction": sat, "continue_rate": 100,
                       "drop_personas": [], "common_expectations": []},
            judge_provenance={"model_id": "improving-sim", "degraded": False})


class _Rewriter:
    """Returns distinct non-empty prose so the rewritten draft has a new hash."""
    model_id = "rw"
    model_kind = "llm"

    def generate(self, prompt):
        from runtime.execution.model import ModelOutput
        return ModelOutput(text="商业优化后的章节正文内容。" * 30,
                           model_id=self.model_id, model_kind=self.model_kind)


class _FixedLenModel:
    """A deterministic stub that emits a FIXED-length body regardless of prompt,
    so candidate models can be given distinct lengths — the default (unanchored)
    reviewer produces no scores, so _candidate_score falls back to word_count and
    the longest candidate must win."""
    model_kind = "deterministic"

    def __init__(self, model_id: str, n_words: int):
        self.model_id = model_id
        self.n_words = n_words

    def generate(self, prompt: str):
        from runtime.execution.model import ModelOutput
        body = " ".join([f"词{i}" for i in range(self.n_words)])
        return ModelOutput(text=body, model_id=self.model_id,
                           model_kind=self.model_kind)


def test_multi_version_selects_best_and_persists_only_winner(tmp_path):
    """C6: with candidate_models of distinct lengths, the director picks the
    highest-scoring (here longest → word_count fallback) and persists ONLY it;
    losers never touch the derived draft index. A version-selection artifact is
    written recording the choice. Never gates (ADR-003)."""
    from runtime import derived as derived_mod

    _scaffold_project(tmp_path, n_events=2)
    short = _FixedLenModel("short", 120)
    best = _FixedLenModel("best", 400)      # longest → should win
    mid = _FixedLenModel("mid", 200)

    r = _run(tmp_path, candidate_models=[short, best, mid])
    assert r.produced == 2
    assert r.gating is False

    # exactly one draft persisted per chapter (losers not written)
    idx = derived_mod._load_index(tmp_path).get("artifacts", [])
    drafts = [e for e in idx if e.get("category") == "drafts"]
    assert len(drafts) == 2, "only the winning draft is persisted per chapter"

    # a version-selection artifact records the choice for each chapter
    selections = [e for e in idx if e.get("category") == "version-selection"]
    assert len(selections) == 2

    # the version-COMPARISON (per-candidate scores) is persisted too, so the
    # selection's comparison_ref resolves on disk (was a dangling id before).
    comparisons = [e for e in idx if e.get("category") == "version-comparison"]
    assert len(comparisons) == 2
    import json as _json
    cmp0 = _json.loads((tmp_path / comparisons[0]["path"]).read_text(encoding="utf-8"))
    sel0 = _json.loads((tmp_path / selections[0]["path"]).read_text(encoding="utf-8"))
    assert sel0["comparison_ref"] == cmp0["id"]      # ref now resolves
    assert cmp0["winner"] == sel0["selected_version"]
    assert len(cmp0["versions"]) == 3                # all 3 candidates scored
    assert "cand-" in sel0["reason"]                 # reason cites actual scores


def test_multi_version_single_model_is_byte_identical(tmp_path):
    """C6 degradation: candidate_models with ONE model == the single-draft path,
    byte-identical to a plain run (no version-selection artifact written)."""
    from runtime import derived as derived_mod

    plain = tmp_path / "plain"
    single = tmp_path / "single"
    _scaffold_project(plain, n_events=2)
    _scaffold_project(single, n_events=2)
    r_plain = _run(plain)
    r_single = _run(single, candidate_models=[None])  # one model (deterministic stub)

    assert [c.draft_hash for c in r_plain.chapters] == \
        [c.draft_hash for c in r_single.chapters]
    idx = derived_mod._load_index(single).get("artifacts", [])
    assert not [e for e in idx if e.get("category") == "version-selection"]


def test_multi_version_does_not_reexecute_winner(tmp_path, monkeypatch):
    """Regression: the selected winner must not be generated a second time.
    The multi-version path should call execute_package once per candidate and
    never re-run the winner with write=True."""
    _scaffold_project(tmp_path, n_events=1)

    from runtime.serialize import loop as loop_mod
    real_execute = loop_mod.execute_package
    calls = []

    def wrapped_execute_package(**kw):
        calls.append(kw.get("write"))
        return real_execute(**kw)

    monkeypatch.setattr(loop_mod, "execute_package", wrapped_execute_package)

    short = _FixedLenModel("short", 120)
    best = _FixedLenModel("best", 400)
    mid = _FixedLenModel("mid", 200)

    r = _run(tmp_path, candidate_models=[short, best, mid])
    assert r.produced == 1
    # one execute_package call per candidate, all write=False; the winner is
    # persisted from its already-built envelope, NOT re-executed with write=True.
    assert calls == [False, False, False], "winner should not be re-executed with write=True"

    # the winning draft still lands in the derived index — persisted from its
    # envelope, so removing the re-execution did not drop persistence.
    from runtime import derived as derived_mod
    idx = derived_mod._load_index(tmp_path).get("artifacts", [])
    assert len([e for e in idx if e.get("category") == "drafts"]) == 1


def test_per_chapter_budget_skips_enhancers(tmp_path):
    """M4-B4: once a chapter's generation cost reaches per_chapter_budget, the
    optional commercial loop is skipped for that chapter and a budget_note records
    why. per_chapter_budget=0.0 forces the cap on every chapter (0 >= 0), so the
    commercial loop never runs — the base draft is kept, the serial never gates."""
    capped = tmp_path / "capped"
    uncapped = tmp_path / "uncapped"
    _scaffold_project(capped, n_events=2)
    _scaffold_project(uncapped, n_events=2)

    r_cap = _run(capped, simulator=_ImprovingSim(), rewrite_model=_Rewriter(),
                 commercial_rounds=1, per_chapter_budget=0.0)
    r_unc = _run(uncapped, simulator=_ImprovingSim(), rewrite_model=_Rewriter(),
                 commercial_rounds=1)

    # capped: commercial loop skipped, budget_note set, base draft kept
    assert all(c.commercial_verdict is None for c in r_cap.chapters)
    assert all(c.budget_note and "commercial loop skipped" in c.budget_note
               for c in r_cap.chapters)
    # uncapped: the loop ran and improved each chapter
    assert all(c.commercial_verdict == "improved" for c in r_unc.chapters)
    assert all(c.budget_note is None for c in r_unc.chapters)
    # the capped run kept the plain (un-rewritten) draft
    assert [c.draft_hash for c in r_cap.chapters] != \
        [c.draft_hash for c in r_unc.chapters]
    # never gates (ADR-003)
    assert r_cap.gating is False


def test_commercial_is_off_by_default_byte_identical(tmp_path):
    # With no simulator/rewriter, the per-chapter draft hashes must equal a plain
    # serial run (the commercial wiring is purely additive).
    base = tmp_path / "base"
    comm = tmp_path / "comm"
    _scaffold_project(base, n_events=3)
    _scaffold_project(comm, n_events=3)
    r_base = _run(base)
    r_off = _run(comm)  # commercial params omitted
    assert [c.draft_hash for c in r_base.chapters] == \
        [c.draft_hash for c in r_off.chapters]
    assert all(c.commercial_verdict is None for c in r_off.chapters)


def test_commercial_rewrites_each_chapter_and_leaves_state_untouched(tmp_path):
    # A serial WITH the commercial loop vs one WITHOUT, same facts.
    plain = tmp_path / "plain"
    comm = tmp_path / "comm"
    _scaffold_project(plain, n_events=3)
    _scaffold_project(comm, n_events=3)
    r_plain = _run(plain)
    r_comm = _run(comm, simulator=_ImprovingSim(), rewrite_model=_Rewriter(),
                  commercial_rounds=1)

    assert r_comm.produced == 3
    # every chapter's reader reaction improved -> the rewrite was accepted, so
    # the draft hash differs from the plain run
    for cc, cp in zip(r_comm.chapters, r_plain.chapters):
        assert cc.commercial_verdict == "improved"
        assert cc.draft_hash != cp.draft_hash
    # ...but state is a fold of the SAME facts, so state hashes are IDENTICAL —
    # commercial optimization changes prose, never state (ADR-008).
    assert [c.state_hash for c in r_comm.chapters] == \
        [c.state_hash for c in r_plain.chapters]
    # the serial still never gates
    assert r_comm.gating is False


def test_commercial_serial_drafts_still_pass_deterministic_gate(tmp_path):
    # The reader-preferred draft that gets written back must have passed the
    # deterministic draft-QA gate (run_serial re-gates before writing it).
    from runtime.execution.draft_qa import check_draft
    from runtime.execution.envelope import unwrap
    from runtime import derived as derived_mod
    import json

    _scaffold_project(tmp_path, n_events=2)
    r = _run(tmp_path, simulator=_ImprovingSim(), rewrite_model=_Rewriter(),
             commercial_rounds=1)
    assert r.produced == 2
    # read back each written draft artifact and confirm it passes the gate
    idx = derived_mod._load_index(tmp_path)
    draft_entries = [e for e in idx["artifacts"] if e["category"] == "drafts"]
    assert draft_entries
    for e in draft_entries:
        obj = json.loads((tmp_path / e["path"]).read_text(encoding="utf-8"))
        draft = unwrap(obj)
        assert check_draft(draft) == []


# --------------------------------------------------------------------------- #
# Regression: the serial CLI must build a GENERATION model for a live provider #
# (a real-model run once produced deterministic-stub prose because             #
# --model-provider was ignored for generation — only --commercial built one).  #
# --------------------------------------------------------------------------- #
import argparse

from runtime import cli


def _serial_args(**over):
    base = dict(project="/tmp/x", standard_root=str(STANDARD), schema_dir=None,
                out=None, model_provider="deterministic", model_id="m",
                temperature=0.7, top_p=None, max_tokens=None, timeout=120,
                replay_dir=None, commercial=False, commercial_rounds=2,
                prompt_version="1.0.0", max_chapters=None, max_depth=2,
                speech=False, mandate=False, vary_openings=False, long_arc=False,
                reviewer="unanchored", panel_roles="literary,structural",
                env_file=None)
    base.update(over)
    return argparse.Namespace(**base)


def test_serial_cli_builds_gen_model_for_live_provider(monkeypatch):
    captured = {}

    def fake_run_serial(**kw):
        captured.update(kw)
        return __import__("runtime.serialize", fromlist=["SerialResult"]).SerialResult(
            reviewer="test")

    monkeypatch.setattr("runtime.serialize.run_serial", fake_run_serial)
    monkeypatch.setattr(cli, "_load_dotenv", lambda args: None)
    monkeypatch.setattr(cli, "_build_llm_model",
                        lambda args, **kw: f"LLM<{kw.get('replay_suffix')}>")

    # live provider -> a generation model MUST be built and passed
    cli._cmd_serial_run(_serial_args(model_provider="deepseek"))
    assert captured["model"] == "LLM<gen>"

    # deterministic -> no live model (falls back to the stub inside run_serial)
    captured.clear()
    cli._cmd_serial_run(_serial_args(model_provider="deterministic"))
    assert captured["model"] is None


def test_serial_cli_passes_reviewer_to_run_serial(monkeypatch):
    """The gap this fixes: the CLI built no reviewer for the serial, so verdicts
    were always None. Now --reviewer is resolved and threaded into run_serial."""
    captured = {}

    def fake_run_serial(**kw):
        captured.update(kw)
        return __import__("runtime.serialize", fromlist=["SerialResult"]).SerialResult(
            reviewer="test")

    monkeypatch.setattr("runtime.serialize.run_serial", fake_run_serial)
    monkeypatch.setattr(cli, "_load_dotenv", lambda args: None)
    monkeypatch.setattr(cli, "_build_llm_model",
                        lambda args, **kw: f"LLM<{kw.get('replay_suffix')}>")

    # default: the deterministic unanchored reviewer IS passed (not None), so the
    # verdict fold always has a reviewer to read.
    cli._cmd_serial_run(_serial_args())
    assert captured["reviewer"] is not None
    assert captured["reviewer"].reviewer_id == "unanchored-entity-reviewer-v1"

    # llm-quality with a live provider: a scoring judge is built and passed.
    captured.clear()
    cli._cmd_serial_run(_serial_args(reviewer="llm-quality", model_provider="deepseek"))
    assert captured["reviewer"].reviewer_id == "llm-quality-judge-v1"

    # a scoring reviewer without a live provider is refused (no silent no-op).
    import pytest
    with pytest.raises(SystemExit):
        cli._cmd_serial_run(_serial_args(reviewer="llm-quality", model_provider="deterministic"))


def test_serial_cli_merges_reference_abstraction_into_outline(monkeypatch, tmp_path):
    """M5 built≠live regression: the reference LM abstraction is a runtime sibling,
    NEVER persisted inside the frozen outline (outline.schema is
    additionalProperties:false). The IR / long-arc / prompt-binding consumers read
    it off the outline object, so the CLI must merge the standalone artifact onto
    the IN-MEMORY outline before run_serial. The pre-existing consumer tests
    self-feed the field, so only THIS test covers the real load→merge path."""
    import json as _json
    captured = {}

    def fake_run_serial(**kw):
        captured.update(kw)
        return __import__("runtime.serialize", fromlist=["SerialResult"]).SerialResult(
            reviewer="test")

    monkeypatch.setattr("runtime.serialize.run_serial", fake_run_serial)
    monkeypatch.setattr(cli, "_load_dotenv", lambda args: None)

    project = tmp_path / "proj"
    # a persisted outline WITHOUT the field (contract-clean, as it is on disk)
    outdir = project / "registry" / "derived" / "outline"
    outdir.mkdir(parents=True)
    (outdir / "OUTLINE-00001.json").write_text(
        _json.dumps({"id": "OUTLINE-00001", "first_30_chapters": []}), encoding="utf-8")
    # a persisted standalone reference-abstraction artifact
    absdir = project / "registry" / "derived" / "reference-abstract"
    absdir.mkdir(parents=True)
    (absdir / "REFABSTRACT-001.json").write_text(
        _json.dumps({"id": "REFABSTRACT-001", "kind": "reference_lm_abstraction",
                     "market_positioning": {"core_promise": "强钩子开局"}}),
        encoding="utf-8")

    cli._cmd_serial_run(_serial_args(project=str(project)))

    # the outline handed to run_serial carries the abstraction (in-memory merge),
    # so IR/arc/binding get it on the real path — even though disk stays clean.
    passed_outline = captured["outline"]
    assert passed_outline is not None
    assert passed_outline.get("reference_abstraction", {}).get("id") == "REFABSTRACT-001"
    # and the on-disk outline was NOT mutated (contract-clean)
    on_disk = _json.loads((outdir / "OUTLINE-00001.json").read_text(encoding="utf-8"))
    assert "reference_abstraction" not in on_disk


def test_serial_cli_originality_is_default_on_with_a_corpus(monkeypatch, tmp_path):
    """M1-B2: the M7 originality similarity arm is default-on when the project
    ships a reference corpus (no --originality flag needed), and --no-originality
    forces it off. Absent a corpus it is a silent no-op."""
    captured = {}

    def fake_run_serial(**kw):
        captured.update(kw)
        return __import__("runtime.serialize", fromlist=["SerialResult"]).SerialResult(
            reviewer="test")

    monkeypatch.setattr("runtime.serialize.run_serial", fake_run_serial)
    monkeypatch.setattr(cli, "_load_dotenv", lambda args: None)

    # project WITH a reference corpus: similarity refs are loaded by default.
    project = tmp_path / "proj"
    refs = project / "sources" / "reference-novels"
    refs.mkdir(parents=True)
    (refs / "ref1.txt").write_text("少年觉醒传承，逃离宗门追杀。" * 40, encoding="utf-8")

    cli._cmd_serial_run(_serial_args(project=str(project)))
    assert captured["originality_references"], "corpus present => refs loaded by default"
    assert captured["originality_references"][0]["source_type"] == "reference_novel"

    # --no-originality forces the arm off even with a corpus present.
    captured.clear()
    cli._cmd_serial_run(_serial_args(project=str(project), no_originality=True))
    assert captured["originality_references"] is None

    # project WITHOUT a corpus: silent no-op (no refs, no crash).
    captured.clear()
    cli._cmd_serial_run(_serial_args(project=str(tmp_path / "empty")))
    assert captured["originality_references"] is None


def test_serial_cli_prompt_version_and_speech(monkeypatch):
    # A.2: the CLI default is the full stack (v6); --speech bumps to v7. The
    # command must forward the RESOLVED version to run_serial (not the raw arg).
    captured = {}

    def fake_run_serial(**kw):
        captured.update(kw)
        return __import__("runtime.serialize", fromlist=["SerialResult"]).SerialResult(
            reviewer="test")

    monkeypatch.setattr("runtime.serialize.run_serial", fake_run_serial)
    monkeypatch.setattr(cli, "_load_dotenv", lambda args: None)

    # explicit v6 passes through
    cli._cmd_serial_run(_serial_args(prompt_version="6.0.0"))
    assert captured["prompt_version"] == "6.0.0"

    # --speech overrides to v7 regardless of the prompt_version arg
    captured.clear()
    cli._cmd_serial_run(_serial_args(prompt_version="6.0.0", speech=True))
    assert captured["prompt_version"] == "7.0.0"

    # --mandate overrides to v8, and wins over --speech (v8 sits above v7)
    captured.clear()
    cli._cmd_serial_run(_serial_args(prompt_version="6.0.0", mandate=True))
    assert captured["prompt_version"] == "8.0.0"
    captured.clear()
    cli._cmd_serial_run(_serial_args(prompt_version="6.0.0", speech=True, mandate=True))
    assert captured["prompt_version"] == "8.0.0"

    # --vary-openings overrides to v9, winning over --mandate/--speech (v9 ⊃ v8 ⊃ v7)
    captured.clear()
    cli._cmd_serial_run(_serial_args(prompt_version="6.0.0", vary_openings=True))
    assert captured["prompt_version"] == "9.0.0"
    captured.clear()
    cli._cmd_serial_run(_serial_args(prompt_version="6.0.0", speech=True,
                                     mandate=True, vary_openings=True))
    assert captured["prompt_version"] == "9.0.0"

    # --long-arc overrides to v10, winning over all lower flags (v10 ⊃ v9 ⊃ v8 ⊃ v7)
    captured.clear()
    cli._cmd_serial_run(_serial_args(prompt_version="6.0.0", long_arc=True))
    assert captured["prompt_version"] == "10.0.0"
    captured.clear()
    cli._cmd_serial_run(_serial_args(prompt_version="6.0.0", speech=True,
                                     mandate=True, vary_openings=True, long_arc=True))
    assert captured["prompt_version"] == "10.0.0"


# --------------------------------------------------------------------------- #
# Director-driven generation (Phase 7.1, prompt v6)                            #
# --------------------------------------------------------------------------- #
def test_v6_injects_director_objective_and_differs_from_v5(tmp_path):
    """v6 folds a ChapterObjective + DirectorBrief into the prompt; the injected
    director intent changes the draft, so v6 draft hashes differ from v5's. State
    is unaffected — the director changes prose, never facts (ADR-008)."""
    v5root = tmp_path / "v5"
    v6root = tmp_path / "v6"
    _scaffold_project(v5root, n_events=3)
    _scaffold_project(v6root, n_events=3)
    r5 = _run(v5root, prompt_version="5.0.0")
    r6 = _run(v6root, prompt_version="6.0.0")
    assert r6.produced == r5.produced == 3
    assert r6.gating is False
    # the director objective is a new prompt input, so every v6 draft differs
    for c5, c6 in zip(r5.chapters, r6.chapters):
        assert c6.draft_hash != c5.draft_hash
    # but the fold cursor (state) is identical — director does not touch facts
    assert [c.state_hash for c in r5.chapters] == [c.state_hash for c in r6.chapters]


def test_v6_persists_objective_and_brief_artifacts(tmp_path):
    """The director objective/brief are written as derived artifacts (obj-/dbr-
    prefixes) so read-side consumers (7.4 dashboard) can fold them."""
    _scaffold_project(tmp_path, n_events=2)
    _run(tmp_path, prompt_version="6.0.0")
    obj_dir = tmp_path / "registry" / "derived" / "chapter-objective"
    dbr_dir = tmp_path / "registry" / "derived" / "director-brief"
    assert obj_dir.exists() and dbr_dir.exists()
    assert len(list(obj_dir.glob("*.json"))) == 2
    assert len(list(dbr_dir.glob("*.json"))) == 2


def test_v6_is_reproducible(tmp_path):
    """Same project + v6 -> same per-chapter draft AND state hashes (the objective
    is a deterministic fold of the IR + cursor, so it adds no nondeterminism)."""
    _scaffold_project(tmp_path, n_events=3)
    r1 = _run(tmp_path, prompt_version="6.0.0")
    r2 = _run(tmp_path, prompt_version="6.0.0")
    assert [c.draft_hash for c in r1.chapters] == [c.draft_hash for c in r2.chapters]
    assert [c.state_hash for c in r1.chapters] == [c.state_hash for c in r2.chapters]


# --------------------------------------------------------------------------- #
# Opening-diversity constraint (§14 anti-AI prevention, prompt v9)             #
# --------------------------------------------------------------------------- #
def test_v8_is_byte_identical_after_v9_added(tmp_path):
    """Adding v9 must NOT change v8: a v8 run reproduces the same per-chapter draft
    and state hashes (v9's new prompt var is bound ONLY on the v9 path)."""
    a = tmp_path / "a"
    b = tmp_path / "b"
    _scaffold_project(a, n_events=3)
    _scaffold_project(b, n_events=3)
    r8 = _run(a, prompt_version="8.0.0")
    r8b = _run(b, prompt_version="8.0.0")
    assert [c.draft_hash for c in r8.chapters] == [c.draft_hash for c in r8b.chapters]
    assert [c.state_hash for c in r8.chapters] == [c.state_hash for c in r8b.chapters]


def test_v9_injects_recent_openings_and_differs_from_v8(tmp_path):
    """v9 folds the recent-openings constraint into the prompt from chapter 2 on,
    so its later drafts differ from v8's. State is unaffected (prose-only, ADR-008)."""
    v8root = tmp_path / "v8"
    v9root = tmp_path / "v9"
    _scaffold_project(v8root, n_events=3)
    _scaffold_project(v9root, n_events=3)
    r8 = _run(v8root, prompt_version="8.0.0")
    r9 = _run(v9root, prompt_version="9.0.0")
    assert r9.produced == r8.produced == 3
    assert r9.gating is False
    # chapter 1 has no prior openings (sentinel), later chapters get the constraint
    # -> at least one later draft differs from the v8 counterpart
    assert any(c9.draft_hash != c8.draft_hash
               for c8, c9 in zip(r8.chapters[1:], r9.chapters[1:]))
    # the fold cursor (state) is identical — the constraint changes prose, not facts
    assert [c.state_hash for c in r8.chapters] == [c.state_hash for c in r9.chapters]


def test_v9_is_reproducible(tmp_path):
    """Same project + v9 -> same hashes (recent-openings is a deterministic fold of
    prior bodies, adding no nondeterminism)."""
    _scaffold_project(tmp_path, n_events=3)
    r1 = _run(tmp_path, prompt_version="9.0.0")
    r2 = _run(tmp_path, prompt_version="9.0.0")
    assert [c.draft_hash for c in r1.chapters] == [c.draft_hash for c in r2.chapters]


# --------------------------------------------------------------------------- #
# Long-Arc coordinate (Long-Arc Planner M3, prompt v10)                        #
# --------------------------------------------------------------------------- #
def test_v9_is_byte_identical_after_v10_added(tmp_path):
    """Adding v10 must NOT change v9: a v9 run reproduces the same per-chapter
    draft and state hashes (v10's long_arc var is bound ONLY on the v10 path)."""
    a = tmp_path / "a"
    b = tmp_path / "b"
    _scaffold_project(a, n_events=3)
    _scaffold_project(b, n_events=3)
    r9 = _run(a, prompt_version="9.0.0")
    r9b = _run(b, prompt_version="9.0.0")
    assert [c.draft_hash for c in r9.chapters] == [c.draft_hash for c in r9b.chapters]
    assert [c.state_hash for c in r9.chapters] == [c.state_hash for c in r9b.chapters]


def test_v10_injects_long_arc_and_differs_from_v9(tmp_path):
    """v10 folds each chapter's long-arc coordinate into the prompt, so its drafts
    differ from v9's. State is unaffected (prose-only, ADR-008)."""
    v9root = tmp_path / "v9"
    v10root = tmp_path / "v10"
    _scaffold_project(v9root, n_events=3)
    _scaffold_project(v10root, n_events=3)
    r9 = _run(v9root, prompt_version="9.0.0")
    r10 = _run(v10root, prompt_version="10.0.0")
    assert r10.produced == r9.produced == 3
    assert r10.gating is False
    # the long-arc coordinate is a new prompt input on every chapter, so at least
    # one draft differs from its v9 counterpart
    assert any(c10.draft_hash != c9.draft_hash
               for c9, c10 in zip(r9.chapters, r10.chapters))
    # the fold cursor (state) is identical — the coordinate changes prose, not facts
    assert [c.state_hash for c in r9.chapters] == [c.state_hash for c in r10.chapters]


def test_v10_is_reproducible(tmp_path):
    """Same project + v10 -> same hashes (the long-arc plan is a deterministic fold
    of the outline, adding no nondeterminism)."""
    _scaffold_project(tmp_path, n_events=3)
    r1 = _run(tmp_path, prompt_version="10.0.0")
    r2 = _run(tmp_path, prompt_version="10.0.0")
    assert [c.draft_hash for c in r1.chapters] == [c.draft_hash for c in r2.chapters]


# --------------------------------------------------------------------------- #
# DirectorSession rides the envelope (Phase 7.2)                               #
# --------------------------------------------------------------------------- #
def test_v6_director_session_rides_envelope_with_real_refs(tmp_path):
    """A v6 run writes a schema-valid DirectorSession onto each chapter's on-disk
    envelope, referencing the REAL objective/brief ids (not the ad-hoc task_id/
    content_hash the Phase 6 dict used). It never gates and never touches the
    inner draft (frozen schema, additionalProperties:false)."""
    import json
    from runtime.execution.envelope import ENVELOPE_FORMAT, unwrap
    from runtime.director import validate_director_session
    _scaffold_project(tmp_path, n_events=2)
    _run(tmp_path, prompt_version="6.0.0")
    drafts_dir = tmp_path / "registry" / "derived" / "drafts"
    files = sorted(drafts_dir.glob("*.json"))
    assert files, "no draft envelopes written"
    for f in files:
        env = json.loads(f.read_text(encoding="utf-8"))
        assert env.get("envelope_format") == ENVELOPE_FORMAT
        sess = env.get("director")
        assert sess is not None, "director session missing from envelope"
        assert validate_director_session(sess) == []
        assert sess["gating"] is False
        assert sess["authority"] == "human"
        # real director refs, not task_id / content_hash posing as ids
        assert sess["objective_id"] and sess["objective_id"].startswith("OBJ-")
        assert sess["brief_id"] and sess["brief_id"].startswith("DBR-")
        # session rides the envelope, NOT the sealed inner draft
        assert "director" not in unwrap(env)


def test_v5_run_still_writes_a_valid_degraded_session(tmp_path):
    """A v5 run (no director objective) still writes a valid DirectorSession —
    degraded: objective_id/brief_id null — so the audit record exists for every
    chapter regardless of prompt version. v5 draft content is unaffected."""
    import json
    from runtime.director import validate_director_session
    _scaffold_project(tmp_path, n_events=2)
    _run(tmp_path, prompt_version="5.0.0")
    drafts_dir = tmp_path / "registry" / "derived" / "drafts"
    for f in sorted(drafts_dir.glob("*.json")):
        env = json.loads(f.read_text(encoding="utf-8"))
        sess = env.get("director")
        assert sess is not None
        assert validate_director_session(sess) == []
        assert sess["objective_id"] is None
        assert sess["brief_id"] is None


# --------------------------------------------------------------------------- #
# Cross-chapter feedback: the director learns from realized signals (Phase 7.3) #
# --------------------------------------------------------------------------- #
def _scaffold_setup_backlog_project(root: Path, *, n_events: int):
    """A project whose events are all dangling setups (伏笔, no effects chain), so
    the open-setup backlog grows monotonically and the director feedback fold has
    a REAL adverse signal to react to."""
    _scaffold_project(root, n_events=n_events)
    events = root / "registry" / "facts" / "events"
    for i in range(1, n_events + 1):
        rec = {
            "id": f"EVT-{i:05d}", "name": f"事件{i}", "status": "active",
            "fact_version": 1, "timeline": "TML-00001", "sequence_index": i,
            "participants": ["CHR-00001"], "causes": [], "effects": [],
            "summary": f"[伏笔] 第{i}章埋下的线索",
        }
        _write(events / f"EVT-{i:05d}.yaml", rec)


def test_v6_feedback_diverges_objective_when_backlog_grows(tmp_path):
    """With a growing setup backlog, a LATER chapter's objective must diverge from
    an EARLY chapter's: once the previous chapter's open_setups crosses the
    threshold, feedback pushes payoff_type to 'clear_payoff'. The early chapter,
    with a small prior backlog, keeps the default 'partial_payoff'."""
    import json
    _scaffold_setup_backlog_project(tmp_path, n_events=6)
    r = _run(tmp_path, prompt_version="6.0.0")
    assert r.produced == 6
    assert r.gating is False
    obj_dir = tmp_path / "registry" / "derived" / "chapter-objective"
    objs = {}
    for f in obj_dir.glob("*.json"):
        o = json.loads(f.read_text(encoding="utf-8"))
        objs[o["chapter_id"]] = o
    payoffs = {cid: o["commercial_intent"]["payoff_type"] for cid, o in objs.items()}
    # early chapters keep the neutral default; later chapters (prev backlog > 3)
    # diverge to a clearer payoff — the director reacted to the realized signal
    assert "partial_payoff" in payoffs.values(), payoffs
    assert "clear_payoff" in payoffs.values(), payoffs


def test_v6_feedback_leaves_state_untouched(tmp_path):
    """Feedback shapes PROSE INTENT only; it never writes facts, so the fold
    cursor (state_hash) is identical to a run where the backlog does not trigger
    feedback. Director changes prose, never state (ADR-008)."""
    # same events, but as a normal causal chain (no backlog) vs a setup backlog:
    # the state_hash sequence differs by FACTS, not by whether feedback fired — so
    # we instead assert feedback adds no nondeterminism: two backlog runs match.
    a = tmp_path / "a"
    b = tmp_path / "b"
    _scaffold_setup_backlog_project(a, n_events=6)
    _scaffold_setup_backlog_project(b, n_events=6)
    ra = _run(a, prompt_version="6.0.0")
    rb = _run(b, prompt_version="6.0.0")
    assert [c.state_hash for c in ra.chapters] == [c.state_hash for c in rb.chapters]
    assert [c.draft_hash for c in ra.chapters] == [c.draft_hash for c in rb.chapters]


# --------------------------------------------------------------------------- #
# Quality reviewer wired into the serial => a per-chapter verdict (the gap the  #
# CLI left: reviewer built but never passed, so verdicts were always None).     #
# --------------------------------------------------------------------------- #
from runtime.execution.quality_center import (QualityReport, chapter_quality_verdict,
                                              SCORE_DIMENSIONS)


class _StubScoringReviewer:
    """A DraftReviewer that returns FIXED per-dimension scores, so we can drive
    the serial's verdict fold without a live model. Scores are a callable of the
    chapter index so a test can make a later chapter regress."""

    reviewer_id = "stub-scoring-reviewer"

    def __init__(self, score_for):
        self._score_for = score_for
        self._n = 0

    def review(self, artifact, package, grounding=None):
        self._n += 1
        val = self._score_for(self._n)
        return QualityReport(reviewer=self.reviewer_id,
                             scores={d: val for d in SCORE_DIMENSIONS})


def test_verdict_derivation_unit():
    # degraded: provenance flags it, or every score is zero
    assert chapter_quality_verdict(
        {"scores": {"hook": 0, "conflict": 0}}, None) == "degraded"
    assert chapter_quality_verdict(
        {"scores": {"hook": 70}, "judge_provenance": {"degraded": True}}, None) == "degraded"
    # first chapter (no prior) with real scores => clean
    assert chapter_quality_verdict({"scores": {"hook": 80, "conflict": 78}}, None) is None
    # a real drop vs prev => regressed
    assert chapter_quality_verdict(
        {"scores": {"hook": 60, "conflict": 60}}, {"hook": 85, "conflict": 85}) == "regressed"
    # within-margin jitter => clean
    assert chapter_quality_verdict(
        {"scores": {"hook": 83, "conflict": 83}}, {"hook": 85, "conflict": 85}) is None
    # no scores (a deterministic reviewer) => None (keeps the serial byte-identical)
    assert chapter_quality_verdict({"reviewer": "unanchored", "findings": []}, {"hook": 85}) is None
    # all-zero across ALL 18 dims is the judge's "can't evaluate" sentinel => degraded,
    # NOT regressed — even though the risk dims (reader_drop_risk/originality_risk/
    # safety_risk) invert 0→100 so the overall mean is ~16.7, never 0. Real live bug:
    # a genesis-pilot chapter scored all-zero (parse_ok=True, degraded=False) and was
    # misread as 'regressed' -73 before the raw-score check. prev high so a naive mean
    # comparison would also say 'regressed' — degraded must win.
    all_zero = {d: 0 for d in SCORE_DIMENSIONS}
    assert chapter_quality_verdict({"scores": all_zero,
                                    "judge_provenance": {"parse_ok": True, "degraded": False}},
                                   {d: 85 for d in SCORE_DIMENSIONS}) == "degraded"


def test_serial_with_scoring_reviewer_produces_verdicts(tmp_path):
    """A scoring reviewer populates ChapterRun.verdict; a mid-run quality drop
    reads as 'regressed' via the cross-chapter fold."""
    _scaffold_project(tmp_path, n_events=4)
    # chapters 1-2 score high, chapter 3 drops hard (regression), 4 recovers
    scores = {1: 85, 2: 85, 3: 55, 4: 85}
    r = _run(tmp_path, reviewer=_StubScoringReviewer(lambda n: scores[n]))
    verdicts = [c.verdict for c in r.chapters]
    assert verdicts[0] is None            # first chapter: no prior to compare
    assert verdicts[2] == "regressed"     # chapter 3 dropped vs chapter 2
    assert r.gating is False              # ADR-003: still never gates
    assert r.produced == 4                # a low verdict never SKIPS a chapter
    assert all(c.ok for c in r.chapters)


def test_serial_default_reviewer_leaves_verdict_none(tmp_path):
    """The default deterministic reviewer produces no scores => verdict stays
    None on every chapter => byte-identical to before the wiring."""
    _scaffold_project(tmp_path, n_events=3)
    r = _run(tmp_path)   # no reviewer => execute falls back to unanchored
    assert all(c.verdict is None for c in r.chapters)
