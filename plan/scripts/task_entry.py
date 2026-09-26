"""Local action entry using existing plan rules. Not a protected CI runner.

Git/content observations support resumption. Packet-bound scope/review pins
require local diff checks for restricted actions before and after dispatch; they do not establish
remote provenance or credential enforcement (V2-004).
"""

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import validate_plan as validator
import yaml


def digest(data):
    return hashlib.sha256(data).hexdigest()


def git(root, *args):
    return subprocess.check_output(
        ["git", "-C", str(root), *args], stderr=subprocess.PIPE
    )


def observe(root):
    """Observe exact tracked/untracked bytes, index, branch and checkout.

    Ignored build outputs are excluded by Git, not a task-defined scan exclusion.
    Symlinks bind their link text; we do not read arbitrary external targets.
    """
    actual_root = Path(
        os.fsdecode(git(root, "rev-parse", "--show-toplevel")).strip()
    ).resolve()
    if root != actual_root:
        raise ValueError("ENTRY_ROOT: entry must belong to the repository root")
    names = set(
        git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard").split(
            b"\0"
        )
    ) - {b""}
    inventory = []
    for raw in sorted(names):
        name = os.fsdecode(raw)
        path = root / name
        if path.is_symlink():
            kind, value = "symlink", os.fsencode(os.readlink(path))
        elif path.is_file():
            kind, value = "file", path.read_bytes()
        elif not path.exists():
            kind, value = "missing", b""
        else:
            raise ValueError("ENTRY_WORKTREE: unsupported tracked path " + name)
        inventory.append(
            {
                "path": name,
                "kind": kind,
                "sha256": digest(value),
                "executable": bool(path.lstat().st_mode & 0o111)
                if path.exists()
                else False,
            }
        )
    status = git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    branch_result = subprocess.run(
        ["git", "-C", str(root), "symbolic-ref", "--quiet", "--short", "HEAD"],
        capture_output=True,
    )
    if branch_result.returncode not in (0, 1):
        branch_result.check_returncode()
    # Git returns 1 for a valid detached HEAD. Bind it explicitly to null while
    # still resolving the commit below; other Git failures must remain errors.
    branch = (
        os.fsdecode(branch_result.stdout).strip()
        if branch_result.returncode == 0
        else None
    )
    return {
        "root": str(root),
        "branch": branch,
        "head": git(root, "rev-parse", "HEAD").decode().strip(),
        "dirty": bool(status),
        "status_sha256": digest(status),
        "index_sha256": digest(git(root, "ls-files", "--stage", "-z")),
        "files": inventory,
        "python": platform.python_version(),
    }


def validate_context(root, task_id, action):
    """Reuse the full current rules, then bind selected action to the real Git base."""
    data = validator.load()
    errors = validator.validate_objects(data) + validator.check_files(
        data, validator.expected_views(data)
    )
    task = next(
        (t for t in data["implementation-backlog"]["tasks"] if t["task_id"] == task_id),
        None,
    )
    if task is None:
        return errors + ["ENTRY_TASK: task not registered"], None
    ref = task.get("execution_packet_ref")
    packet = None
    if not ref:
        errors.append(
            "ENTRY_PACKET: selected task requires its own packet even for PREPARE"
        )
    else:
        path = (root / "plan" / ref).resolve()
        if (
            not path.is_relative_to((root / "plan/validation").resolve())
            or not path.is_file()
        ):
            errors.append("ENTRY_PACKET: packet must resolve beneath plan/validation")
        else:
            packet = yaml.safe_load(path.read_text())
    if isinstance(packet, dict):
        if packet.get("task_id") != task_id or packet.get("action") != action:
            errors.append(
                "ENTRY_ACTION: requested task/action does not match the bound packet"
            )
        if task["status"] in {"VERIFIED", "CLOSED"}:
            errors.append(
                "ENTRY_STATE: completed task must be explicitly reopened before new actions"
            )
        if action != "PREPARE" and task["status"] not in {"IN_PROGRESS", "IMPLEMENTED"}:
            errors.append("ENTRY_STATE: implementation requires task start transition")
        revision = packet.get("repository_revision", "")
        if not isinstance(revision, str) or len(revision) != 40:
            errors.append("ENTRY_BASE: invalid opening revision")
        else:
            exists = subprocess.run(
                [
                    "git",
                    "-C",
                    str(root),
                    "merge-base",
                    "--is-ancestor",
                    revision,
                    "HEAD",
                ],
                capture_output=True,
            )
            if exists.returncode:
                errors.append(
                    "ENTRY_BASE: opening revision is absent or not an ancestor of current HEAD"
                )
    return errors, packet


def safe_output(root, output):
    """Reports cannot rewrite sources, tracked files, or their own prior record."""
    output = output.resolve()
    if output.exists():
        raise ValueError(
            "ENTRY_OUTPUT: use a new output file; prior records are immutable"
        )
    if output.is_relative_to(root):
        relative = output.relative_to(root)
        if relative.parts[0] in {"plan", ".git"}:
            raise ValueError("ENTRY_OUTPUT: reports must be outside plan/.git")
        # Keep output writes from changing the observed source worktree. Using an
        # arbitrary task-specified ignore list here would conceal source changes.
        ignored = subprocess.run(
            ["git", "-C", str(root), "check-ignore", "--quiet", "--", str(relative)]
        )
        tracked = git(root, "ls-files", "--", str(relative)).strip()
        if ignored.returncode or tracked:
            raise ValueError(
                "ENTRY_OUTPUT: in-repository reports require an untracked Git-ignored destination, e.g. dist/"
            )
    return output


def bind_change_review(packet, action, args):
    """CLI flags may assert the packet binding, never select another scope."""
    binding = packet.get("change_review") if isinstance(packet, dict) else None
    requested = any(
        getattr(args, key)
        for key in ("scope_revision", "scope_ref", "review_revision", "review_ref")
    )
    if action == "PREPARE" and not requested:
        return
    if (
        not isinstance(binding, dict)
        or not binding.get("scope_revision")
        or not binding.get("scope_ref")
    ):
        raise ValueError(
            "ENTRY_DIFF_BINDING: restricted action requires a packet-bound scope pin"
        )
    for key in ("scope_revision", "scope_ref", "review_revision", "review_ref"):
        declared = binding.get(key)
        explicit = getattr(args, key)
        if explicit is not None and explicit != declared:
            raise ValueError("ENTRY_DIFF_BINDING: CLI cannot override packet " + key)
        setattr(args, key, declared)
    if bool(args.review_revision) != bool(args.review_ref):
        raise ValueError(
            "ENTRY_DIFF_BINDING: packet review revision and ref must be paired"
        )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["check", "run", "resume"])
    parser.add_argument("--task", required=True)
    parser.add_argument(
        "--action",
        required=True,
        choices=["PREPARE", "IMPLEMENT", "LIVE_CALL", "CERTIFY"],
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument(
        "--scope-revision",
        help="Full immutable local Git commit containing the change baseline",
    )
    parser.add_argument(
        "--scope-ref", help="Repository-relative baseline JSON at scope-revision"
    )
    parser.add_argument(
        "--review-revision", help="Optional separately pinned technical review commit"
    )
    parser.add_argument(
        "--review-ref", help="Repository-relative review record at review-revision"
    )
    # argparse REMAINDER after a positional consumes options too; separate the
    # explicit command delimiter so normal options can occur after mode.
    raw = list(sys.argv[1:] if argv is None else argv)
    command = []
    if "--" in raw:
        index = raw.index("--")
        raw, command = raw[:index], raw[index + 1 :]
    args = parser.parse_args(raw)
    root = Path(__file__).resolve().parents[2]
    report = {
        "record_type": "local_task_execution",
        "schema_version": "1.0",
        "task_id": args.task,
        "action": args.action,
        "mode": args.mode,
        "started_at": datetime.now(UTC).isoformat(),
        "status": "BLOCKED",
        "errors": [],
        "command": command,
        "command_result": None,
        "limitations": [
            "local observations; not CI or completion evidence",
            "direct tools/shared writers are not protected by this entry",
            "restricted actions require packet-bound scope pins; arbitrary command semantics are not certified",
        ],
    }
    output = None
    code = 2
    command_started = False
    try:
        output = safe_output(root, args.output)
        if args.mode == "run" and not command:
            raise ValueError("ENTRY_COMMAND: run requires a command after --")
        if args.mode == "check" and (command or args.checkpoint):
            raise ValueError("ENTRY_COMMAND: check neither executes nor resumes")
        if args.mode == "resume" and not args.checkpoint:
            raise ValueError("ENTRY_RESUME: checkpoint required")
        if args.mode != "resume" and args.checkpoint:
            raise ValueError("ENTRY_RESUME: checkpoint only applies to resume")
        if bool(args.scope_revision) != bool(args.scope_ref) or bool(
            args.review_revision
        ) != bool(args.review_ref):
            raise ValueError("ENTRY_DIFF: revision and ref must be supplied together")
        if args.review_revision and not args.scope_revision:
            raise ValueError("ENTRY_DIFF: review requires a pinned scope baseline")
        before = observe(root)
        report["before"] = before
        errors, packet = validate_context(root, args.task, args.action)
        after_validation = observe(root)
        if before != after_validation:
            errors.append(
                "ENTRY_RACE: repository changed during validation; reconcile and retry"
            )
        if args.mode == "resume":
            checkpoint_bytes = args.checkpoint.read_bytes()
            report["checkpoint"] = {
                "path": str(args.checkpoint.resolve()),
                "sha256": digest(checkpoint_bytes),
            }
            try:
                previous = json.loads(checkpoint_bytes)
            except (ValueError, UnicodeDecodeError) as exc:
                raise ValueError(
                    "ENTRY_RESUME: checkpoint must contain valid JSON"
                ) from exc
            if not isinstance(previous, dict):
                raise ValueError("ENTRY_RESUME: checkpoint must be a JSON object")
            if (
                previous.get("record_type") != "local_task_execution"
                or previous.get("schema_version") != "1.0"
                or previous.get("status") != "PASS"
                or previous.get("task_id") != args.task
                or previous.get("action") != args.action
                or previous.get("after") != before
            ):
                errors.append(
                    "ENTRY_RESUME: prior success/context does not match actual repository and inputs"
                )
            if (
                packet
                and packet.get("handoff", {}).get("last_check", {}).get("status")
                != "PASS"
            ):
                errors.append(
                    "ENTRY_HANDOFF: resume cannot inherit missing, failed or unknown last check"
                )
        if command and args.action in {"LIVE_CALL", "CERTIFY"}:
            errors.append(
                "ENTRY_AUTHORIZATION: paid/certification dispatch requires the future protected authorization adapter; this local entry checks declarations only"
            )
        try:
            bind_change_review(packet, args.action, args)
        except ValueError as exc:
            errors.append(str(exc))
        if args.scope_revision and not errors:
            from change_review import review_changes

            review = review_changes(
                root,
                task_id=args.task,
                scope_revision=args.scope_revision,
                scope_ref=args.scope_ref,
                review_revision=args.review_revision,
                review_ref=args.review_ref,
            )
            report["change_review"] = review
            if review["status"] != "PASS":
                # V2-002-R0: Diagnostic logging for fixture failure investigation
                print("\n" + "=" * 80, file=sys.stderr)
                print("DIAGNOSTIC: review_changes() returned FAIL", file=sys.stderr)
                print("=" * 80, file=sys.stderr)
                print(f"Task: {args.task}", file=sys.stderr)
                print(f"Status: {review['status']}", file=sys.stderr)
                print(f"\nErrors ({len(review.get('errors', []))}):", file=sys.stderr)
                for err in review.get("errors", []):
                    print(f"  - {err}", file=sys.stderr)
                print(
                    f"\nScope Findings ({len(review.get('scope_findings', []))}):",
                    file=sys.stderr,
                )
                for finding in review.get("scope_findings", [])[:20]:
                    print(
                        f"  - {json.dumps(finding, ensure_ascii=False)}",
                        file=sys.stderr,
                    )
                print(
                    f"\nFindings ({len(review.get('findings', []))}):", file=sys.stderr
                )
                for finding in review.get("findings", [])[:20]:
                    print(
                        f"  - code={finding.get('code')}, path={finding.get('path')}",
                        file=sys.stderr,
                    )
                print(f"\nChanges ({len(review.get('changes', []))}):", file=sys.stderr)
                for change in review.get("changes", [])[:20]:
                    print(
                        f"  - {change.get('status')} {change.get('path')}",
                        file=sys.stderr,
                    )
                print("=" * 80 + "\n", file=sys.stderr)
                errors.append(
                    "ENTRY_DIFF: actual changes failed frozen scope or weakening review"
                )
            if observe(root) != after_validation:
                errors.append(
                    "ENTRY_RACE: validated inputs changed before command dispatch; reconcile and retry"
                )
        report["change_review_requested"] = bool(args.scope_revision)
        report["errors"] = errors
        if not errors:
            code = 0
            if command:
                # PREPARE semantic gate: capture repository state before command
                before_command = None
                if args.action == "PREPARE":
                    before_command = observe(root)

                command_started = True
                result = subprocess.run(
                    command,
                    cwd=root,
                    capture_output=True,
                    text=True,
                    timeout=packet["budget"]["maximum_runtime"],
                )
                report["command_result"] = {
                    "exit_code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }
                code = (
                    result.returncode
                    if result.returncode >= 0
                    else 128 - result.returncode
                )

                # PREPARE semantic gate: verify no persistent implementation changes
                if args.action == "PREPARE" and before_command is not None:
                    after_command = observe(root)
                    # Check Git-visible repository-controlled state including file content identity
                    if (
                        before_command["head"] != after_command["head"]
                        or before_command["branch"] != after_command["branch"]
                        or before_command["index_sha256"]
                        != after_command["index_sha256"]
                        or before_command["files"] != after_command["files"]
                    ):
                        errors.append(
                            "ENTRY_PREPARE_IMMUTABLE: PREPARE cannot leave Git-visible persistent implementation changes (HEAD/branch/index/tracked worktree/untracked content modified)"
                        )
                        report["status"] = "FAIL"
                        code = code or 2

            if not errors:
                report["status"] = "PASS" if code == 0 else "FAIL"
            if command and args.scope_revision:
                after_review = review_changes(
                    root,
                    task_id=args.task,
                    scope_revision=args.scope_revision,
                    scope_ref=args.scope_ref,
                    review_revision=args.review_revision,
                    review_ref=args.review_ref,
                )
                report["change_review_after"] = after_review
                if after_review["status"] != "PASS":
                    report["errors"].append(
                        "ENTRY_DIFF_AFTER: command effects failed frozen scope or weakening review"
                    )
                    report["status"] = "FAIL"
                    code = code or 2
        report["after"] = observe(root)
    except subprocess.TimeoutExpired as exc:
        report["status"] = "UNKNOWN"
        report["errors"].append(
            "ENTRY_TIMEOUT: command interrupted; inspect effects before a fresh check"
        )
        report["command_result"] = {
            "exit_code": None,
            "stdout": str(exc.stdout or ""),
            "stderr": str(exc.stderr or ""),
        }
        code = 124
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        subprocess.SubprocessError,
        yaml.YAMLError,
    ) as exc:
        # A successful child is not a successful handoff if post-run observation
        # failed. Preserve uncertainty instead of returning a false green result.
        code = 2
        report["status"] = "UNKNOWN" if command_started else "BLOCKED"
        report["errors"].append(f"{type(exc).__name__}: {exc}")
    report["finished_at"] = datetime.now(UTC).isoformat()
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x") as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
    print(
        json.dumps(
            {key: report[key] for key in ("status", "task_id", "action", "errors")},
            ensure_ascii=False,
        )
    )
    return code
