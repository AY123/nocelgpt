"""Compare fixed old/new bytes for observable weakening; never approve changes.

The caller supplies Git observations and a pinned protection policy. Findings are
review inputs, not proof of program equivalence or authenticated authorization.
No candidate code is imported and no candidate authorization file is consulted.
"""

import ast
import configparser
import copy
import hashlib
import json
import re
import shlex
from collections import Counter
from pathlib import PurePosixPath

import tomllib
import yaml


class _UniqueLoader(yaml.SafeLoader):
    """Duplicate YAML keys must not hide the old or candidate requirement."""


def _mapping(loader, node, deep=False):
    loader.flatten_mapping(node)
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise ValueError("duplicate YAML key: " + str(key))
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


_UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


def _sha(value):
    return hashlib.sha256(value).hexdigest() if value is not None else None


def _dump(node):
    return ast.dump(node, include_attributes=False)


def _canonical(tree):
    # Docstrings, comments, parentheses and source positions are not checks.
    tree = copy.deepcopy(tree)
    for node in ast.walk(tree):
        if isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            if (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)
            ):
                node.body.pop(0)
    return tree


def _aliases(tree):
    aliases = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for item in node.names:
                aliases[item.asname or item.name.split(".")[0]] = (
                    item.name if item.asname else item.name.split(".")[0]
                )
        elif isinstance(node, ast.ImportFrom):
            for item in node.names:
                aliases[item.asname or item.name] = ".".join(
                    filter(None, (node.module, item.name))
                )
    return aliases


def _name(node, aliases):
    if isinstance(node, ast.Name):
        return aliases.get(node.id, node.id)
    if isinstance(node, ast.Attribute):
        return _name(node.value, aliases) + "." + node.attr
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "getattr"
        and len(node.args) >= 2
        and isinstance(node.args[1], ast.Constant)
        and isinstance(node.args[1].value, str)
    ):
        return _name(node.args[0], aliases) + "." + node.args[1].value
    return ""


def _skip_controls(tree):
    aliases = _aliases(tree)
    names = {
        "pytest.skip",
        "pytest.xfail",
        "pytest.mark.skip",
        "pytest.mark.skipif",
        "pytest.mark.xfail",
        "unittest.skip",
        "unittest.skipIf",
        "unittest.skipUnless",
        "unittest.expectedFailure",
    }
    found = Counter()
    # Calls retain their condition/arguments, so skipif(False) -> skipif(True)
    # is observable even though the count of skip nodes remains unchanged.
    for node in ast.walk(tree):
        target = node.func if isinstance(node, ast.Call) else node
        for name in {_name(target, aliases), _name(node, aliases)}:
            if name in names or name.endswith(".skipTest"):
                signature = name + (
                    ":" + _dump(node) if isinstance(node, ast.Call) else ""
                )
                found[signature] += 1
    return found


def _unknown_test_reflection(tree):
    aliases = _aliases(tree)
    return Counter(
        _dump(node)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "getattr"
        and node.args
        and _name(node.args[0], aliases).split(".")[0] in {"pytest", "unittest"}
        and (
            len(node.args) < 2
            or not isinstance(node.args[1], ast.Constant)
            or not isinstance(node.args[1].value, str)
        )
    )


def _is_assertion(node):
    return isinstance(node, ast.Assert) or (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Attribute)
        and node.value.func.attr.startswith("assert")
    )


def _assertions(tree):
    return Counter(_dump(node) for node in ast.walk(tree) if _is_assertion(node))


def _definitions(tree):
    found = Counter()

    def visit(node, prefix=""):
        for child in getattr(node, "body", []):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                key = prefix + child.name
                found[key] += 1
                visit(child, key + ".")

    visit(tree)
    return found


def _test_names(tree):
    return Counter(
        {
            name: count
            for name, count in _definitions(tree).items()
            if name.rsplit(".", 1)[-1].startswith("test")
        }
    )


def _safe_insertion(node, owner):
    if _is_assertion(node):
        return not isinstance(owner, (ast.Module, ast.ClassDef))
    if isinstance(owner, (ast.Module, ast.ClassDef)):
        return (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test")
            and not node.decorator_list
            and not node.args.defaults
            and not any(node.args.kw_defaults)
            and node.returns is None
            and not getattr(node, "type_params", [])
            and not any(
                arg.annotation is not None
                for arg in ast.walk(node.args)
                if isinstance(arg, ast.arg)
            )
        )
    return False


def _monotonic_ast(old, new):
    """Recognize only a narrow syntax-preserving extension, not equivalence."""
    if type(old) is not type(new):
        return False
    if not isinstance(old, ast.AST):
        return old == new
    if _dump(old) == _dump(new):
        return True
    for field, value in ast.iter_fields(old):
        candidate = getattr(new, field)
        if isinstance(value, list):
            if field == "body":
                index = 0
                for statement in candidate:
                    if index < len(value) and _monotonic_ast(value[index], statement):
                        index += 1
                    elif not _safe_insertion(statement, old):
                        return False
                if index != len(value):
                    return False
            elif len(value) != len(candidate) or not all(
                _monotonic_ast(a, b) for a, b in zip(value, candidate)
            ):
                return False
        elif not _monotonic_ast(value, candidate):
            return False
    return True


def _python_tests(old, new, emit):
    if old is not None and new is None:
        emit(
            "TEST_FILE_REMOVED",
            "/",
            "An existing Python test or fixture file was removed.",
        )
        return
    before = (
        _canonical(ast.parse(old))
        if old is not None
        else ast.Module(body=[], type_ignores=[])
    )
    after = _canonical(ast.parse(new))

    def collection_controls(tree):
        controls = Counter()
        for node in ast.walk(tree):
            if isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef)
            ) and node.name.startswith("pytest_"):
                controls[_dump(node)] += 1
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = (
                    node.targets if isinstance(node, ast.Assign) else [node.target]
                )
                if any(
                    isinstance(target, ast.Name)
                    and target.id
                    in {"collect_ignore", "collect_ignore_glob", "pytest_plugins"}
                    for target in targets
                ):
                    controls[_dump(node)] += 1
        return controls

    if collection_controls(before) != collection_controls(after):
        emit(
            "TEST_COLLECTION_CONTROL",
            "/collection",
            "Pytest collection/session hooks, ignore rules or plugin loading changed; review their actual collection effects.",
        )
    if _skip_controls(after) - _skip_controls(before):
        emit(
            "TEST_SKIP_CHANGED",
            "/skip",
            "A skip, conditional skip, xfail or expected-failure control was added or changed.",
        )
    if _unknown_test_reflection(after) - _unknown_test_reflection(before):
        emit(
            "TEST_DYNAMIC_CONTROL",
            "/reflection",
            "A pytest/unittest control is accessed through an unresolved reflective attribute; review is required.",
        )
    removed = _test_names(before) - _test_names(after)
    for name in sorted(removed):
        emit(
            "TEST_FUNCTION_REMOVED",
            "/" + name,
            "An existing test function is no longer discovered under its prior name.",
        )
    if _assertions(before) - _assertions(after):
        if _monotonic_ast(after, before):
            emit(
                "TEST_ASSERTION_REMOVED",
                "/assertions",
                "An assertion was deleted while the remaining test syntax was retained.",
            )
        else:
            emit(
                "TEST_ASSERTION_CHANGED",
                "/assertions",
                "An existing assertion was changed or reorganized; unchanged counts do not prove equivalent checks.",
            )
    duplicates = {name for name, count in _definitions(after).items() if count > 1}
    for name in sorted(duplicates):
        emit(
            "TEST_DEFINITION_REPLACED",
            "/" + name,
            "Repeated definitions can replace an earlier test or helper at runtime.",
        )
    if old is not None and not _monotonic_ast(before, after):
        emit(
            "TEST_LOGIC_CHANGED",
            "/",
            "Existing test, helper, fixture or control-flow semantics changed; equivalence requires review.",
        )


def _unknown_fields(old, new, known, pointer, emit):
    """Do not let typed comparisons silently exempt other policy fields."""
    metadata = {
        "status",
        "evidence",
        "evidence_refs",
        "execution_evidence",
        "execution_packet_ref",
        "version",
    }
    for key in (set(old) | set(new)) - set(known) - metadata:
        if old.get(key) != new.get(key):
            emit(
                "MACHINE_POLICY_CHANGED",
                pointer + "/" + str(key),
                "An unmodelled machine policy field changed and requires review.",
            )


def _rows(document, key, identity):
    if not isinstance(document, dict) or not isinstance(document.get(key), list):
        raise ValueError("expected a mapping containing a list at " + key)
    result = {}
    for row in document[key]:
        if (
            not isinstance(row, dict)
            or not isinstance(row.get(identity), str)
            or row[identity] in result
        ):
            raise ValueError("missing or duplicate " + identity + " in " + key)
        result[row[identity]] = row
    return result


def _list(value):
    if not isinstance(value, list):
        raise ValueError("expected a requirement list")
    return value


def _removed(old, new):
    # Serialized identities also support structured requirement lists.
    encode = lambda item: json.dumps(item, sort_keys=True, ensure_ascii=False)
    return set(map(encode, _list(old))) - set(map(encode, _list(new)))


def _phase(value):
    return (
        int(value[1:])
        if isinstance(value, str) and re.fullmatch(r"P\d+", value)
        else None
    )


def _later(old, new):
    return old != new and (
        _phase(old) is None or _phase(new) is None or _phase(new) > _phase(old)
    )


def _gate(old, new, pointer, emit, baseline=False):
    checks = "required_checks" if baseline else "checks"
    activation = "latest_activation_phase" if baseline else "activation_phase"
    if _removed(old.get(checks, []), new.get(checks, [])):
        emit(
            "GATE_CHECK_REMOVED",
            pointer + "/" + checks,
            "An existing required check was removed.",
        )
    if _later(old.get(activation), new.get(activation)):
        known = (
            _phase(old.get(activation)) is not None
            and _phase(new.get(activation)) is not None
        )
        emit(
            "GATE_ACTIVATION_RELAXED" if known else "GATE_ACTIVATION_CHANGED",
            pointer + "/" + activation,
            "A gate activation deadline was postponed or changed to an unknown value.",
        )
    if old.get("mode") != new.get("mode"):
        emit(
            "GATE_TRIGGER_CHANGED",
            pointer + "/mode",
            "The gate execution mode changed and requires review.",
        )
    if old.get("allow_failure") is False and new.get("allow_failure") is not False:
        emit(
            "HARD_FAILURE_DISABLED",
            pointer + "/allow_failure",
            "A previously explicit hard-failure requirement was removed or relaxed.",
        )
    _unknown_fields(
        old, new, {"id", checks, activation, "mode", "allow_failure"}, pointer, emit
    )


_MACHINE = {
    "implementation-backlog.yaml",
    "test-catalog.yaml",
    "ci-gates.yaml",
    "governance-baseline.yaml",
    "phase-gates.yaml",
    "milestones.yaml",
}


def _machine(path, old, new, emit):
    name = PurePosixPath(path).name
    if old is None:
        return
    if new is None:
        emit(
            "REQUIREMENTS_FILE_REMOVED",
            "/",
            "An existing machine requirement file was removed.",
        )
        return
    if name == "implementation-backlog.yaml":
        before, after = _rows(old, "tasks", "task_id"), _rows(new, "tasks", "task_id")
        for key, row in before.items():
            pointer = "/tasks/" + key
            if key not in after:
                emit(
                    "TASK_REMOVED", pointer, "An existing task definition was removed."
                )
                continue
            candidate = after[key]
            for field, code in (
                ("acceptance_criteria", "AC_REMOVED"),
                ("tests", "TASK_TEST_REFERENCE_REMOVED"),
                ("dependencies", "TASK_DEPENDENCY_REMOVED"),
                ("required_decisions", "TASK_DECISION_REMOVED"),
                ("out_of_scope", "TASK_EXCLUSION_REMOVED"),
            ):
                if _removed(row.get(field, []), candidate.get(field, [])):
                    emit(
                        code,
                        pointer + "/" + field,
                        "An existing task requirement was removed or rewritten.",
                    )
            for field in ("phase", "start_gate"):
                if row.get(field) != candidate.get(field):
                    emit(
                        "TASK_BOUNDARY_CHANGED",
                        pointer + "/" + field,
                        "Task phase or entry-gate identity changed.",
                    )
            _unknown_fields(
                row,
                candidate,
                {
                    "task_id",
                    "acceptance_criteria",
                    "tests",
                    "dependencies",
                    "required_decisions",
                    "out_of_scope",
                    "phase",
                    "start_gate",
                },
                pointer,
                emit,
            )
    elif name == "test-catalog.yaml":
        before, after = _rows(old, "suites", "id"), _rows(new, "suites", "id")
        for key, row in before.items():
            pointer = "/suites/" + key
            if key not in after:
                emit(
                    "TEST_SUITE_REMOVED",
                    pointer,
                    "An existing acceptance suite was removed.",
                )
                continue
            candidate = after[key]
            if row.get("target_path") != candidate.get("target_path"):
                emit(
                    "TEST_TARGET_CHANGED",
                    pointer + "/target_path",
                    "The acceptance test target changed; replacement coverage requires review.",
                )
            original = _rows(row, "scenarios", "id")
            current = _rows(candidate, "scenarios", "id")
            for sid, scenario in original.items():
                if sid not in current:
                    emit(
                        "SCENARIO_REMOVED",
                        pointer + "/scenarios/" + sid,
                        "An existing acceptance scenario was removed.",
                    )
                elif scenario.get("required_assertion") != current[sid].get(
                    "required_assertion"
                ):
                    emit(
                        "SCENARIO_ASSERTION_CHANGED",
                        pointer + "/scenarios/" + sid,
                        "The required assertion text changed; matching task edits do not prove no weakening.",
                    )
                if sid in current:
                    _unknown_fields(
                        scenario,
                        current[sid],
                        {"id", "required_assertion"},
                        pointer + "/scenarios/" + sid,
                        emit,
                    )
            _unknown_fields(
                row, candidate, {"id", "target_path", "scenarios"}, pointer, emit
            )
    elif name == "ci-gates.yaml":
        before, after = _rows(old, "gates", "id"), _rows(new, "gates", "id")
        for key, row in before.items():
            if key not in after:
                emit(
                    "GATE_REMOVED", "/gates/" + key, "An existing CI gate was removed."
                )
            else:
                _gate(row, after[key], "/gates/" + key, emit)
        if _removed(old.get("live_required_at", []), new.get("live_required_at", [])):
            emit(
                "GATE_CHECK_REMOVED",
                "/live_required_at",
                "A required live-validation occasion was removed.",
            )
        _unknown_fields(old, new, {"gates", "live_required_at"}, "", emit)
    elif name == "governance-baseline.yaml":
        for key, row in old.get("required_ci", {}).items():
            candidate = new.get("required_ci", {}).get(key)
            if candidate is None:
                emit(
                    "BASELINE_GATE_REMOVED",
                    "/required_ci/" + key,
                    "A minimum required CI gate was removed.",
                )
            else:
                _gate(row, candidate, "/required_ci/" + key, emit, baseline=True)
        for key, criteria in old.get("phase_criteria", {}).items():
            if _removed(criteria, new.get("phase_criteria", {}).get(key, [])):
                emit(
                    "BASELINE_REQUIREMENT_REMOVED",
                    "/phase_criteria/" + key,
                    "A minimum phase exit requirement was removed or rewritten.",
                )
        if _removed(old.get("required_findings", []), new.get("required_findings", [])):
            emit(
                "BASELINE_REQUIREMENT_REMOVED",
                "/required_findings",
                "A required finding obligation was removed.",
            )
        _milestones(old.get("milestones", {}), new.get("milestones", {}), emit)
        _unknown_fields(
            old,
            new,
            {"required_ci", "phase_criteria", "required_findings", "milestones"},
            "",
            emit,
        )
    elif name == "milestones.yaml":
        _milestones(
            _rows(old, "milestones", "id"), _rows(new, "milestones", "id"), emit
        )
    elif name == "phase-gates.yaml":
        before, after = _rows(old, "phases", "id"), _rows(new, "phases", "id")
        for key, row in before.items():
            pointer = "/phases/" + key
            if key not in after:
                emit(
                    "PHASE_REMOVED",
                    pointer,
                    "An existing phase definition was removed.",
                )
                continue
            for field in ("exit_criteria", "tasks"):
                if _removed(row.get(field, []), after[key].get(field, [])):
                    emit(
                        "PHASE_REQUIREMENT_REMOVED",
                        pointer + "/" + field,
                        "A phase requirement or required task was removed.",
                    )
            for field in ("entry_gate", "exit_gate"):
                if row.get(field) != after[key].get(field):
                    emit(
                        "PHASE_GATE_CHANGED",
                        pointer + "/" + field,
                        "Phase gate identity changed.",
                    )
            _unknown_fields(
                row,
                after[key],
                {"id", "exit_criteria", "tasks", "entry_gate", "exit_gate"},
                pointer,
                emit,
            )
        _unknown_fields(old, new, {"phases"}, "", emit)


def _milestones(old, new, emit):
    for key, row in old.items():
        pointer = "/milestones/" + key
        if key not in new:
            emit("MILESTONE_REMOVED", pointer, "A required milestone was removed.")
            continue
        candidate = new[key]
        if _removed(row.get("required_tasks", []), candidate.get("required_tasks", [])):
            emit(
                "MILESTONE_REQUIREMENT_REMOVED",
                pointer + "/required_tasks",
                "A milestone task obligation was removed.",
            )
        old_phase, new_phase = (
            row.get("earliest_close_phase"),
            candidate.get("earliest_close_phase"),
        )
        if old_phase != new_phase and (
            _phase(old_phase) is None
            or _phase(new_phase) is None
            or _phase(new_phase) < _phase(old_phase)
        ):
            known = _phase(old_phase) is not None and _phase(new_phase) is not None
            emit(
                "MILESTONE_CLOSE_RELAXED" if known else "MILESTONE_CLOSE_CHANGED",
                pointer + "/earliest_close_phase",
                "The earliest permitted milestone closure was advanced or became unknown.",
            )
        _unknown_fields(
            row,
            candidate,
            {"id", "required_tasks", "earliest_close_phase"},
            pointer,
            emit,
        )


_MINIMUM = {
    "fail_under",
    "minimum",
    "threshold",
    "min_coverage",
    "minimum_coverage",
    "coverage_minimum",
    "min_score",
    "min_pass_rate",
}
_MAXIMUM = {"max_error_rate", "max_failures", "maximum_failures", "max_failure_rate"}
_EXCLUDE = {
    "exclude",
    "excludes",
    "omit",
    "ignore",
    "extend_exclude",
    "norecursedirs",
    "collect_ignore",
    "collect_ignore_glob",
}
_TARGETS = {"testpaths", "scan_paths", "scan_targets", "packages"}


def _numeric(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _policy(old, new, emit, pointer=""):
    if not isinstance(old, dict) or not isinstance(new, dict):
        return
    for key in sorted(set(old) | set(new), key=str):
        before, after = old.get(key), new.get(key)
        if before == after:
            continue
        path = pointer + "/" + str(key)
        normalized = str(key).lower().replace("-", "_")
        if normalized in _MINIMUM | _MAXIMUM:
            if key in old and key not in new:
                emit(
                    "THRESHOLD_REMOVED",
                    path,
                    "An existing explicit threshold was removed.",
                )
            elif key in old and (not _numeric(before) or not _numeric(after)):
                emit(
                    "THRESHOLD_CHANGED",
                    path,
                    "A threshold was removed or changed to a value whose direction cannot be established.",
                )
            elif (
                _numeric(before)
                and _numeric(after)
                and (
                    (normalized in _MINIMUM and after < before)
                    or (normalized in _MAXIMUM and after > before)
                )
            ):
                emit(
                    "THRESHOLD_RELAXED",
                    path,
                    "A recognized minimum was lowered or maximum failure tolerance increased.",
                )
        elif normalized in _EXCLUDE:
            if (
                isinstance(after, list)
                and all(isinstance(v, str) for v in after)
                and (before is None or isinstance(before, list))
            ):
                if set(after) - set(before or []):
                    emit(
                        "SCAN_EXCLUSION_EXPANDED",
                        path,
                        "The scan exclusion list gained entries.",
                    )
            elif after is not None:
                emit(
                    "SCAN_EXCLUSION_CHANGED",
                    path,
                    "A non-list exclusion changed; containment requires review.",
                )
        elif normalized in _TARGETS and key in old:
            if (
                not isinstance(before, list)
                or not isinstance(after, list)
                or _removed(before, after)
            ):
                emit(
                    "SCAN_TARGETS_CHANGED",
                    path,
                    "An existing scan target was removed or rewritten.",
                )
        elif (
            normalized in {"allow_failure", "continue_on_error"} and after is not False
        ):
            emit("HARD_FAILURE_DISABLED", path, "A hard failure may now be ignored.")
        elif (
            normalized in {"required", "enabled"}
            and before is True
            and after is not True
        ):
            emit(
                "REQUIRED_CHECK_DISABLED",
                path,
                "An explicit enabled/required policy was disabled or removed.",
            )
        elif normalized == "addopts":
            before_tokens = (
                shlex.split(before or "")
                if isinstance(before, (str, type(None)))
                else before
            )
            after_tokens = (
                shlex.split(after or "")
                if isinstance(after, (str, type(None)))
                else after
            )
            selectors = ("--ignore", "--deselect", "--ignore-glob", "-k", "-m")
            if any(
                any(
                    str(token) == s or str(token).startswith(s + "=") for s in selectors
                )
                for token in after_tokens or []
            ):
                if before_tokens != after_tokens:
                    emit(
                        "TEST_SELECTION_CHANGED",
                        path,
                        "Test command selection changed; excluded coverage requires review.",
                    )
        if isinstance(before, dict) or isinstance(after, dict):
            _policy(
                before if isinstance(before, dict) else {},
                after if isinstance(after, dict) else {},
                emit,
                path,
            )
        elif isinstance(before, list) or isinstance(after, list):
            previous, current = (
                before if isinstance(before, list) else [],
                after if isinstance(after, list) else [],
            )
            for index in range(max(len(previous), len(current))):
                item_old = previous[index] if index < len(previous) else {}
                item_new = current[index] if index < len(current) else {}
                _policy(item_old, item_new, emit, path + "/" + str(index))


def _parse(path, value):
    suffix = PurePosixPath(path).suffix
    if value is None:
        return None
    if suffix in {".yaml", ".yml"}:
        return yaml.load(value, Loader=_UniqueLoader)
    if suffix == ".toml":
        return tomllib.loads(value.decode("utf-8"))
    if suffix == ".json":
        return json.loads(value)
    if suffix == ".py":
        return _dump(_canonical(ast.parse(value)))
    if PurePosixPath(path).name in {
        "pytest.ini",
        ".pytest.ini",
        "setup.cfg",
        "tox.ini",
    }:
        parser = configparser.ConfigParser(interpolation=None, strict=True)
        parser.read_string(value.decode("utf-8"))
        return {section: dict(parser[section]) for section in parser.sections()}
    return value


def _protected(path, rules):
    return any(
        path.startswith(rule) if rule.endswith("/") else path == rule for rule in rules
    )


_WEAKENING_CODES = {
    "TEST_FILE_REMOVED",
    "TEST_SKIP_CHANGED",
    "TEST_FUNCTION_REMOVED",
    "TEST_ASSERTION_REMOVED",
    "TASK_REMOVED",
    "AC_REMOVED",
    "TASK_TEST_REFERENCE_REMOVED",
    "TASK_DEPENDENCY_REMOVED",
    "TASK_DECISION_REMOVED",
    "TASK_EXCLUSION_REMOVED",
    "TEST_SUITE_REMOVED",
    "SCENARIO_REMOVED",
    "GATE_REMOVED",
    "GATE_CHECK_REMOVED",
    "BASELINE_GATE_REMOVED",
    "BASELINE_REQUIREMENT_REMOVED",
    "PHASE_REMOVED",
    "PHASE_REQUIREMENT_REMOVED",
    "MILESTONE_REMOVED",
    "MILESTONE_REQUIREMENT_REMOVED",
    "REQUIREMENTS_FILE_REMOVED",
    "THRESHOLD_RELAXED",
    "THRESHOLD_REMOVED",
    "SCAN_EXCLUSION_EXPANDED",
    "HARD_FAILURE_DISABLED",
    "REQUIRED_CHECK_DISABLED",
    "GATE_ACTIVATION_RELAXED",
    "MILESTONE_CLOSE_RELAXED",
}

# Collection-control codes require explicit authorization (not same-AI self-review)
_COLLECTION_CONTROL_CODES = {
    "TEST_COLLECTION_CONTROL",
}


def scan_weakening(changes, *, task_id, baseline):
    """Return stable review findings; the caller validates baseline and authority.

    ``protected_paths`` is a fixed list of exact files or trailing-slash scopes.
    Status/phase evidence metadata are not acceptance requirements. Supported
    machine structures and threshold names are deliberately finite; this does
    not claim arbitrary semantic weakening can be decided statically.
    """
    findings = {}
    for change in changes:
        path = change["path"]
        old, new = change["old_bytes"], change["new_bytes"]
        old_path = change.get("old_path") or path
        layer = change["layer"]

        def emit(code, pointer, reason):
            identity = [
                task_id,
                code,
                path,
                old_path,
                layer,
                pointer,
                _sha(old),
                _sha(new),
            ]
            identifier = hashlib.sha256(
                json.dumps(identity, ensure_ascii=False).encode()
            ).hexdigest()
            findings[identifier] = {
                "id": identifier,
                "code": code,
                "path": path,
                "layer": layer,
                "pointer": pointer,
                "old_sha": _sha(old),
                "new_sha": _sha(new),
                "reason": reason,
            }
            # Assign severity_kind based on code category
            if code in _WEAKENING_CODES:
                findings[identifier]["severity_kind"] = "WEAKENING"
            elif code in _COLLECTION_CONTROL_CODES:
                findings[identifier]["severity_kind"] = "AUTHORIZATION_REQUIRED"
            else:
                findings[identifier]["severity_kind"] = "REVIEW"

        if old_path != path and (
            _protected(path, baseline.get("protected_paths", []))
            or _protected(old_path, baseline.get("protected_paths", []))
        ):
            emit(
                "PROTECTION_MOVED",
                "/",
                "A protected checker or policy moved; its loading and protection coverage require review.",
            )
        if (old != new or old_path != path) and any(
            PurePosixPath(name).name == ".gitignore" for name in (path, old_path)
        ):
            emit(
                "SCAN_IGNORE_CHANGED",
                "/",
                "A Git ignore file was added, changed, removed or moved; nested ignore rules require review against the fixed scan scope.",
            )
        if old == new:
            continue

        try:
            before, after = _parse(old_path, old), _parse(path, new)
            if before != after and any(
                PurePosixPath(name).name == "conftest.py" for name in (path, old_path)
            ):
                emit(
                    "TEST_CONFTEST_CHANGED",
                    "/",
                    "An automatically loaded conftest was added, removed or changed; fixture and collection effects require review.",
                )
            if before != after and any(
                PurePosixPath(name).name
                in {"pytest.ini", ".pytest.ini", "setup.cfg", "tox.ini"}
                for name in (path, old_path)
            ):
                emit(
                    "TEST_CONFIG_CHANGED",
                    "/",
                    "A test discovery/configuration entry changed; review collection targets, selectors and plugin options.",
                )
            is_machine = (
                PurePosixPath(path).name in _MACHINE
                or PurePosixPath(old_path).name in _MACHINE
            )
            is_test = any(
                PurePosixPath(name).suffix == ".py"
                and (
                    name.startswith("tests/")
                    or PurePosixPath(name).name.startswith("test_")
                    or PurePosixPath(name).name == "conftest.py"
                )
                for name in (path, old_path)
            )
            if is_test:
                _python_tests(old, new, emit)
            if is_machine:
                _machine(
                    old_path if PurePosixPath(old_path).name in _MACHINE else path,
                    before,
                    after,
                    emit,
                )
            if PurePosixPath(path).suffix in {
                ".toml",
                ".yaml",
                ".yml",
                ".json",
            } or PurePosixPath(path).name in {
                "pytest.ini",
                ".pytest.ini",
                "setup.cfg",
                "tox.ini",
            }:
                _policy(before or {}, after or {}, emit)
            if (
                old is not None
                and before != after
                and (
                    _protected(path, baseline.get("protected_paths", []))
                    or _protected(old_path, baseline.get("protected_paths", []))
                )
            ):
                # Typed machine comparisons distinguish additions/status updates
                # from removed obligations. Existing executable protection code
                # and unmodelled policy changes always remain reviewable.
                if not is_machine:
                    emit(
                        "PROTECTION_CHANGED",
                        "/",
                        "An existing protected checker or policy changed semantically; review against the fixed baseline is required.",
                    )
        except (
            ValueError,
            TypeError,
            SyntaxError,
            AttributeError,
            KeyError,
            yaml.YAMLError,
            configparser.Error,
            RecursionError,
        ) as error:
            emit(
                "WEAKENING_PARSE_ERROR",
                "/",
                "Cannot safely compare required content: "
                + type(error).__name__
                + ": "
                + str(error),
            )
    return sorted(
        findings.values(),
        key=lambda item: (
            item["path"],
            item["layer"],
            item["pointer"],
            item["code"],
            item["id"],
        ),
    )
