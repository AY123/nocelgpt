"""Validate declared AI task execution context, not actual tool permissions.

The future P0 runner must call checks before actions, reconcile real Git changes,
and obtain trusted CI results. A writable packet cannot prove an action occurred.
"""

import hashlib
import json
from pathlib import Path, PurePosixPath

import yaml
from jsonschema import Draft202012Validator

ACTIONS = {"PREPARE", "IMPLEMENT", "LIVE_CALL", "CERTIFY"}
CONTROL_INPUTS = (
    "machine/implementation-backlog.yaml",
    "machine/test-catalog.yaml",
    "machine/decision-register.yaml",
    "machine/ai-execution-policy.yaml",
)
ACTION_TIMINGS = {
    "PREPARE": set(),
    "IMPLEMENT": {"before_interface_implementation"},
    "LIVE_CALL": {"before_interface_implementation", "before_live_call"},
    "CERTIFY": {
        "before_interface_implementation",
        "before_live_call",
        "before_certification_run",
    },
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def local_file(plan, ref):
    """Resolve references inside plan, rejecting missing files and escapes."""
    if not isinstance(ref, str) or not ref.strip():
        return None
    path = (plan / ref).resolve()
    return path if plan in path.parents and path.is_file() else None


def bounded_path(value):
    """Only explicit repo-relative files/directories, never a root/glob grant."""
    if not isinstance(value, str) or not value.strip():
        return False
    path = PurePosixPath(value)
    return (
        not path.is_absolute()
        and bool(path.parts)
        and all(p not in {".", "..", ".git"} for p in value.rstrip("/").split("/"))
        and not any(c in value for c in ("*", "?", "[", "]", "\\", ":"))
    )


def execution_checks(data, plan):
    plan = Path(plan).resolve()
    errors = []
    schema = json.loads((plan / "schemas/execution-packet.schema.json").read_text())
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    decisions = {a["id"]: a for a in data["decision-register"]["decisions"]}

    def require(ok, prefix, tid, message):
        if not ok:
            errors.append(f"{prefix} {tid}: {message}")

    def check_artifact(item, tid):
        path = local_file(plan, item["ref"])
        require(
            path is not None and sha(path) == item["sha256"],
            "EXEC_INPUT",
            tid,
            "missing/changed artifact " + item["ref"],
        )
        return path

    for task in data["implementation-backlog"]["tasks"]:
        tid = task["task_id"]
        ref = task.get("execution_packet_ref")
        if not ref:
            require(
                task["status"] == "OPEN",
                "EXEC_PACKET",
                tid,
                "non-OPEN task requires an execution packet",
            )
            continue
        path = local_file(plan, ref)
        if path is None or path.relative_to(plan).parts[0] != "validation":
            errors.append(
                f"EXEC_PACKET {tid}: packet must resolve to a real file under validation/ (outside manifest)"
            )
            continue
        try:
            packet = yaml.safe_load(path.read_text())
            issues = list(validator.iter_errors(packet))
            if issues:
                errors.append(
                    f"EXEC_SCHEMA {tid}: " + "; ".join(e.message for e in issues[:3])
                )
                continue
        except (OSError, ValueError, yaml.YAMLError) as exc:
            errors.append(f"EXEC_SCHEMA {tid}: {exc}")
            continue

        active = task["status"] in {"OPEN", "IN_PROGRESS", "IMPLEMENTED"}
        require(packet["task_id"] == tid, "EXEC_SUBJECT", tid, "wrong task")
        if active:
            require(
                packet["owner_role"] == task["owner_role"],
                "EXEC_OWNER",
                tid,
                "wrong owner role",
            )
            require(
                set(packet["required_decisions"]) == set(task["required_decisions"]),
                "EXEC_ADR",
                tid,
                "required decision list differs",
            )
            require(
                set(task["artifacts"]).issubset(packet["expected_outputs"]),
                "EXEC_OUTPUTS",
                tid,
                "task outputs omitted",
            )
        require(
            all(
                bounded_path(p)
                for p in packet["allowed_paths"] + packet["expected_outputs"]
            ),
            "EXEC_SCOPE",
            tid,
            "paths must be bounded repository-relative files/directories",
        )
        # This checks the declared scope only. Inspecting actual diff is a P0 duty.
        for output in packet["expected_outputs"]:
            require(
                any(
                    output == allowed
                    or (allowed.endswith("/") and output.startswith(allowed))
                    for allowed in packet["allowed_paths"]
                ),
                "EXEC_SCOPE",
                tid,
                "declared output outside allowed paths: " + output,
            )

        if active:
            require(
                packet["plan_version"] == data["implementation-backlog"]["version"],
                "EXEC_VERSION",
                tid,
                "plan changed; reconcile context before continuation",
            )
            manifest = plan / "FILE_MANIFEST.json"
            require(
                manifest.is_file() and packet["plan_manifest_sha256"] == sha(manifest),
                "EXEC_VERSION",
                tid,
                "manifest changed; reconcile context before continuation",
            )
        seen_sources = set()
        for item in packet["inputs"]:
            check_artifact(item, tid)
            source = local_file(plan, item["source_ref"])
            if source is not None:
                source_ref = str(source.relative_to(plan))
                require(
                    source_ref not in seen_sources,
                    "EXEC_INPUT",
                    tid,
                    "duplicate input source",
                )
                seen_sources.add(source_ref)
            if active:
                require(
                    source is not None and sha(source) == item["sha256"],
                    "EXEC_INPUT",
                    tid,
                    "live source changed/missing: " + item["source_ref"],
                )
        if active:
            require(
                (set(task["normative_specs"]) | set(CONTROL_INPUTS)).issubset(
                    seen_sources
                ),
                "EXEC_INPUT",
                tid,
                "required normative input omitted",
            )

        action = packet["action"]
        require(
            task["status"] != "OPEN" or action == "PREPARE",
            "EXEC_ACTION",
            tid,
            "OPEN may prepare only; implementation requires task start gates",
        )
        require(
            task["status"] not in {"IMPLEMENTED", "VERIFIED", "CLOSED"}
            or action != "PREPARE",
            "EXEC_ACTION",
            tid,
            "preparation is not an implementation record",
        )
        if active:
            require(
                packet["handoff"]["next_action"] == action,
                "EXEC_HANDOFF",
                tid,
                "next action differs from current checked action",
            )
        # Historical packets preserve their declared context; accepted decisions
        # remain checked by the existing task/evidence validation as applicable.
        for decision_id in packet["required_decisions"]:
            decision = decisions.get(decision_id)
            require(decision is not None, "EXEC_ADR", tid, "unknown decision")
            if decision is not None and active:
                require(
                    decision["timing"] in set().union(*ACTION_TIMINGS.values()),
                    "EXEC_ADR",
                    tid,
                    "unknown timing cannot silently bypass checks",
                )
                if active and decision["timing"] in ACTION_TIMINGS[action]:
                    require(
                        decision["status"] == "ACCEPTED"
                        and bool(decision["decision_record"]),
                        "EXEC_ADR",
                        tid,
                        f"{decision_id} must be decided before {action}",
                    )

        claim_ids = [c["id"] for c in packet["claims"]]
        require(
            len(claim_ids) == len(set(claim_ids)),
            "EXEC_CLAIM",
            tid,
            "duplicate claim ID",
        )
        for claim in packet["claims"]:
            for item in claim["sources"]:
                check_artifact(item, tid)
            if active:
                require(
                    claim["kind"] == "FACT" or action not in claim["blocks_actions"],
                    "EXEC_CLAIM",
                    tid,
                    "unresolved action-blocking input: " + claim["id"],
                )
        for item in packet["handoff"]["last_check"]["artifacts"]:
            artifact = check_artifact(item, tid)
            require(
                artifact is None or artifact.relative_to(plan).parts[0] != "templates",
                "EXEC_HANDOFF",
                tid,
                "a template is not a check result",
            )
        if active and action in {"LIVE_CALL", "CERTIFY"}:
            require(
                int(task["phase"][1:]) >= (5 if action == "LIVE_CALL" else 8),
                "EXEC_ACTION",
                tid,
                "action is earlier than its production phase",
            )
            budget = packet["budget"]
            require(
                budget["paid_calls_allowed"]
                and budget["model_cost_cap"] is not None
                and budget["model_cost_cap"] > 0,
                "EXEC_BUDGET",
                tid,
                "live/certification action requires a positive declared budget",
            )
    return errors
