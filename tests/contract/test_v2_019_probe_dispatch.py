"""Synthetic frozen-authority probes against local HTTP and disposable Git.

These tests never read API-key environment variables or contact a Provider. The
fixture approval and cost evidence apply only to the loopback server.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import socket
import sqlite3
import subprocess
import sys
from contextlib import closing, contextmanager
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import unquote, urlsplit

import pytest
import yaml

from anovel.canon.identity import canonical_bytes
from anovel.context.models import (
    ContextArtifact,
    ContextBudget,
    ContextItem,
    ContextRequest,
    ContextRole,
)
from anovel.gateway.ledger import BudgetLedger
from anovel.gateway.models import (
    KIMI_CHAT_PATH,
    KIMI_MODEL,
    BudgetLimit,
    GatewayRequest,
    ModelPolicy,
)

ROOT = Path(__file__).resolve().parents[2]
PACKET = "plan/validation/execution/V2-019/execution-packet.yaml"
RECORDS = "plan/validation/execution/V2-019/synthetic-dispatch-fixture"
SYNTHETIC_CREDENTIAL = "not-a-key"
SYNTHETIC_RATE_LIMIT_MESSAGE = "Private loopback error detail."
SCHEMA = canonical_bytes(
    {
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
        "additionalProperties": False,
    }
)


def clean_environment(repo):
    # Deliberately construct an environment instead of inspecting ambient keys.
    return {
        "PATH": os.defpath,
        "PYTHONPATH": str(repo / "src"),
        "PYTHONDONTWRITEBYTECODE": "1",
    }


def call(repo, *command, check=False):
    return subprocess.run(
        command,
        cwd=repo,
        env=clean_environment(repo),
        capture_output=True,
        text=True,
        timeout=150,
        # A pipe alone does not detach an inherited controlling terminal.
        start_new_session=True,
        check=check,
    )


def git(repo, *args):
    return call(repo, "git", *args, check=True).stdout.strip()


def commit(repo, message):
    git(repo, "add", ".")
    git(
        repo,
        "-c",
        "user.name=Synthetic Probe Fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "commit",
        "-qm",
        message,
    )
    return git(repo, "rev-parse", "HEAD")


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def save_packet(repo, packet):
    (repo / PACKET).write_text(
        yaml.safe_dump(packet, allow_unicode=True, sort_keys=False)
    )


def reconcile_fixture(repo):
    # Synthetic source/context reconciliation, never production evidence.
    code = """
import hashlib,json,sys
from pathlib import Path
import yaml
sys.path.insert(0,'plan/scripts')
import validate_plan as validator
plan=Path('plan')
data=validator.load()
# Recreate the point just before the first P5 probe in this independent Git
# history. Later packets, grants, and closure receipts belong to the checkout
# they came from. Keep their task contracts and the verified upstream inputs.
tasks = data['implementation-backlog']['tasks']
gateway = next(task for task in tasks if task['task_id'] == 'V2-019')
phases = data['phase-gates']['phases']
probe_index = next(i for i, phase in enumerate(phases) if phase['id'] == gateway['phase'])
downstream_phases = {phase['id'] for phase in phases[probe_index + 1:]}
downstream = {task['task_id'] for task in tasks if task['phase'] in downstream_phases}
reopened = downstream | {gateway['task_id']}
for task in tasks:
    if task['task_id'] in reopened:
        task['evidence'] = {kind: [] for kind in task['evidence']}
    if task['task_id'] in downstream:
        task.update(status='OPEN', readiness='PLANNED', execution_packet_ref=None)
        task.pop('implementation_admission', None)
gateway.update(status='IN_PROGRESS', readiness='READY_TO_START')
for suite in data['test-catalog']['suites']:
    if suite['task_id'] in reopened:
        suite.update(status='PLANNED', execution_evidence=[])
for phase in phases[probe_index:]:
    phase.update(status='NOT_VERIFIED', evidence_refs=[])
for milestone in data['milestones']['milestones']:
    if reopened.intersection(milestone['required_tasks']):
        milestone.update(status='NOT_VERIFIED', evidence_refs=[])
for finding in data['remediation-register']['findings']:
    if finding['closure_refs'] and reopened.intersection(finding['related_tasks']):
        finding.update(status='OPEN_TRACKED', closure_refs=[])
for practice in data['external-practice-register']['practices']:
    if practice['status'] == 'VERIFIED' and reopened.intersection(practice['related_tasks']):
        practice.update(status='PLANNED', verification_refs=[])
for name in ('implementation-backlog', 'test-catalog', 'phase-gates', 'milestones',
             'remediation-register', 'external-practice-register'):
    (plan / 'machine' / (name + '.yaml')).write_text(
        yaml.safe_dump(data[name], allow_unicode=True, sort_keys=False)
    )
for ref,text in validator.expected_views(data).items():
    (plan/ref).write_text(text)
(plan/'FILE_MANIFEST.json').write_text(json.dumps(validator.build_manifest(),ensure_ascii=False,indent=2)+'\\n')
manifest_hash=hashlib.sha256((plan/'FILE_MANIFEST.json').read_bytes()).hexdigest()
for task in data['implementation-backlog']['tasks']:
    if task['status'] not in {'OPEN','IN_PROGRESS','IMPLEMENTED'} or not task.get('execution_packet_ref'):
        continue
    path=plan/task['execution_packet_ref']
    packet=yaml.safe_load(path.read_text())
    packet['plan_manifest_sha256']=manifest_hash
    for item in packet['inputs']:
        raw=(plan/item['source_ref']).read_bytes()
        digest=hashlib.sha256(raw).hexdigest()
        destination=plan/'validation/synthetic-current-inputs'/task['task_id']/(digest+'.txt')
        destination.parent.mkdir(parents=True,exist_ok=True)
        destination.write_bytes(raw)
        item.update(ref=str(destination.relative_to(plan)),sha256=digest)
    path.write_text(yaml.safe_dump(packet,allow_unicode=True,sort_keys=False))
"""
    call(repo, sys.executable, "-B", "-c", code, check=True)


def copy_linked_replay_inputs(repo):
    """Preserve external assets the current planning check reads in this fixture."""
    files = set()
    for document in (repo / "plan").rglob("*.md"):
        if "archive" in document.relative_to(repo / "plan").parts:
            continue
        for reference in re.findall(r"\]\(([^)]+)\)", document.read_text()):
            if reference.startswith("#") or urlsplit(reference).scheme:
                continue
            target = (document.parent / unquote(reference.split("#")[0])).resolve()
            if target.exists() or not (
                target.is_relative_to(repo / "drafts")
                or target.is_relative_to(repo / "dist/recovery")
            ):
                continue
            relative = target.relative_to(repo)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, target)
            files.add(str(relative))
    return sorted(files)


@pytest.fixture(scope="module")
def seed(tmp_path_factory):
    """A real source checkout; no caller/context validation is mocked."""
    repo = tmp_path_factory.mktemp("synthetic-probe-seed").resolve()
    for name in ("plan", "scripts", "src", "specs", "tests", ".github"):
        shutil.copytree(
            ROOT / name,
            repo / name,
            ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"),
        )
    for name in (
        ".gitignore",
        ".python-version",
        "pyproject.toml",
        "uv.lock",
        "README.md",
        "AGENTS.md",
        "compose.yaml",
        "alembic.ini",
        "model-policy.yaml",
        ".gitleaks.toml",
        ".gitlab-ci.yml",
    ):
        source = ROOT / name
        if source.is_file():
            shutil.copyfile(source, repo / name)
    git(repo, "init", "-b", "main")
    reconcile_fixture(repo)
    replay_inputs = copy_linked_replay_inputs(repo)
    # Preserve ignored-but-tracked historical plan artifacts in the clone too.
    git(
        repo,
        "add",
        "-f",
        "plan",
        "scripts",
        "src",
        "specs",
        "tests",
        ".github",
        *replay_inputs,
    )
    commit(repo, "synthetic source fixture; no Provider or Owner evidence")
    return repo


class LocalProbe:
    def __init__(self, mode="success"):
        self.mode = mode
        self.requests = []
        self.headers = []
        self.responses = []


@contextmanager
def local_server(mode="success", *, kimi=False, openai_probe=False):
    state = LocalProbe(mode)
    count_path = (
        "/v1/tokenizers/estimate-token-count" if kimi else "/v1/responses/input_tokens"
    )

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_POST(self):
            raw = self.rfile.read(int(self.headers["Content-Length"]))
            state.requests.append((self.path, json.loads(raw)))
            state.headers.append(dict(self.headers))
            is_count = self.path == count_path
            if not is_count and state.mode == "disconnect":
                self.connection.shutdown(socket.SHUT_RDWR)
                self.connection.close()
                return
            status = 403 if is_count and state.mode == "count_denied" else 200
            if is_count:
                body = (
                    {"data": {"total_tokens": 30}}
                    if kimi
                    else {"object": "response.input_tokens", "input_tokens": 30}
                )
            elif state.mode == "http_429":
                status = 429
                body = {"error": {"message": SYNTHETIC_RATE_LIMIT_MESSAGE}}
            elif kimi:
                body = {
                    "id": "synthetic-kimi-completion",
                    "object": "chat.completion",
                    "model": KIMI_MODEL,
                    "choices": [
                        {
                            "index": 0,
                            "finish_reason": "stop",
                            "message": {
                                "role": "assistant",
                                "content": '{"text":"Synthetic Kimi loopback only."}',
                            },
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 30,
                        "completion_tokens": 10,
                        "total_tokens": 40,
                    },
                }
            else:
                body = {
                    "status": "completed",
                    "model": "gpt-6.2-sol" if openai_probe else "gpt-6-luna",
                    "service_tier": "default",
                    "output": [
                        {
                            "type": "message",
                            "role": "assistant",
                            "content": [
                                {
                                    "type": "output_text",
                                    "text": '{"text":"ANovelOS OpenAI probe OK"}'
                                    if openai_probe and mode == "success"
                                    else '{"text":"Synthetic local HTTP only."}',
                                }
                            ],
                        }
                    ],
                    "usage": {
                        "input_tokens": 30,
                        "output_tokens": 10,
                        "total_tokens": 40,
                    },
                }
            if not is_count and state.mode == "missing_usage":
                body.pop("usage")
            encoded = canonical_bytes(body)
            state.responses.append(encoded)
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header(
                "x-request-id",
                "synthetic-count" if is_count else "synthetic-generation",
            )
            self.end_headers()
            self.wfile.write(encoded)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    path = KIMI_CHAT_PATH if kimi else "/v1/responses"
    state.endpoint = f"http://127.0.0.1:{server.server_port}{path}"
    try:
        yield state
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def make_request(endpoint, *, openai_probe=False):
    kimi = endpoint.endswith(KIMI_CHAT_PATH)
    context_budget = ContextBudget(100000)
    identity = ContextRequest(
        "synthetic-probe-project",
        "main",
        "sha256:" + "a" * 64,
        "b" * 64,
        ContextRole.WRITER,
        context_budget,
    )
    content = canonical_bytes({"fact": "Synthetic local fixture; no novel Canon."})
    item = ContextItem(
        "fact-1",
        "FACT",
        content,
        "synthetic:probe-fixture",
        sha256(content).hexdigest(),
        True,
        "required",
    )
    context = ContextArtifact(
        identity.project,
        identity.branch,
        identity.parent_ref,
        identity.contract_hash,
        "c" * 64,
        "d" * 64,
        ContextRole.WRITER,
        None,
        None,
        "e" * 64,
        identity.content_hash,
        (item,),
        (),
        context_budget,
    )
    policy = ModelPolicy(
        "synthetic-probe-policy",
        KIMI_MODEL if kimi else "gpt-6-luna",
        endpoint,
        16384,
        1024,
        250000,
        500000,
        "https://example.invalid/synthetic-count-fixture",
        "2099-01-01T00:00:00Z",
        timeout_seconds=2,
        params_bytes=canonical_bytes({"reasoning_effort": "high"} if kimi else {}),
        margin_microusd=1000,
        test_mode=True,
    )
    if openai_probe:
        context = replace(context, items=())
        policy = replace(
            policy,
            model="gpt-6.2-sol",
            accepted_models=("gpt-6.2-sol",),
            params_bytes=canonical_bytes({"reasoning": {"effort": "low"}}),
        )
    return GatewayRequest(
        context.project,
        context.branch,
        "synthetic-probe-run",
        "synthetic-probe-logical",
        context,
        'Return exactly this JSON object: {"text":"ANovelOS OpenAI probe OK"}.'
        if openai_probe
        else "Synthetic local protocol probe only.",
        "gateway-openai-first-generation-v1"
        if openai_probe
        else "gateway-protocol-probe-v1",
        SCHEMA,
        (policy,),
    )


@dataclass
class Fixture:
    repo: Path
    private: Path
    request: GatewayRequest
    budget: BudgetLimit
    grant: dict
    grant_ref: str
    binding: dict

    @property
    def arguments(self):
        return {
            "request_path": str(self.private / "request.json"),
            "budget_path": str(self.private / "budget.json"),
            "policy_path": str(self.private / "policy.json"),
            "ledger": str(self.private / "ledger.sqlite3"),
            "output": str(self.private / "result.json"),
            "policy_id": self.request.policies[0].id,
            "attempt_id": "synthetic-probe-attempt",
        }

    def freeze_grant(self):
        write_json(self.repo / self.grant_ref, self.grant)
        revision = commit(self.repo, "freeze exact synthetic probe grant")
        packet = yaml.safe_load((self.repo / PACKET).read_text())
        packet["probe_authorization"] = {
            "revision": revision,
            "ref": self.grant_ref,
            "sha256": sha256((self.repo / self.grant_ref).read_bytes()).hexdigest(),
        }
        save_packet(self.repo, packet)
        commit(self.repo, "bind synthetic grant; not production authorization")

    def validate(self, *, prefix=""):
        code = (
            "import json,sys;from pathlib import Path;"
            "sys.path.insert(0,str(Path.cwd()/'plan/scripts'));"
            + prefix
            + "from probe_dispatch import validate_probe;"
            "a=json.loads(sys.argv[1]);"
            "a={k:(Path(v) if k not in ('policy_id','attempt_id') else v) for k,v in a.items()};"
            "p=validate_probe(Path.cwd(),**a);"
            "print(json.dumps({'ok':True,'allow_test_transport':p.allow_test_transport,"
            "'request_hash':p.request.content_hash}))"
        )
        return call(
            self.repo, sys.executable, "-B", "-c", code, json.dumps(self.arguments)
        )

    def command(self, *, typed=True):
        args = self.arguments
        if typed:
            command = [
                sys.executable,
                "-B",
                str(self.repo / "scripts/task_execution.py"),
                "probe",
                "--task",
                "V2-019",
                "--action",
                "LIVE_CALL",
                "--output",
                str(self.private / "entry-report.json"),
            ]
            output_flag = "--probe-output"
        else:
            command = [
                sys.executable,
                "-B",
                str(self.repo / "scripts/run_gateway_probe.py"),
            ]
            output_flag = "--output"
        return (
            command
            + [
                "--request",
                args["request_path"],
                "--budget",
                args["budget_path"],
                "--policy-file",
                args["policy_path"],
                "--policy-id",
                args["policy_id"],
                "--ledger",
                args["ledger"],
                output_flag,
                args["output"],
                "--attempt-id",
                args["attempt_id"],
                "--prompt-key",
            ]
            + ([] if typed else ["--execute-live"])
        )


def freeze_fixture(seed, tmp_path, endpoint, *, openai_probe=False):
    repo = (tmp_path / "repo").resolve()
    call(
        tmp_path.resolve(),
        "git",
        "clone",
        "--shared",
        "--quiet",
        str(seed),
        str(repo),
        check=True,
    )
    private = (repo / "dist/synthetic-probe").resolve()
    private.mkdir(parents=True, mode=0o700)
    private.chmod(0o700)
    request = make_request(endpoint, openai_probe=openai_probe)
    (repo / "model-policy.yaml").write_bytes(request.policies[0].to_bytes())
    source_revision = commit(repo, "freeze synthetic loopback source policy")
    fingerprint = call(
        repo,
        sys.executable,
        "-B",
        "-c",
        "import sys;sys.path.insert(0,'plan/scripts');from probe_dispatch import fingerprint_source;"
        "from pathlib import Path;print(fingerprint_source(Path.cwd(),sys.argv[1]))",
        source_revision,
        check=True,
    ).stdout.strip()
    issued = datetime.now(UTC)
    stamp = lambda instant: instant.isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )
    budget = BudgetLimit(
        request.project,
        request.branch,
        request.run_id,
        10000,
        1,
        stamp(issued + timedelta(seconds=90)),
        1,
        1,
    )
    for name, data in (
        ("request.json", request.to_bytes()),
        ("budget.json", budget.to_bytes()),
        ("policy.json", request.policies[0].to_bytes()),
    ):
        path = private / name
        path.write_bytes(data)
        path.chmod(0o600)
    owner_ref = RECORDS + "/owner.txt"
    count_ref = RECORDS + "/count-price.txt"
    (repo / owner_ref).parent.mkdir(parents=True, exist_ok=True)
    (repo / owner_ref).write_text(
        "SYNTHETIC FIXTURE ONLY: authorize local HTTP at most10000microUSD,1attempt,120seconds.\n"
    )
    (repo / count_ref).write_text(
        "SYNTHETIC FIXTURE ONLY: this loopback server charges nothing; not Provider pricing evidence.\n"
    )
    packet = yaml.safe_load((repo / PACKET).read_text())
    packet.update(repository_revision=source_revision, action="LIVE_CALL", claims=[])
    packet["allowed_paths"] = [
        *packet["expected_outputs"],
        PACKET,
        RECORDS + "/",
        "scripts/run_gateway_probe.py",
    ]
    packet["handoff"]["next_action"] = "LIVE_CALL"
    packet["budget"].update(
        paid_calls_allowed=True,
        model_cost_cap=0.01,
        maximum_attempts=1,
        maximum_runtime=120,
    )
    packet["probe_authorization"] = None
    scope_ref = RECORDS + "/scope.json"
    scope = {
        "record_type": "local_change_baseline",
        "schema_version": "1.0",
        "task_id": "V2-019",
        "opening_revision": source_revision,
        "packet_ref": PACKET,
        "allowed_paths": packet["allowed_paths"],
        "pre_existing": {},
        "protected_paths": [],
        "authorization_source": {
            "kind": "existing_user_task_authorization",
            "ref": owner_ref,
            "sha256": sha256((repo / owner_ref).read_bytes()).hexdigest(),
        },
        "exception_authorizations": [],
    }
    save_packet(repo, packet)
    write_json(repo / scope_ref, scope)
    scope_revision = commit(repo, "pin synthetic scope and inert owner fixture")
    review_ref = RECORDS + "/review.json"
    write_json(
        repo / review_ref,
        {
            "task_id": "V2-019",
            "baseline_pin": {
                "revision": scope_revision,
                "ref": scope_ref,
                "sha256": sha256((repo / scope_ref).read_bytes()).hexdigest(),
            },
            "dispositions": [],
        },
    )
    review_revision = commit(repo, "pin synthetic no-weakening review")
    binding = {
        "scope_revision": scope_revision,
        "scope_ref": scope_ref,
        "review_revision": review_revision,
        "review_ref": review_ref,
    }
    packet["change_review"] = binding
    save_packet(repo, packet)
    commit(repo, "bind exact synthetic scope and review")
    policy = request.policies[0]
    grant = {
        "record_type": "controlled_probe_authorization",
        "schema_version": "1.0",
        "task_id": "V2-019",
        "purpose": "FIRST_CAPABILITY_PROBE",
        "environment": "LOOPBACK_FIXTURE",
        "authorization_id": "synthetic-fixed-probe-grant",
        "source_revision": source_revision,
        "source_sha256": fingerprint,
        "scope_review": binding,
        "owner_authorization": {
            "kind": "owner_numeric_live_authorization",
            "source": "synthetic local test only",
            "ref": owner_ref,
            "sha256": sha256((repo / owner_ref).read_bytes()).hexdigest(),
        },
        "inputs": {
            "request": {
                "path": str(private / "request.json"),
                "sha256": sha256(request.to_bytes()).hexdigest(),
                "content_hash": request.content_hash,
            },
            "budget": {
                "path": str(private / "budget.json"),
                "sha256": sha256(budget.to_bytes()).hexdigest(),
                "content_hash": budget.content_hash,
            },
            "policy": {
                "path": str(private / "policy.json"),
                "sha256": sha256(policy.to_bytes()).hexdigest(),
                "content_hash": policy.content_hash,
            },
        },
        "identity": {
            "project": request.project,
            "branch": request.branch,
            "run_id": request.run_id,
            "logical_id": request.logical_id,
            "attempt_id": "synthetic-probe-attempt",
            "policy_id": policy.id,
            "model": policy.model,
        },
        "paths": {
            "private_root": str(private),
            "ledger": str(private / "ledger.sqlite3"),
            "output": str(private / "result.json"),
            "claim": str(private / "dispatch.claim"),
        },
        "issued_at": stamp(issued),
        "expires_at": stamp(issued + timedelta(seconds=120)),
        "deadline_at": budget.deadline_at,
        "limits": {
            "total_microusd": 10000,
            "max_attempts": 1,
            "max_inflight": 1,
            "max_unknown": 1,
            "maximum_runtime_seconds": 120,
            "max_http_requests": 2,
            "per_post_timeout_seconds": 30,
        },
        "count_cost": {
            "status": "VERIFIED_ZERO_COST",
            "source": "https://example.invalid/synthetic-count-fixture",
            "ref": count_ref,
            "sha256": sha256((repo / count_ref).read_bytes()).hexdigest(),
        },
        "automatic_retry": False,
        "fallback": False,
        "stop_on_unknown": True,
        "stop_on_pending": True,
    }
    fixture = Fixture(
        repo, private, request, budget, grant, RECORDS + "/grant.json", binding
    )
    fixture.freeze_grant()
    return fixture


@pytest.fixture
def prepared(seed, tmp_path):
    with local_server() as server:
        fixture = freeze_fixture(seed, tmp_path, server.endpoint)
        yield fixture, server


def terminal_process(repo, command, *, send_credential):
    environment = clean_environment(repo)
    # forkpty runs in a new single-threaded helper, not the HTTP-server process.
    helper = """
import errno,json,os,pty,select,sys,time
command=json.loads(sys.argv[1])
send=json.loads(sys.argv[2])
environment=json.loads(sys.argv[3])
credential=sys.argv[4]
pid,descriptor=pty.fork()
if pid==0:
    os.execve(command[0],command,environment)
transcript=b''
sent=False
status=None
started=time.monotonic()
try:
    while time.monotonic()-started<120:
        ready,_,_=select.select([descriptor],[],[],0.1)
        if ready:
            try:
                data=os.read(descriptor,65536)
            except OSError as error:
                if error.errno!=errno.EIO:
                    raise
                data=b''
            if data:
                transcript+=data
                if send and not sent and b'key' in transcript.lower():
                    os.write(descriptor,credential.encode()+b'\\n')
                    sent=True
            elif status is not None:
                break
        if status is None:
            waited,result=os.waitpid(pid,os.WNOHANG)
            if waited:
                status=result
        elif not ready:
            break
    if status is None:
        raise AssertionError('synthetic probe exceeded 120-second source-check test deadline')
    print(json.dumps({'code':os.waitstatus_to_exitcode(status),'transcript':transcript.decode('utf-8','replace'),'sent':sent}))
finally:
    if status is None:
        try:
            os.kill(pid,9)
        except ProcessLookupError:
            pass
        os.waitpid(pid,0)
    os.close(descriptor)
"""
    completed = call(
        repo,
        sys.executable,
        "-B",
        "-c",
        helper,
        json.dumps(command),
        json.dumps(send_credential),
        json.dumps(environment),
        SYNTHETIC_CREDENTIAL,
    )
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    return result["code"], result["transcript"].encode(), result["sent"]


def run_with_terminal(fixture, *, typed=True):
    return terminal_process(
        fixture.repo, fixture.command(typed=typed), send_credential=True
    )


def test_exact_frozen_fixture_authority_passes_real_context_scope_and_source(prepared):
    fixture, server = prepared
    checked = fixture.validate()
    assert checked.returncode == 0, checked.stderr
    assert json.loads(checked.stdout)["allow_test_transport"] is True
    assert server.requests == []
    assert not (fixture.private / "dispatch.claim").exists()
    assert not (fixture.private / "ledger.sqlite3").exists()


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_binding",
        "wrong_binding_hash",
        "wrong_task",
        "wrong_purpose",
        "expired",
        "missing_numeric_owner",
        "zero_total",
        "over_budget",
        "boolean_total",
        "excess_attempts",
        "over_runtime",
        "source_hash",
        "request_hash",
        "policy_hash",
        "budget_hash",
        "scope_pin",
        "project",
        "attempt",
        "count_cost_unknown",
        "arbitrary_endpoint",
    ],
)
def test_invalid_or_unapproved_authority_refuses_before_credential_or_network(
    prepared, mutation
):
    fixture, server = prepared
    if mutation in {"missing_binding", "wrong_binding_hash"}:
        packet = yaml.safe_load((fixture.repo / PACKET).read_text())
        if mutation == "missing_binding":
            packet["probe_authorization"] = None
        else:
            packet["probe_authorization"]["sha256"] = "0" * 64
        save_packet(fixture.repo, packet)
    else:
        changes = {
            "wrong_task": lambda g: g.update(task_id="V2-020"),
            "wrong_purpose": lambda g: g.update(purpose="GENERAL_GENERATION"),
            "expired": lambda g: g.update(expires_at="2000-01-01T00:00:00Z"),
            "missing_numeric_owner": lambda g: g["owner_authorization"].update(
                kind="existing_user_task_authorization"
            ),
            "zero_total": lambda g: g["limits"].update(total_microusd=0),
            "over_budget": lambda g: g["limits"].update(total_microusd=20000),
            "boolean_total": lambda g: g["limits"].update(total_microusd=True),
            "excess_attempts": lambda g: g["limits"].update(max_attempts=2),
            "over_runtime": lambda g: g["limits"].update(maximum_runtime_seconds=121),
            "source_hash": lambda g: g.update(source_sha256="0" * 64),
            "request_hash": lambda g: g["inputs"]["request"].update(
                content_hash="0" * 64
            ),
            "policy_hash": lambda g: g["inputs"]["policy"].update(sha256="0" * 64),
            "budget_hash": lambda g: g["inputs"]["budget"].update(sha256="0" * 64),
            "scope_pin": lambda g: g["scope_review"].update(scope_revision="f" * 40),
            "project": lambda g: g["identity"].update(
                project="other-synthetic-project"
            ),
            "attempt": lambda g: g["identity"].update(attempt_id="unapproved-attempt"),
            "count_cost_unknown": lambda g: g["count_cost"].update(status="UNKNOWN"),
            "arbitrary_endpoint": lambda g: g.update(environment="LIVE_PROVIDER"),
        }
        changes[mutation](fixture.grant)
        fixture.freeze_grant()
    checked = fixture.validate()
    assert checked.returncode != 0
    denied = call(fixture.repo, *fixture.command(typed=False))
    assert denied.returncode != 0
    assert server.requests == []
    assert not (fixture.private / "dispatch.claim").exists()
    assert not (fixture.private / "ledger.sqlite3").exists()
    assert SYNTHETIC_CREDENTIAL not in denied.stdout + denied.stderr


def test_qualified_typed_probe_uses_hidden_synthetic_input_and_durable_loopback_receipt(
    prepared,
):
    fixture, server = prepared
    code, transcript, sent = run_with_terminal(fixture)
    assert code == 0, transcript.decode(errors="replace")
    assert sent
    assert len(server.requests) == 2
    assert [path for path, _ in server.requests] == [
        "/v1/responses/input_tokens",
        "/v1/responses",
    ]
    result = json.loads((fixture.private / "result.json").read_text())
    summary = result["summary"]
    assert summary["status"] == "SUCCESS"
    assert summary["charge_status"] == "ESTIMATED"
    assert summary["provider_request_id"] == "synthetic-generation"
    assert summary["response_hash"] == sha256(server.responses[-1]).hexdigest()
    assert summary["usage"] == {
        "kind": "PROVIDER_USAGE",
        "schema_version": "1.0",
        "input_tokens": 30,
        "output_tokens": 10,
        "total_tokens": 40,
    }
    assert (fixture.private / "ledger.sqlite3").exists()
    assert (fixture.private / "dispatch.claim").exists()
    assert (fixture.private / "result.json").stat().st_mode & 0o777 == 0o600
    assert SYNTHETIC_CREDENTIAL.encode() not in transcript
    assert SYNTHETIC_CREDENTIAL not in (fixture.private / "result.json").read_text()
    assert (
        SYNTHETIC_CREDENTIAL not in (fixture.private / "entry-report.json").read_text()
    )


def test_kimi_typed_probe_preserves_frozen_dispatch_and_hidden_credential(
    seed, tmp_path
):
    with local_server(kimi=True) as server:
        fixture = freeze_fixture(seed, tmp_path, server.endpoint)
        code, transcript, sent = run_with_terminal(fixture)

    assert code == 0, transcript.decode(errors="replace")
    assert sent and b"Kimi API key:" in transcript
    assert SYNTHETIC_CREDENTIAL.encode() not in transcript
    assert [path for path, _ in server.requests] == [
        "/v1/tokenizers/estimate-token-count",
        KIMI_CHAT_PATH,
    ]
    assert server.requests[1][1]["reasoning_effort"] == "high"
    output = fixture.private / "result.json"
    summary = json.loads(output.read_text())["summary"]
    assert summary["provider"] == "KIMI"
    assert summary["probe_environment"] == "LOOPBACK_FIXTURE"
    assert summary["observed_model"] == KIMI_MODEL
    assert summary["status"] == "SUCCESS"
    assert summary["charge_status"] == "ESTIMATED"
    assert summary["response_hash"] == sha256(server.responses[-1]).hexdigest()
    assert summary["provider_request_id"] == "synthetic-generation"
    assert summary["usage"]["total_tokens"] == 40
    assert (fixture.private / "dispatch.claim").exists()
    assert (fixture.private / "ledger.sqlite3").exists()
    assert output.stat().st_mode & 0o777 == 0o600
    assert SYNTHETIC_CREDENTIAL not in output.read_text()


def test_kimi_probe_rejects_unresolved_count_charge_before_dispatch(seed, tmp_path):
    with local_server(kimi=True) as server:
        fixture = freeze_fixture(seed, tmp_path, server.endpoint)
        fixture.grant["count_cost"]["status"] = "UNKNOWN"
        fixture.freeze_grant()
        checked = fixture.validate()
        denied = call(fixture.repo, *fixture.command(typed=False))
    assert checked.returncode != 0
    assert "PROBE_COUNT_COST_UNRESOLVED" in checked.stderr
    assert denied.returncode != 0
    assert server.requests == []
    assert not (fixture.private / "dispatch.claim").exists()
    assert not (fixture.private / "ledger.sqlite3").exists()


def configure_kimi_generation_only(fixture, **request_changes):
    request = replace(
        fixture.request,
        **(
            {
                "context": replace(fixture.request.context, items=()),
                "instructions": (
                    'Return exactly this JSON object: {"text":"ANovelOS Kimi probe OK"}.'
                ),
                "template_version": "gateway-kimi-first-generation-v1",
            }
            | request_changes
        ),
    )
    fixture.request = request
    raw = request.to_bytes()
    (fixture.private / "request.json").write_bytes(raw)
    fixture.grant["inputs"]["request"].update(
        sha256=sha256(raw).hexdigest(), content_hash=request.content_hash
    )
    fixture.grant["count_cost"] = {
        "status": "NOT_REQUESTED",
        "source": None,
        "ref": None,
        "sha256": None,
    }
    fixture.grant["limits"]["max_http_requests"] = 1


def test_kimi_generation_only_grant_sends_one_reserved_post(seed, tmp_path):
    with local_server(kimi=True) as server:
        fixture = freeze_fixture(seed, tmp_path, server.endpoint)
        configure_kimi_generation_only(fixture)
        fixture.freeze_grant()

        code, transcript, sent = run_with_terminal(fixture)
        assert code == 0, transcript.decode(errors="replace")
        assert sent and b"Kimi API key:" in transcript
        refused, _, repeated_input = run_with_terminal(fixture, typed=False)
        assert refused != 0 and not repeated_input

    assert SYNTHETIC_CREDENTIAL.encode() not in transcript
    assert [path for path, _ in server.requests] == [KIMI_CHAT_PATH]
    output = fixture.private / "result.json"
    summary = json.loads(output.read_text())["summary"]
    assert summary["token_estimate"] == "NOT_REQUESTED"
    assert summary["count_hash"] is None
    assert "estimate_fee_reserve" not in summary
    assert summary["reserve_microusd"] == fixture.request.policies[0].reserve_microusd
    assert summary["response_hash"] == sha256(server.responses[0]).hexdigest()
    assert summary["provider_request_id"] == "synthetic-generation"
    assert summary["observed_model"] == KIMI_MODEL and summary["status"] == "SUCCESS"
    assert summary["charge_status"] == "ESTIMATED"
    assert (fixture.private / "dispatch.claim").exists()
    assert (fixture.private / "ledger.sqlite3").exists()
    assert output.stat().st_mode & 0o777 == 0o600
    assert SYNTHETIC_CREDENTIAL not in output.read_text()


@pytest.mark.parametrize(
    ("mode", "outcome", "http_status", "error_code"),
    [
        ("success", "SUCCESS", 200, None),
        ("wrong_marker", "FAILED", 200, "PROBE_MARKER_MISMATCH"),
        ("disconnect", "UNKNOWN", None, "GENERATION_TRANSPORT_UNPROVEN"),
        ("http_429", "FAILED", 429, "HTTP_429"),
    ],
)
def test_openai_first_generation_uses_one_post_and_checks_marker(
    seed, tmp_path, mode, outcome, http_status, error_code
):
    with local_server(mode, openai_probe=True) as server:
        fixture = freeze_fixture(seed, tmp_path, server.endpoint, openai_probe=True)
        fixture.grant["count_cost"] = {
            "status": "NOT_REQUESTED",
            "source": None,
            "ref": None,
            "sha256": None,
        }
        fixture.grant["limits"]["max_http_requests"] = 1
        fixture.freeze_grant()
        code, transcript, sent = run_with_terminal(fixture)
        assert sent and SYNTHETIC_CREDENTIAL.encode() not in transcript
        assert b"response_base64" not in transcript
        assert SYNTHETIC_RATE_LIMIT_MESSAGE.encode() not in transcript
        assert (code == 0) == (outcome == "SUCCESS"), transcript.decode(
            errors="replace"
        )
        refused, _, repeated_input = run_with_terminal(fixture, typed=False)
        assert refused != 0 and not repeated_input

    ((path, payload),) = server.requests
    assert path == "/v1/responses"
    assert payload["model"] == "gpt-6.2-sol" and payload["store"] is False
    assert payload["text"]["format"]["strict"] is True
    result = json.loads((fixture.private / "result.json").read_text())
    summary = result["summary"]
    assert summary["provider"] == "OPENAI" and summary["count_hash"] is None
    assert summary["token_estimate"] == "NOT_REQUESTED"
    assert summary["response_hash"] == (
        sha256(server.responses[0]).hexdigest() if server.responses else None
    )
    assert (summary["status"], summary["http_status"], summary["error_code"]) == (
        outcome,
        http_status,
        error_code,
    )
    assert summary["automatic_retry"] is False
    assert summary["budget_summary"]["attempts"] == 1
    reply = result["result"]["reply"]
    for field in ("http_status", "error_code", "response_hash", "count_hash"):
        assert summary[field] == reply[field]
    assert "response_base64" not in summary
    if mode in {"disconnect", "http_429"}:
        assert summary["charge_status"] == "PENDING"

    ledger_uri = (fixture.private / "ledger.sqlite3").as_uri() + "?mode=ro"
    with closing(sqlite3.connect(ledger_uri, uri=True)) as reopened:
        attempts = reopened.execute(
            "SELECT attempt_id, state, result_record FROM attempts WHERE run_id=?",
            (fixture.request.run_id,),
        ).fetchall()
    assert attempts == [
        (fixture.arguments["attempt_id"], "FINISHED", canonical_bytes(result["result"]))
    ]


@pytest.mark.parametrize(
    ("mutation", "diagnostic"),
    [
        ("legacy_template", "PROBE_PROBE_CONTRACT"),
        ("context_content", "PROBE_GENERATION_ONLY_REQUEST"),
        ("count_evidence", "PROBE_COUNT_NOT_REQUESTED_FIELDS"),
        ("two_posts", "PROBE_HTTP_LIMIT"),
        ("other_provider", "PROBE_GENERATION_ONLY_REQUEST"),
    ],
)
def test_kimi_generation_only_grant_refuses_unbound_modes(
    seed, tmp_path, mutation, diagnostic
):
    with local_server(kimi=mutation != "other_provider") as server:
        fixture = freeze_fixture(seed, tmp_path, server.endpoint)
        changes = {
            "legacy_template": {"template_version": "gateway-protocol-probe-v1"},
            "context_content": {"context": fixture.request.context},
        }.get(mutation, {})
        configure_kimi_generation_only(fixture, **changes)
        if mutation == "count_evidence":
            fixture.grant["count_cost"]["source"] = "https://platform.kimi.com/"
        if mutation == "two_posts":
            fixture.grant["limits"]["max_http_requests"] = 2
        fixture.freeze_grant()
        checked = fixture.validate()
        denied = call(fixture.repo, *fixture.command(typed=False))

    assert checked.returncode != 0 and diagnostic in checked.stderr
    assert denied.returncode != 0
    assert server.requests == []
    assert not (fixture.private / "dispatch.claim").exists()
    assert not (fixture.private / "ledger.sqlite3").exists()


def bind_paid_estimate(fixture, **tariff_changes):
    original_ref = RECORDS + "/synthetic-paid-count-source.txt"
    reviewed_ref = RECORDS + "/synthetic-paid-count-review.json"
    original = fixture.repo / original_ref
    reviewed = fixture.repo / reviewed_ref
    source = "https://example.invalid/synthetic-paid-estimate"
    maximum = tariff_changes.get("maximum_microusd", 137)
    quote = f"Synthetic loopback fixture only. Maximum estimate fee {maximum} microUSD."
    original.write_text(quote + "\n")
    endpoint = fixture.request.policies[0].endpoint
    tariff = {
        "record_type": "kimi_estimate_fee_bound",
        "schema_version": "1.0",
        "currency": "USD",
        "model": KIMI_MODEL,
        "endpoint": endpoint.removesuffix(KIMI_CHAT_PATH)
        + "/v1/tokenizers/estimate-token-count",
        "source": source,
        "maximum_microusd": maximum,
        "expires_at": fixture.budget.deadline_at,
        "source_ref": original_ref,
        "source_sha256": sha256(original.read_bytes()).hexdigest(),
        "source_quote": quote,
    }
    tariff.update(tariff_changes)
    write_json(reviewed, tariff)
    evidence_sha256 = sha256(reviewed.read_bytes()).hexdigest()
    fixture.grant["count_cost"] = {
        "status": "VERIFIED_BOUNDED_CHARGE",
        "source": source,
        "ref": reviewed_ref,
        "sha256": evidence_sha256,
    }
    fixture.freeze_grant()
    return maximum, evidence_sha256


def test_kimi_paid_estimate_reservation_survives_success_and_refuses_replay(
    seed, tmp_path
):
    with local_server(kimi=True) as server:
        fixture = freeze_fixture(seed, tmp_path, server.endpoint)
        maximum, evidence_sha256 = bind_paid_estimate(fixture)
        code, transcript, sent = run_with_terminal(fixture)
        assert code == 1, transcript.decode(errors="replace")
        assert sent
        repeated_code, _, repeated_input = run_with_terminal(fixture, typed=False)
        assert repeated_code != 0 and not repeated_input
    assert SYNTHETIC_CREDENTIAL.encode() not in transcript
    assert [path for path, _ in server.requests] == [
        "/v1/tokenizers/estimate-token-count",
        KIMI_CHAT_PATH,
    ]
    output = json.loads((fixture.private / "result.json").read_text())
    summary = output["summary"]
    assert summary["estimate_fee_reserve"]["maximum_microusd"] == maximum
    assert summary["estimate_fee_reserve"]["evidence_sha256"] == evidence_sha256
    assert summary["reserve_microusd"] == (
        fixture.request.policies[0].reserve_microusd + maximum
    )
    assert summary["status"] == "SUCCESS"
    assert summary["charge_status"] == "PENDING"
    assert summary["charge_microusd"] is None
    assert summary["count_hash"] == sha256(server.responses[0]).hexdigest()
    assert summary["response_hash"] == sha256(server.responses[1]).hexdigest()
    reopened = BudgetLedger(fixture.private / "ledger.sqlite3").summary(
        fixture.request.run_id
    )
    assert reopened == summary["budget_summary"]
    assert reopened["unknown_microusd"] >= maximum
    assert reopened["attempts"] == reopened["unknown_attempts"] == 1


@pytest.mark.parametrize(
    "tampering,error",
    [
        ({"source_sha256": "0" * 64}, "COUNT_COST_EVIDENCE"),
        ({"source_quote": "not present in the pinned source"}, "COUNT_COST_EVIDENCE"),
        ({"model": "kimi-k3.1-pro-highspeed"}, "COUNT_COST_TARIFF"),
        (
            {"endpoint": "https://api.moonshot.ai/v1/tokenizers/estimate-token-count"},
            "COUNT_COST_TARIFF_ENDPOINT",
        ),
        ({"expires_at": "2020-01-01T00:00:00Z"}, "COUNT_COST_TARIFF_EXPIRED"),
        ({"maximum_microusd": 10000}, "BUDGET_BOUND"),
    ],
)
def test_kimi_paid_estimate_rejects_bad_bound_before_claim(
    seed, tmp_path, tampering, error
):
    with local_server(kimi=True) as server:
        fixture = freeze_fixture(seed, tmp_path, server.endpoint)
        bind_paid_estimate(fixture, **tampering)
        checked = fixture.validate()
        denied = call(fixture.repo, *fixture.command(typed=False))
    assert checked.returncode != 0
    assert f"PROBE_{error}" in checked.stderr
    assert denied.returncode != 0
    assert server.requests == []
    assert not (fixture.private / "dispatch.claim").exists()
    assert not (fixture.private / "ledger.sqlite3").exists()


@pytest.mark.parametrize(
    "mode", ["success", "disconnect", "missing_usage", "count_denied"]
)
def test_finished_unknown_or_pending_claim_never_sends_a_second_attempt(
    seed, tmp_path, mode
):
    with local_server(mode) as server:
        fixture = freeze_fixture(seed, tmp_path, server.endpoint)
        code, transcript, _ = run_with_terminal(fixture)
        assert code == (0 if mode == "success" else 1), transcript.decode(
            errors="replace"
        )
        expected = 1 if mode == "count_denied" else 2
        assert len(server.requests) == expected
        repeated_code, repeated_text, repeated_input = run_with_terminal(
            fixture, typed=False
        )
        assert repeated_code != 0
        assert not repeated_input
        assert len(server.requests) == expected
        assert SYNTHETIC_CREDENTIAL.encode() not in repeated_text


@pytest.mark.parametrize(
    "condition",
    [
        "no_tty",
        "directory_mode",
        "directory_symlink",
        "output_exists",
        "ledger_symlink",
        "claim_exists",
    ],
)
def test_private_path_or_terminal_failure_never_reads_input_or_sends(
    prepared, condition
):
    fixture, server = prepared
    if condition == "directory_mode":
        fixture.private.chmod(0o755)
    elif condition == "directory_symlink":
        moved = fixture.private.with_name("moved-private")
        fixture.private.rename(moved)
        fixture.private.symlink_to(moved, target_is_directory=True)
    elif condition == "output_exists":
        (fixture.private / "result.json").write_text("existing synthetic evidence")
        (fixture.private / "result.json").chmod(0o600)
    elif condition == "ledger_symlink":
        target = fixture.private / "unapproved-ledger-target"
        target.write_text("synthetic target")
        target.chmod(0o600)
        (fixture.private / "ledger.sqlite3").symlink_to(target)
    elif condition == "claim_exists":
        (fixture.private / "dispatch.claim").write_text("existing synthetic claim")
        (fixture.private / "dispatch.claim").chmod(0o600)
    if condition == "no_tty":
        denied = call(fixture.repo, *fixture.command(typed=False))
        assert denied.returncode != 0
        assert (fixture.private / "dispatch.claim").exists()
    else:
        denied_code, _, prompted = run_with_terminal(fixture, typed=False)
        assert denied_code != 0
        assert not prompted
    assert server.requests == []
    assert (
        not (fixture.private / "ledger.sqlite3").is_file()
        or condition == "ledger_symlink"
    )
    if condition == "output_exists":
        assert (
            fixture.private / "result.json"
        ).read_text() == "existing synthetic evidence"


@pytest.mark.parametrize("action", ["LIVE_CALL", "CERTIFY"])
def test_generic_paid_or_certification_command_remains_denied(prepared, action):
    fixture, server = prepared
    sentinel = fixture.private / "must-not-run"
    denied = call(
        fixture.repo,
        sys.executable,
        "-B",
        str(fixture.repo / "scripts/task_execution.py"),
        "run",
        "--task",
        "V2-019",
        "--action",
        action,
        "--output",
        str(fixture.private / "generic-report.json"),
        "--",
        sys.executable,
        "-c",
        "from pathlib import Path;Path(%r).write_text('ran')" % str(sentinel),
    )
    assert denied.returncode != 0
    assert "ENTRY_AUTHORIZATION" in denied.stdout
    assert not sentinel.exists()
    assert server.requests == []


def test_source_mutation_after_frozen_authority_is_not_adopted(prepared):
    fixture, server = prepared
    source = fixture.repo / "scripts/run_gateway_probe.py"
    source.write_text(
        source.read_text() + "\n# synthetic post-approval source mutation\n"
    )
    denied = fixture.validate()
    assert denied.returncode != 0
    assert server.requests == []


def test_actual_import_outside_bound_source_is_rejected(prepared):
    fixture, server = prepared
    module_path = fixture.private / "synthetic_foreign_module.py"
    module_path.write_text("SYNTHETIC_FIXTURE_ONLY = True\n")
    prefix = (
        "import importlib.util;"
        "s=importlib.util.spec_from_file_location('anovel.synthetic_foreign_module',%r);"
        "m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m);"
    ) % str(module_path)
    denied = fixture.validate(prefix=prefix)
    assert denied.returncode != 0
    assert "PROBE_MODULE_ORIGIN" in denied.stderr
    assert server.requests == []


def test_parent_terminal_guard_restores_echo_after_killed_synthetic_child():
    child = (
        "import sys,termios,time;fd=sys.stdin.fileno();a=termios.tcgetattr(fd);"
        "a[3]&=~termios.ECHO;termios.tcsetattr(fd,termios.TCSANOW,a);"
        "print('synthetic child disabled echo',flush=True);time.sleep(10)"
    )
    code = """
import os,subprocess,sys,termios
sys.path.insert(0,'plan/scripts')
from task_entry import probe_terminal_guard
fd=os.open('/dev/tty',os.O_RDWR|os.O_NOCTTY)
before=termios.tcgetattr(fd)
try:
    with probe_terminal_guard():
        subprocess.run([sys.executable,'-B','-c',sys.argv[1]],timeout=0.3,check=True)
except subprocess.TimeoutExpired:
    pass
after=termios.tcgetattr(fd)
assert after==before,'terminal flags were not restored'
os.close(fd)
print('SYNTHETIC_TIMEOUT_TERMINAL_RESTORED',flush=True)
"""
    result, transcript, sent = terminal_process(
        ROOT,
        [sys.executable, "-B", "-c", code, child],
        send_credential=False,
    )
    assert result == 0, transcript.decode(errors="replace")
    assert not sent
    assert b"SYNTHETIC_TIMEOUT_TERMINAL_RESTORED" in transcript


@pytest.mark.parametrize(
    "name",
    [
        "ledger.sqlite3",
        "ledger.sqlite3-wal",
        "ledger.sqlite3-shm",
        "ledger.sqlite3-journal",
        "result.json",
        "dispatch.claim",
        "RESULT.JSON",
    ],
)
def test_parent_receipt_helper_rejects_probe_paths_and_case_aliases(tmp_path, name):
    code = """
import json,sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,'plan/scripts')
from task_entry import probe_receipt_conflicts
directory=Path(sys.argv[1])
config=SimpleNamespace(ledger=directory/'ledger.sqlite3',output=directory/'result.json',claim_path=directory/'dispatch.claim')
print(json.dumps({'conflict':probe_receipt_conflicts(directory/sys.argv[2],config)}))
"""
    completed = call(ROOT, sys.executable, "-B", "-c", code, str(tmp_path), name)
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {"conflict": True}


def test_parent_receipt_helper_allows_separate_path(tmp_path):
    code = """
import json,sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,'plan/scripts')
from task_entry import probe_receipt_conflicts
directory=Path(sys.argv[1])
config=SimpleNamespace(ledger=directory/'ledger.sqlite3',output=directory/'result.json',claim_path=directory/'dispatch.claim')
print(json.dumps({'conflict':probe_receipt_conflicts(directory/'task-receipt.json',config)}))
"""
    completed = call(ROOT, sys.executable, "-B", "-c", code, str(tmp_path))
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {"conflict": False}


def test_competing_parent_guard_cannot_enter_or_change_active_hidden_terminal():
    contender = """
import sys
sys.path.insert(0,'plan/scripts')
from task_entry import probe_terminal_guard
try:
    with probe_terminal_guard():
        print('UNEXPECTED_GUARD_ENTRY',flush=True)
        raise SystemExit(7)
except (ValueError,OSError):
    print('SYNTHETIC_COMPETING_GUARD_BLOCKED',flush=True)
"""
    code = """
import subprocess,sys,termios
sys.path.insert(0,'plan/scripts')
from task_entry import probe_terminal_guard
with probe_terminal_guard() as descriptor:
    before=termios.tcgetattr(descriptor)
    hidden=before.copy()
    hidden[3]&=~termios.ECHO
    termios.tcsetattr(descriptor,termios.TCSANOW,hidden)
    try:
        contender=subprocess.run([sys.executable,'-B','-c',sys.argv[1]],capture_output=True,text=True,timeout=5)
        assert contender.returncode==0,contender.stdout+contender.stderr
        assert 'SYNTHETIC_COMPETING_GUARD_BLOCKED' in contender.stdout
        assert not termios.tcgetattr(descriptor)[3]&termios.ECHO,'contender restored echo during another input'
    finally:
        termios.tcsetattr(descriptor,termios.TCSAFLUSH,before)
print('SYNTHETIC_ACTIVE_TERMINAL_PRESERVED',flush=True)
"""
    result, transcript, sent = terminal_process(
        ROOT,
        [sys.executable, "-B", "-c", code, contender],
        send_credential=False,
    )
    assert result == 0, transcript.decode(errors="replace")
    assert not sent
    assert b"SYNTHETIC_ACTIVE_TERMINAL_PRESERVED" in transcript


def test_typed_parent_receipt_alias_is_rejected_before_claim_and_dispatch(prepared):
    fixture, server = prepared
    command = fixture.command()
    command[command.index("--output") + 1] = str(fixture.private / "result.json")
    completed = call(fixture.repo, *command)
    assert completed.returncode != 0
    assert "ENTRY_PROBE_OUTPUT" in completed.stdout
    assert server.requests == []
    assert not (fixture.private / "dispatch.claim").exists()
    assert not (fixture.private / "result.json").exists()
    assert not (fixture.private / "ledger.sqlite3").exists()


def test_parent_receipt_helper_rejects_unicode_normalization_alias(tmp_path):
    code = """
import json,sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,'plan/scripts')
from task_entry import probe_receipt_conflicts
directory=Path(sys.argv[1])
config=SimpleNamespace(ledger=directory/'caf\u00e9.sqlite3',output=directory/'result.json',claim_path=directory/'dispatch.claim')
alias=directory/'cafe\u0301.sqlite3-wal'
print(json.dumps({'conflict':probe_receipt_conflicts(alias,config)}))
"""
    completed = call(ROOT, sys.executable, "-B", "-c", code, str(tmp_path))
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {"conflict": True}
