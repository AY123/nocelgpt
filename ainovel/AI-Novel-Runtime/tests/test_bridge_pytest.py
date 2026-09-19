"""test_bridge_pytest.py — PromptRuntime -> LLMExecutionModel bridge (ANES v2).

Proves the v2 execution bridge contract:
  1. PromptManifest enters provenance — via the Runtime envelope on disk.
  2. Streaming yields incremental deltas AND a coherent final draft.
  3. Retry + fallback survive a transient provider failure.
  4. Deterministic replay: a replayed run reproduces the inner draft's
     content_hash byte-for-byte (replay is semantic, not temporal).
  5. ADR-005 layering: the llm/ layer never imports the prompt/ subdomain.

Run: python3 -m pytest tests/test_bridge_pytest.py
"""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest

from runtime import compiler
from runtime.pipeline import build_task_package
from runtime.execution.run import execute_package
from runtime.execution.agent import ChapterDraftAgent
from runtime.execution.llm_model import LLMExecutionModel, manifest_to_prompt_provenance
from runtime.execution.model import StreamEvent
from runtime.prompt.runtime import PromptRuntime

HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "fixtures" / "proj-demo"
STANDARD = HERE.parent.parent / "AI-Novel-Standard"
SCHEMA = STANDARD / "phase-1" / "generated" / "json-schema"
PROMPTS = STANDARD / "contracts" / "prompts"


@pytest.fixture
def env(tmp_path):
    project = tmp_path / "proj"
    shutil.copytree(FIXTURE, project)
    out = tmp_path / "build"
    r = build_task_package(
        project_path=project, schema_dir=SCHEMA,
        task=compiler.TaskDefinition("TASK-00018", "draft chapter 18",
                                     "ChapterDraft", ["CHR-00001", "EVT-00002"]),
        out_dir=out)
    assert r.ok, r.message
    return project, r.package


def _runtime():
    return PromptRuntime(prompt_root=PROMPTS)


def test_streaming_yields_deltas_and_final_draft(env):
    project, package = env
    events = []
    model = LLMExecutionModel(provider="mock", model_id="mock-1", stream=True)
    agent = ChapterDraftAgent(model=model, prompt_runtime=_runtime(),
                              on_event=events.append)
    artifact = agent.run(package)

    deltas = [e for e in events if e.kind == "delta"]
    dones = [e for e in events if e.kind == "done"]
    assert deltas, "streaming must surface incremental deltas"
    assert len(dones) == 1, "exactly one terminal done event"
    # the streamed deltas reconstruct the same body the artifact carries
    streamed = "".join(e.text_delta for e in deltas).strip()
    assert streamed == artifact["body"]
    assert artifact["produced_by"]["model_kind"] == "llm"


def test_manifest_enters_provenance_via_request(env):
    project, package = env
    rendered, manifest = _runtime().render(
        prompt_id="chapter-draft", version="1.0.0", package=package)
    prov = manifest_to_prompt_provenance(manifest)
    # the manifest's identity hashes are what travel on the wire
    assert prov.prompt_hash == manifest.rendered_hash
    assert prov.package_hash == manifest.package_hash
    assert prov.derived_from == list(manifest.derived_from)


def test_rendered_messages_are_the_wire_payload(env):
    project, package = env
    model = LLMExecutionModel(provider="mock", model_id="mock-1")
    agent = ChapterDraftAgent(model=model, prompt_runtime=_runtime())
    agent.run(package)
    req = model.last_request
    # the request messages come from rendered.messages (a user turn exists),
    # not from a flattened legacy string.
    roles = [m.role for m in req.messages]
    assert "user" in roles
    assert req.prompt_provenance.prompt_id == "chapter-draft"
    assert req.capability == "ChapterDraft"


def test_language_register_lock_reaches_wire_system_message(env):
    """两周清单 Week-1 item 1 (中文语域锁定) regression.

    The chapter-draft templates ship an ENGLISH system message. Before the fix,
    that made has_system=True and the Chinese language instruction was dropped,
    so the model got an all-English system prompt (the 语域漂移 root cause). The
    fix ALWAYS merges the Chinese language directive into the leading system
    message on the wire, without touching the frozen template or rendered_hash.
    """
    from runtime.execution.llm_model import LANGUAGE_REGISTER_DIRECTIVE

    # Render a real template so we exercise the true (English-system) payload.
    rendered, manifest = _runtime().render(
        prompt_id="chapter-draft", version="1.0.0", package=package_of(env))
    # the template itself ships an English system message and no Chinese lock
    tmpl_system = next(m for m in rendered.messages if m["role"] == "system")
    assert "professional long-form fiction" in tmpl_system["content"]
    assert "中文" not in tmpl_system["content"]

    model = LLMExecutionModel(provider="mock", model_id="mock-1")
    req = model._request_from_rendered(rendered, manifest)

    system_msgs = [m for m in req.messages if m.role == "system"]
    assert len(system_msgs) == 1, "exactly one leading system message on the wire"
    wire_system = system_msgs[0].content
    # the Chinese register lock now LEADS the system prompt …
    assert wire_system.startswith(LANGUAGE_REGISTER_DIRECTIVE)
    assert "必须全程使用简体中文" in wire_system
    # … and the original template task instructions are preserved after it
    assert "professional long-form fiction" in wire_system


def package_of(env):
    return env[1]


def test_live_equals_replay_content_hash(env, tmp_path):
    """Requirement #4: a replayed run reproduces the inner draft content_hash."""
    project, package = env
    replay_dir = str(tmp_path / "replay")

    live_model = LLMExecutionModel(provider="mock", model_id="mock-1",
                                   replay_dir=replay_dir)
    live = ChapterDraftAgent(model=live_model, prompt_runtime=_runtime()).run(package)
    assert live_model.last_response.replay_ref  # recorded

    replay_model = LLMExecutionModel(provider="mock", model_id="mock-1",
                                     replay_dir=replay_dir)
    replayed = ChapterDraftAgent(model=replay_model, prompt_runtime=_runtime()).run(package)

    assert replayed["content_hash"] == live["content_hash"]
    assert replayed["body"] == live["body"]


def test_streaming_replay_is_semantic_not_temporal(env, tmp_path):
    """Replay must NOT emit chunked deltas — one reconstructed done event."""
    project, package = env
    replay_dir = str(tmp_path / "replay")

    # prime the replay cache with a live (mock) stream
    warm_events = []
    warm = LLMExecutionModel(provider="mock", model_id="mock-1",
                             replay_dir=replay_dir, stream=True)
    live = ChapterDraftAgent(model=warm, prompt_runtime=_runtime(),
                             on_event=warm_events.append).run(package)
    assert any(e.kind == "delta" for e in warm_events)  # live streamed deltas

    # replay the same request as a stream
    replay_events = []
    cold = LLMExecutionModel(provider="mock", model_id="mock-1",
                             replay_dir=replay_dir, stream=True)
    replayed = ChapterDraftAgent(model=cold, prompt_runtime=_runtime(),
                                 on_event=replay_events.append).run(package)

    assert [e.kind for e in replay_events] == ["done"], \
        "replay is semantic: a single reconstructed completion, no deltas"
    assert replayed["content_hash"] == live["content_hash"]


def test_retry_then_fallback_survives_transient(env):
    """A transient failure on the primary provider falls back; the try-log is
    captured in produced_by.attempts."""
    from runtime.llm.errors import TransientLLMError
    from runtime.llm.fallback import FallbackLLMClient

    project, package = env

    class _Boom:
        def generate(self, request):
            raise TransientLLMError("primary down")

        def stream(self, request):
            raise TransientLLMError("primary down")

    model = LLMExecutionModel(provider="mock", model_id="mock-1")
    # swap in a fallback chain: failing primary -> healthy mock
    model.client = FallbackLLMClient([("boom", _Boom()), ("mock", model.client)])
    artifact = ChapterDraftAgent(model=model, prompt_runtime=_runtime()).run(package)

    attempts = artifact["produced_by"]["llm"]["attempts"]
    statuses = {a["provider"]: a["status"] for a in attempts}
    assert statuses.get("boom") == "transient_error"
    assert statuses.get("mock") == "ok"


def test_adr005_llm_layer_does_not_import_prompt():
    """Fitness: the resource layer (llm/) must not depend on prompt/."""
    import re
    llm_pkg = HERE.parent / "runtime" / "llm"
    offenders = []
    for p in llm_pkg.rglob("*.py"):
        src = p.read_text(encoding="utf-8")
        if re.search(r"^\s*(from|import)\s+.*\bprompt\b", src, re.MULTILINE):
            offenders.append(str(p))
    assert not offenders, f"llm/ must not import prompt/: {offenders}"


def test_unanchored_entity_reviewer_flags_invented_faction(env):
    """The evaluative reviewer warns on a proper noun with no fact anchor, passes
    known fact names, and NEVER gates (ADR-003)."""
    from runtime.execution.draft_review import unanchored_entity_reviewer

    project, package = env
    artifact = {
        "body": (
            "Vael Ardyn knelt before Maesa Korrin and swore upon the "
            "Oathblade. She had joined the Order of the Severed Chain, "
            "an order whose name appears in no registry fact."
        ),
    }
    report = unanchored_entity_reviewer().review(artifact, package)

    assert report.axis == "evaluative" and report.gating is False
    flagged = {f.message.split("'")[1] for f in report.findings
               if f.check == "unanchored-entity" and f.severity == "warning"}
    # the invented faction is flagged...
    assert any("Severed Chain" in name for name in flagged), flagged
    # ...while known canonical names (Vael Ardyn / Maesa Korrin) are NOT flagged
    assert not any("Vael" in name or "Maesa" in name for name in flagged), flagged


def test_unanchored_entity_reviewer_clean_when_all_anchored(env):
    """A draft naming only known facts yields an info note, no warnings."""
    from runtime.execution.draft_review import unanchored_entity_reviewer

    project, package = env
    artifact = {"body": "Vael Ardyn trained under Maesa Korrin for two years."}
    report = unanchored_entity_reviewer().review(artifact, package)

    warnings = [f for f in report.findings if f.severity == "warning"]
    assert warnings == []
    assert any(f.severity == "info" for f in report.findings)
