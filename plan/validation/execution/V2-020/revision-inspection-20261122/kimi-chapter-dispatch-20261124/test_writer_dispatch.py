"""Offline tests for the chapter-specific authorization and Writer composition."""

import importlib
import json
import socket
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest

from anovel.canon.identity import canonical_bytes
from anovel.gateway.models import (
    KIMI_CHAT_ENDPOINT,
    KIMI_CONTEXT_WINDOW,
    KIMI_MODEL,
    OPENAI_RESPONSES_ENDPOINT,
    BudgetLimit,
    ModelPolicy,
)
from anovel.gateway.provider import KimiChatCompletionsAdapter, OpenAIResponsesAdapter
from anovel.workflow import __main__ as workflow_cli
from anovel.workflow.chapter import ChapterWorkflow, DraftChapterBrief
from anovel.workflow.gateway_binding import read_provider_writer_receipt

ROOT = Path(__file__).resolve().parents[6]
_SYNTHETIC_TEXT = "单章派发离线验证标记。"


def _forbidden(*_args, **_kwargs):
    raise AssertionError("Protected Writer tests must remain offline")


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(socket, "create_connection", _forbidden)
    monkeypatch.setattr(socket.socket, "connect", _forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", _forbidden)
    monkeypatch.setattr(KimiChatCompletionsAdapter, "_post", _forbidden)
    monkeypatch.setattr(OpenAIResponsesAdapter, "_post", _forbidden)


@pytest.fixture
def modules(monkeypatch):
    for directory in ("scripts", "plan/scripts", "tests/contract"):
        monkeypatch.syspath_prepend(str(ROOT / directory))
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parent))
    return (
        importlib.import_module("run_chapter"),
        importlib.import_module("writer_authorization"),
    )


def _private_file(path, raw):
    with path.open("xb") as stream:
        path.chmod(0o600)
        stream.write(raw)
    return path


def _revised_writer_source(seed, observation, scope, private):
    from test_v2_020_scene_generation import start_child

    from anovel.context.scene import SceneDeltaBinding, SceneSpan

    env, current = seed.env, seed.case.frozen

    def save_revision(observed, version, previous_hash):
        return env.workflow.save_observed_chapter_revision(
            current,
            **scope,
            step_id=observed.assembly.child.step_id,
            expected_observation_hash=observed.record_hash,
            version=version,
            request_id=f"writer-rewrite-source-{version}",
            expected_revision_hash=previous_hash,
        )

    first = save_revision(observation, 1, None)
    writer = ChapterWorkflow(
        env.store, next_chapter_writer=lambda _packet: "第一版下游验证草稿。".encode()
    )
    old_selection = scope | {"expected_revision_hash": first.record_hash}
    handoff = writer.next_chapter_draft_input(current, **old_selection)
    draft = writer.write_next_chapter_draft(
        current,
        **old_selection,
        retained_payload=handoff.payload_bytes(),
        output=private / "old-draft.json",
    )
    old_target = writer.save_next_chapter_draft(
        current, draft_payload=draft.payload_bytes(), **old_selection
    )

    revised_choice = "改稿后，许甲决定先暂停交付。"
    parent = env.workflow.replace_draft(
        current,
        **scope,
        expected_revision=seed.source.revision,
        expected_prose_hash=seed.source.prose_hash,
        prose=revised_choice.encode(),
    )
    ending = SceneSpan(0, len(revised_choice), revised_choice)
    projection = env.workflow.project_scene(
        current,
        **scope,
        expected_record_hash=parent.record_hash,
        source_scene_id=parent.contract.scenes[0].id,
        target_scene_id=parent.contract.scenes[1].id,
        source_span=ending,
        ending_span=ending,
        delta_binding=SceneDeltaBinding(None, "authorized-writer-rewrite-fixture"),
    )
    env.adapter.output = {"text": "balance变为45。"}
    child = start_child(
        env, seed.case, projection, attempt_id="writer-rewrite-source-child"
    )
    observed = env.workflow.extract_chapter(current, **scope, step_id=child.step_id)
    revised = save_revision(observed, 2, first.record_hash)
    return revised, old_target


@pytest.fixture
def writer_inputs(tmp_path, modules, request):
    from test_v2_017 import BRANCH, PROJECT
    from test_v2_020 import RUN
    from test_v2_021 import make_extraction_seed

    tmp_path = tmp_path.resolve()
    private = tmp_path / "writer"
    private.mkdir(mode=0o700)
    seed = make_extraction_seed(private, False)
    env, current = seed.env, seed.case.frozen
    scope = {"project": PROJECT, "branch": BRANCH, "run_id": RUN}
    observation = env.workflow.extract_chapter(
        current, **scope, step_id=seed.child.step_id
    )
    rewrite = request.param == "OPENAI-REWRITE"
    provider = "OPENAI" if rewrite else request.param
    old_target = None
    step = seed.child.step_id
    source = observation
    if rewrite:
        source, old_target = _revised_writer_source(seed, observation, scope, private)
        step = None
    selection = scope | {"expected_revision_hash": source.record_hash}
    reader = ChapterWorkflow(env.store, draft_handoff_step_id=step)
    handoff = reader.next_chapter_draft_input(current, **selection)
    brief = DraftChapterBrief.from_dict(
        {
            "record_type": "draft_chapter_brief",
            "schema_version": "1.0",
            "artifact_state": "DRAFT",
            "project": PROJECT,
            "branch": BRANCH,
            "source_chapter_id": handoff.source.chapter_id.to_dict(),
            "target_chapter_id": handoff.target.id.to_dict(),
            "source_prose_hash": handoff.to_dict()["source_prose_hash"],
            "story_title": "派发验证夹具",
            "setting": "合成校园场景",
            "arc_goal": "交付试片",
            "character_motives": ["许甲要找到有说服力的素材。"],
            "chapter_title": "失去机位",
            "chapter_goal": "让人物选择影响可用素材。",
            "opening": "承接前章账单。",
            "causal_beats": ["许甲选择等采访，采访被拒后失去备选机位。"],
            "constraints": ["只覆盖当前章。"],
        }
    )
    now = datetime.now(UTC)
    kimi = provider == "KIMI"
    policy = ModelPolicy(
        f"synthetic-{provider.lower()}-dispatch-policy",
        KIMI_MODEL if kimi else "gpt-6.2-sol",
        KIMI_CHAT_ENDPOINT if kimi else OPENAI_RESPONSES_ENDPOINT,
        KIMI_CONTEXT_WINDOW if kimi else 32_768,
        1024,
        1,
        1,
        "synthetic-local-policy",
        (now + timedelta(minutes=10)).isoformat(),
        timeout_seconds=1,
        params_bytes=canonical_bytes(
            {"reasoning_effort": "high"}
            if kimi
            else {"reasoning": {"effort": "medium"}}
        ),
    )
    request_path = private / "request.json"
    request = reader.prepare_next_chapter_model_request(
        current,
        **selection,
        retained_payload=handoff.payload_bytes(),
        brief=brief,
        policy=policy,
        output=request_path,
        expected_target_revision_hash=old_target.record_hash if old_target else None,
    )
    budget = BudgetLimit(
        PROJECT,
        BRANCH,
        RUN,
        10_000,
        1,
        (datetime.now(UTC) + timedelta(seconds=110)).isoformat(),
        1,
        1,
    )
    return SimpleNamespace(
        **selection,
        provider=provider,
        env=env,
        current=current,
        brief=brief,
        handoff=handoff,
        step=step,
        old_target=old_target,
        request=request,
        budget=budget,
        policy=policy,
        private=private,
        request_path=request_path,
        input_path=_private_file(private / "current.json", current.payload),
        handoff_path=_private_file(private / "handoff.json", handoff.payload_bytes()),
        brief_path=_private_file(private / "brief.json", brief.payload),
        budget_path=_private_file(private / "budget.json", budget.to_bytes()),
        ledger=private / "writer.sqlite",
        output=private / "draft.json",
        claim=private / "dispatch-claim.json",
        attempt=request.logical_id + "-attempt-1",
    )


def _fake_kimi(monkeypatch):
    posts = []
    count_url = KIMI_CHAT_ENDPOINT.removesuffix("/v1/chat/completions") + (
        "/v1/tokenizers/estimate-token-count"
    )
    reply = canonical_bytes(
        {
            "id": "synthetic-kimi-draft-body",
            "object": "chat.completion",
            "model": KIMI_MODEL,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": canonical_bytes({"text": _SYNTHETIC_TEXT}).decode(),
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 30, "completion_tokens": 15, "total_tokens": 45},
        }
    )

    def post(_adapter, url, body, _timeout):
        posts.append((url, json.loads(body)))
        if url == count_url:
            return 200, canonical_bytes({"data": {"total_tokens": 30}}), "count-marker"
        assert url == KIMI_CHAT_ENDPOINT
        return 200, reply, "generation-marker"

    monkeypatch.setattr(KimiChatCompletionsAdapter, "_post", post)
    return posts, sha256(reply).hexdigest()


def _fake_openai(monkeypatch, model):
    posts = []
    reply = canonical_bytes(
        {
            "id": "synthetic-openai-draft-body",
            "object": "response",
            "model": model,
            "status": "completed",
            "service_tier": "default",
            "output": [
                {"type": "reasoning"},
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [
                        {
                            "type": "output_text",
                            "text": canonical_bytes({"text": _SYNTHETIC_TEXT}).decode(),
                        }
                    ],
                },
            ],
            "usage": {"input_tokens": 30, "output_tokens": 15, "total_tokens": 45},
        }
    )

    def post(_adapter, url, body, _timeout):
        posts.append((url, json.loads(body)))
        if url == OPENAI_RESPONSES_ENDPOINT + "/input_tokens":
            return (
                200,
                canonical_bytes(
                    {"object": "response.input_tokens", "input_tokens": 30}
                ),
                "count-marker",
            )
        assert url == OPENAI_RESPONSES_ENDPOINT
        return 200, reply, "generation-marker"

    monkeypatch.setattr(OpenAIResponsesAdapter, "_post", post)
    return posts, sha256(reply).hexdigest()


def _fixture_approval(
    inputs, *, expected_target_revision_hash=None, name="fixture-repository"
):
    root = inputs.private.parent / name
    plan = root / "plan"
    evidence = plan / "validation/execution/V2-020"
    evidence.mkdir(parents=True)

    def write_ref(name, payload):
        path = _private_file(evidence / name, payload)
        return {
            "ref": str(path.relative_to(plan)),
            "sha256": sha256(payload).hexdigest(),
        }

    owner = write_ref("synthetic-owner.txt", b"Fixture only. No live approval.\n")
    zero = write_ref("synthetic-estimate.txt", b"Fixture only. HTTP is intercepted.\n")
    files = (
        inputs.env.store_path,
        inputs.input_path,
        inputs.handoff_path,
        inputs.brief_path,
        inputs.request_path,
        inputs.budget_path,
    )
    target = (
        {"expected_target_revision_hash": expected_target_revision_hash}
        if expected_target_revision_hash is not None
        else {}
    )
    grant = write_ref(
        "synthetic-grant.json",
        canonical_bytes(
            {
                "record_type": f"v2_020_{inputs.provider.lower()}_draft_authorization",
                "schema_version": "1.0",
                "task_id": "V2-020",
                "action": "LIVE_CALL",
                "artifact_state": "DRAFT",
                "job_dir": str(inputs.private),
                "input_sha256": {
                    p.name: sha256(p.read_bytes()).hexdigest() for p in files
                },
                "owner_approval_sha256": owner["sha256"],
                "root_step_id": inputs.step,
                **target,
            }
        ),
    )
    return root, {
        "task_id": "V2-020",
        "action": "LIVE_CALL",
        "budget": {
            "paid_calls_allowed": True,
            "maximum_attempts": 1,
            "maximum_runtime": 120,
            "model_cost_cap": 0.01,
        },
        "claims": [
            {
                "id": f"V2_020_{inputs.provider}_DRAFT_GRANT",
                "kind": "FACT",
                "sources": [owner, grant],
            },
            *(
                [
                    {
                        "id": "V2_020_KIMI_ESTIMATE_ZERO_COST",
                        "kind": "FACT",
                        "sources": [zero],
                    }
                ]
                if inputs.provider == "KIMI"
                else []
            ),
        ],
    }


@pytest.mark.parametrize("provider", ["KIMI", "OPENAI"])
def test_current_repository_blocks_chapter_dispatch_before_credentials(
    modules, monkeypatch, capsys, provider
):
    runner, _authorization = modules
    monkeypatch.setattr(runner, "read_hidden_credential", _forbidden)
    monkeypatch.setattr(runner, "read_openai_credential", _forbidden)
    monkeypatch.setattr(runner, "run_job", _forbidden)
    for argv in ([], ["--execute-live"]):
        assert runner.main(argv, provider=provider) == 2
        assert (
            f"{provider}_CHAPTER_LIVE_ACTION_NOT_AUTHORIZED" in capsys.readouterr().out
        )


@pytest.mark.parametrize("writer_inputs", ["KIMI", "OPENAI"], indirect=True)
def test_bound_chapter_is_claimed_before_credentials_and_never_sent_twice(
    modules, writer_inputs, monkeypatch, capsys
):
    runner, authorization = modules
    inputs = writer_inputs
    provider = inputs.provider
    kimi = provider == "KIMI"
    root, packet = _fixture_approval(inputs)
    with pytest.raises(ValueError):
        authorization.validate_job(root, packet, provider="OPENAI" if kimi else "KIMI")
    if kimi:
        with pytest.raises(ValueError):
            authorization.validate_job(root, packet | {"claims": packet["claims"][:1]})
    job = authorization.validate_job(root, packet, provider=provider)
    posts, raw_hash = (
        _fake_kimi(monkeypatch)
        if kimi
        else _fake_openai(monkeypatch, inputs.policy.model)
    )
    checks, credentials = [], []

    def revalidate():
        checks.append(True)
        assert authorization.validate_job(root, packet, provider=provider) == job

    def credential(**_kwargs):
        assert checks and job.claim.is_file()
        assert job.claim.stat().st_mode & 0o777 == 0o600
        assert not posts
        credentials.append(True)
        return "synthetic-credential-for-local-chapter-test"

    env_path = inputs.private / ".env"
    if kimi:
        monkeypatch.setattr(runner, "read_hidden_credential", credential)
    else:
        original_read = runner.read_openai_credential
        public = (
            b"OPENAI_BASE_URL=https://api.openai.com/v1/\nOPENAI_MODEL=gpt-6.2-sol\n"
        )
        key = "sk-" + "fixture-local-only"
        raw_env = public + f"OPENAI_API_KEY={key}\n".encode()
        _private_file(env_path, raw_env.replace(b"gpt-6.2-sol", b"wrong-model"))
        with pytest.raises(ValueError, match="OPENAI_ENV_POLICY_MISMATCH"):
            runner.run_job(job, revalidate, env_path=env_path)
        assert not job.claim.exists() and not posts
        env_path.write_bytes(raw_env)

        def read_openai(path, policy):
            credential()
            assert path == env_path and policy == inputs.policy
            assert original_read(path, policy) == key
            return key

        monkeypatch.setattr(runner, "read_openai_credential", read_openai)
        monkeypatch.setattr(runner, "read_hidden_credential", _forbidden)
    stale = replace(job, request=replace(job.request, instructions="stale input"))
    with pytest.raises(ValueError, match=f"{provider}_DRAFT_REQUEST_CHANGED"):
        runner.run_job(stale, revalidate, env_path=env_path)
    assert not credentials and not posts
    assert (
        not job.claim.exists() and not job.ledger.exists() and not job.output.exists()
    )

    result = runner.run_job(job, revalidate, env_path=env_path)
    assert result.prose.decode() == _SYNTHETIC_TEXT
    assert job.output.read_bytes() == result.payload_bytes()
    assert json.loads(job.output.read_bytes())["artifact_state"] == "DRAFT"
    assert (
        inputs.env.store.load_written_draft(
            project=inputs.project,
            branch=inputs.branch,
            chapter_id=inputs.handoff.target.id,
        ).prose
        == result.prose
    )
    receipt = read_provider_writer_receipt(
        job.ledger, job.request, inputs.attempt, provider
    )
    assert receipt is not None
    assert receipt.request_hash == job.request.semantic_hash
    assert receipt.reply.response_hash == raw_hash
    assert len(posts) == 2 and len(credentials) == 1
    input_key = "messages" if kimi else "input"
    assert posts[0][1][input_key] == posts[1][1][input_key]
    if kimi:
        assert (
            posts[-1][1][input_key][-1]["content"]
            == job.request.context.model_bytes.decode()
        )
    else:
        payload = posts[-1][1]
        assert payload["model"] == inputs.policy.model
        assert payload["text"]["format"]["strict"] is True
        assert (
            payload["input"][0]["content"][0]["text"]
            == job.request.context.model_bytes.decode()
        )

    original = {p: p.read_bytes() for p in (job.claim, job.ledger, job.output)}
    with pytest.raises(ValueError, match=f"{provider}_CHAPTER_ALREADY_ATTEMPTED"):
        runner.run_job(job, revalidate, env_path=env_path)
    assert {p: p.read_bytes() for p in original} == original
    assert len(posts) == 2 and len(credentials) == 1

    if not kimi:
        env_path.unlink()
        cli_scope = [
            "--db",
            str(job.workflow_db),
            "--project",
            inputs.project,
            "--branch",
            inputs.branch,
            "--run-id",
            inputs.run_id,
            "--draft-handoff-step-id",
            inputs.step,
        ]
        recover = cli_scope + [
            "recover-next-chapter-openai",
            "--input",
            str(inputs.input_path),
            "--expected-revision-hash",
            inputs.expected_revision_hash,
            "--handoff",
            str(inputs.handoff_path),
            "--brief",
            str(inputs.brief_path),
            "--request",
            str(inputs.request_path),
            "--writer-ledger",
            str(job.ledger),
        ]
        recovered = inputs.private / "recovered.json"
        assert workflow_cli.main(recover + ["--output", str(recovered)]) == 0
        assert json.loads(capsys.readouterr().out)["artifact_state"] == "DRAFT"
        assert recovered.read_bytes() == result.payload_bytes()

        draft_scope = {
            "project": inputs.project,
            "branch": inputs.branch,
            "chapter_id": inputs.handoff.target.id,
        }
        first = inputs.env.store.load_written_draft(**draft_scope)
        edited_prose = _SYNTHETIC_TEXT + "\n\n编辑补记。"
        edited_path = inputs.private / "edited.txt"
        edited_path.write_text(edited_prose, encoding="utf-8")
        assert (
            workflow_cli.main(
                cli_scope
                + [
                    "edit-written-draft",
                    "--input",
                    str(inputs.input_path),
                    "--chapter-id",
                    first.chapter_id.local_id,
                    "--expected-revision-hash",
                    first.record_hash,
                    "--prose",
                    str(edited_path),
                ]
            )
            == 0
        )
        capsys.readouterr()
        edited = inputs.env.store.load_written_draft(**draft_scope)
        assert edited.version == 2 and edited.prose == edited_prose.encode()
        edited_database = job.workflow_db.read_bytes()

        recovered_after_edit = inputs.private / "recovered-after-edit.json"
        assert workflow_cli.main(recover + ["--output", str(recovered_after_edit)]) == 0
        assert recovered_after_edit.read_bytes() == recovered.read_bytes()
        assert job.workflow_db.read_bytes() == edited_database
        assert inputs.env.store.load_written_draft(**draft_scope) == edited
        assert inputs.env.store.load_written_draft(**draft_scope, version=1) == first
        assert job.ledger.read_bytes() == original[job.ledger]
        assert len(posts) == 2 and len(credentials) == 1


@pytest.mark.parametrize("writer_inputs", ["OPENAI-REWRITE"], indirect=True)
def test_bound_openai_rewrite_claims_only_the_selected_target_and_recovers(
    modules, writer_inputs, monkeypatch, capsys
):
    runner, authorization = modules
    inputs = writer_inputs
    old_target = inputs.old_target
    assert inputs.handoff.source.record_hash != old_target.source_revision_hash
    root, packet = _fixture_approval(
        inputs, expected_target_revision_hash=old_target.record_hash
    )
    rejected_root, rejected_packet = _fixture_approval(
        inputs, expected_target_revision_hash="0" * 64, name="wrong-target-repository"
    )
    packets = {root: packet, rejected_root: rejected_packet}
    for directory in packets:
        _private_file(
            directory / ".env",
            b"OPENAI_BASE_URL=https://api.openai.com/v1/\n"
            b"OPENAI_MODEL=gpt-6.2-sol\nOPENAI_API_KEY=sk-fixture-local-only\n",
        )
    job = authorization.validate_job(root, packet, provider="OPENAI")
    assert job.expected_target_revision_hash == old_target.record_hash
    posts, response_hash = _fake_openai(monkeypatch, inputs.policy.model)
    credentials = []
    original_read = runner.read_openai_credential

    def checked_job(directory, *, own_claim=None, provider):
        # The test supplies its synthetic task packet. The real packet parser,
        # per-job claim, protected Writer, and Draft persistence still run.
        checked = authorization.validate_job(
            directory, packets[directory], provider=provider
        )
        assert own_claim == (checked.claim if checked.claim.is_file() else None)
        return checked, {"fixture": str(directory)}

    def credential(path, policy):
        assert path == root / ".env" and policy == inputs.policy
        assert job.claim.is_file() and not posts
        credentials.append(True)
        return original_read(path, policy)

    monkeypatch.setattr(runner, "_checked_job", checked_job)
    monkeypatch.setattr(runner, "read_openai_credential", credential)
    monkeypatch.setattr(runner, "ROOT", rejected_root)
    before = job.workflow_db.read_bytes()
    assert runner.main(["--execute-live"], provider="OPENAI") == 2
    assert (
        json.loads(capsys.readouterr().out)["code"] == "WRITTEN_DRAFT_REVISION_CONFLICT"
    )
    assert not any(path.exists() for path in (job.claim, job.ledger, job.output))
    assert not posts and not credentials and job.workflow_db.read_bytes() == before

    monkeypatch.setattr(runner, "ROOT", root)
    scope = {
        "project": inputs.project,
        "branch": inputs.branch,
        "chapter_id": old_target.chapter_id,
    }

    def interrupt_save(_store, candidate, *, rewrite=False):
        assert rewrite and candidate.previous_revision_hash == old_target.record_hash
        raise KeyboardInterrupt

    with monkeypatch.context() as interrupted:
        interrupted.setattr(
            type(inputs.env.store), "append_written_draft", interrupt_save
        )
        assert runner.main(["--execute-live"], provider="OPENAI") == 130
    assert json.loads(capsys.readouterr().out) == {
        "status": "INTERRUPTED",
        "automatic_retry": False,
    }
    assert inputs.env.store.load_written_draft(**scope) == old_target
    assert job.claim.is_file() and not job.output.exists()
    receipt = read_provider_writer_receipt(
        job.ledger, job.request, inputs.attempt, "OPENAI"
    )
    assert receipt is not None and receipt.status == "SUCCESS"
    assert receipt.reply.response_hash == response_hash
    assert [url for url, _body in posts] == [
        OPENAI_RESPONSES_ENDPOINT + "/input_tokens",
        OPENAI_RESPONSES_ENDPOINT,
    ]
    model_text = posts[1][1]["input"][0]["content"][0]["text"]
    assert model_text == job.request.context.model_bytes.decode()
    assert "许甲决定先暂停交付" in model_text and "balance变为45。" in model_text
    assert credentials == [True]

    (root / ".env").unlink()
    original = job.ledger.read_bytes()
    recovered = inputs.private / "recovered-rewrite.json"
    assert (
        workflow_cli.main(
            [
                "--db",
                str(job.workflow_db),
                "--project",
                inputs.project,
                "--branch",
                inputs.branch,
                "--run-id",
                inputs.run_id,
                "recover-next-chapter-openai",
                "--input",
                str(inputs.input_path),
                "--expected-revision-hash",
                inputs.expected_revision_hash,
                "--expected-target-revision-hash",
                old_target.record_hash,
                "--handoff",
                str(inputs.handoff_path),
                "--brief",
                str(inputs.brief_path),
                "--request",
                str(inputs.request_path),
                "--writer-ledger",
                str(job.ledger),
                "--output",
                str(recovered),
            ]
        )
        == 0
    )
    summary = json.loads(capsys.readouterr().out)
    rewritten = inputs.env.store.load_written_draft(**scope)
    assert (
        summary["artifact_state"] == "DRAFT"
        and summary["revision_hash"] == rewritten.record_hash
    )
    assert rewritten.version == 2 and rewritten.prose.decode() == _SYNTHETIC_TEXT
    assert rewritten.previous_revision_hash == old_target.record_hash
    assert rewritten.source_revision_hash == inputs.handoff.source.record_hash
    assert inputs.env.store.load_written_draft(**scope, version=1) == old_target
    assert recovered.read_bytes() == rewritten.payload_bytes()
    assert job.ledger.read_bytes() == original
    assert len(posts) == 2 and credentials == [True]
