"""Real package discovery plus synthetic source-only architecture fixtures.

The temporary Python files are parsed, never imported; no Canon or Provider
business implementation is installed by this suite.
"""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('v2003_architecture_checks', ROOT / 'plan/scripts/architecture_checks.py')
architecture = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(architecture)


def write(root, relative, text):
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text)
    return target


@pytest.fixture
def synthetic(tmp_path):
    write(tmp_path, 'src/anovel/__init__.py', '"""Synthetic package; never executed."""\n')
    write(tmp_path, 'plan/machine/ci-gates.yaml', (ROOT / 'plan/machine/ci-gates.yaml').read_text())
    assert architecture.check_architecture(tmp_path)['status'] == 'PASS'
    return tmp_path


def codes(report):
    return {item['code'] for item in report['findings']}


def test_real_production_tree_is_discovered_separately_from_synthetic_fixtures():
    report = architecture.check_architecture(ROOT)
    assert report['status'] == 'PASS', report['findings']
    actual = {str(path.relative_to(ROOT)) for path in (ROOT / 'src/anovel').rglob('*.py')}
    assert actual == {row['path'] for row in report['files']}
    assert actual and 'anovel' in report['modules']
    assert 'synthetic fixtures are separate' in report['scope']
    assert any('runtime/DB' in text for text in report['limitations'])


def test_legal_domain_ports_and_workflow_public_service(synthetic):
    write(synthetic, 'src/anovel/domain/ports.py', 'from typing import Protocol\nclass Port(Protocol):\n    pass\n')
    write(synthetic, 'src/anovel/domain/values.py', 'from dataclasses import dataclass\nfrom .ports import Port\n')
    write(synthetic, 'src/anovel/canon/repository.py', 'class Repository:\n    pass\n')
    write(synthetic, 'src/anovel/canon/commit_service.py', 'from .repository import Repository\n')
    write(synthetic, 'src/anovel/workflow/application.py', 'from anovel.canon.commit_service import CommitService\n')
    report = architecture.check_architecture(synthetic)
    assert report['status'] == 'PASS', report['findings']
    assert not report['coverage']['bootstrap_only']


@pytest.mark.parametrize('source', [
    'import openai as provider', 'from anthropic import Client as Provider',
    'from sqlalchemy.orm import Session', 'import psycopg',
    'import fastapi', 'import temporalio', 'import sqlite3',
    'if False:\n    import openai',
    'from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    import openai',
    'def helper():\n    from sqlalchemy import create_engine',
])
def test_domain_implementation_dependencies_fail(synthetic, source):
    write(synthetic, 'src/anovel/domain/values.py', source + '\n')
    report = architecture.check_architecture(synthetic)
    assert 'ARCH_DOMAIN_DEPENDENCY' in codes(report)


def test_unknown_domain_third_party_needs_review(synthetic):
    write(synthetic, 'src/anovel/domain/values.py', 'import unreviewed_sdk\n')
    assert 'ARCH_DOMAIN_UNKNOWN' in codes(architecture.check_architecture(synthetic))


def test_indirect_provider_and_internal_workflow_dependency_fail(synthetic):
    write(synthetic, 'src/anovel/platform/adapter.py', 'import openai\n')
    write(synthetic, 'src/anovel/workflow/engine.py', 'from anovel.platform import adapter\n')
    write(synthetic, 'src/anovel/domain/values.py', 'from ..workflow import engine as run\n')
    report = architecture.check_architecture(synthetic)
    assert {'ARCH_DOMAIN_LAYER', 'ARCH_DOMAIN_DEPENDENCY'} <= codes(report)
    assert any(item.get('dependency_chain') == ['anovel.domain.values', 'anovel.workflow.engine', 'anovel.platform.adapter', 'openai'] for item in report['findings'])


@pytest.mark.parametrize('caller', ['gateway/writer', 'quality/reviewer', 'repair/patcher', 'context/compiler', 'intelligence/reference'])
@pytest.mark.parametrize('target', ['repository', 'commit_service'])
def test_unauthorized_canon_imports_fail(synthetic, caller, target):
    write(synthetic, 'src/anovel/' + caller + '.py', 'from anovel.canon import ' + target + ' as capability\n')
    write(synthetic, 'src/anovel/canon/' + target + '.py', '"""Synthetic capability marker."""\n')
    assert {'ARCH_CANON_INTERNAL', 'ARCH_CANON_WRITE'} & codes(architecture.check_architecture(synthetic))


def test_workflow_may_not_access_internal_repository(synthetic):
    write(synthetic, 'src/anovel/workflow/application.py', 'import anovel.canon.repository\n')
    assert 'ARCH_CANON_INTERNAL' in codes(architecture.check_architecture(synthetic))


def test_package_reexport_and_intermediate_alias_do_not_hide_canon(synthetic):
    write(synthetic, 'src/anovel/canon/__init__.py', 'from .commit_service import CommitService as PublicThing\n')
    write(synthetic, 'src/anovel/canon/commit_service.py', 'class CommitService:\n    pass\n')
    write(synthetic, 'src/anovel/platform/alias.py', 'from anovel.canon import PublicThing\n')
    write(synthetic, 'src/anovel/quality/reviewer.py', 'from anovel.platform.alias import PublicThing as X\n')
    report = architecture.check_architecture(synthetic)
    assert any(item.get('source') == 'anovel.quality.reviewer' and item.get('target') == 'anovel.canon.commit_service' for item in report['findings'])


@pytest.mark.parametrize('source', [
    'import importlib\nimportlib.import_module("openai")',
    'import importlib as il\nil.import_module("openai")',
    'from importlib import import_module as load\nload("openai")',
    'from importlib import import_module\nload = import_module\nload("openai")',
    '__import__("openai")',
    'from builtins import __import__ as load\nload("openai")',
    'import importlib\ngetattr(importlib, "import_module")("openai")',
])
def test_literal_dynamic_import_and_aliases_follow_same_policy(synthetic, source):
    write(synthetic, 'src/anovel/domain/model.py', source + '\n')
    assert 'ARCH_DOMAIN_DEPENDENCY' in codes(architecture.check_architecture(synthetic))


def test_literal_relative_dynamic_import_is_resolved(synthetic):
    write(synthetic, 'src/anovel/domain/ports.py', 'class Port:\n    pass\n')
    write(synthetic, 'src/anovel/domain/value.py', 'from importlib import import_module\nimport_module(".ports", "anovel.domain")\n')
    report = architecture.check_architecture(synthetic)
    assert report['status'] == 'PASS', report['findings']
    assert any(item['target'] == 'anovel.domain.ports' and item['kind'] == 'literal-dynamic-import' for item in report['edges'])


@pytest.mark.parametrize('call', [
    '__import__("anovel.canon", fromlist=["repository"])',
    '__import__("anovel.canon", None, None, ("repository",))',
])
def test_literal_dynamic_fromlist_cannot_hide_canon_repository(synthetic, call):
    write(synthetic, 'src/anovel/canon/repository.py', 'class Repository:\n    pass\n')
    write(synthetic, 'src/anovel/quality/check.py', call + '\n')
    assert 'ARCH_CANON_INTERNAL' in codes(architecture.check_architecture(synthetic))


@pytest.mark.parametrize('source', [
    'import importlib\nimportlib.import_module(name)',
    'from importlib import import_module as load\nload(prefix + ".module")',
    '__import__(name)',
    'from anovel.domain import *',
    'import importlib.util as util\nutil.spec_from_file_location("history", path)',
    'from importlib.machinery import SourceFileLoader as Loader\nLoader("history", path)',
    'import importlib.util\nimportlib.util.find_spec("plan.archive.old")',
    '__import__("anovel.canon", fromlist=names)',
    '__import__("anovel.canon", fromlist=["*"])',
    'import sys\nsys.path.append("plan/archive")',
    'import sys as system\nsystem.path = []',
    'import sys\nsys.modules["x"] = other',
    'exec(source)', 'eval(source)',
    'import runpy\nrunpy.run_path(path)',
    'import importlib\ngetattr(importlib, function_name)("openai")',
])
def test_unresolved_dynamic_loading_fails_explicitly(synthetic, source):
    write(synthetic, 'src/anovel/platform/loader.py', source + '\n')
    assert 'ARCH_DYNAMIC_UNKNOWN' in codes(architecture.check_architecture(synthetic))


@pytest.mark.parametrize('source', ['import plan.archive.old', 'from archive import old', 'import tests.fixture', 'from scripts import helper'])
def test_historical_and_nonproduction_imports_fail(synthetic, source):
    write(synthetic, 'src/anovel/platform/adapter.py', source + '\n')
    assert 'ARCH_ARCHIVE' in codes(architecture.check_architecture(synthetic))


def test_new_nested_namespace_module_is_always_scanned(synthetic):
    new = write(synthetic, 'src/anovel/domain/new/nested.py', 'from typing import Protocol\n')
    before = architecture.check_architecture(synthetic)
    assert before['status'] == 'PASS' and 'anovel.domain.new.nested' in before['modules']
    new.write_text('import anthropic\n')
    after = architecture.check_architecture(synthetic)
    assert 'ARCH_DOMAIN_DEPENDENCY' in codes(after)
    assert before['coverage']['file_count'] == after['coverage']['file_count'] == 2


def test_synthetic_source_is_parsed_without_execution(synthetic):
    sentinel = synthetic / 'must-not-exist'
    write(synthetic, 'src/anovel/platform/helper.py', 'from pathlib import Path\nPath(' + repr(str(sentinel)) + ').write_text("executed")\nraise RuntimeError("not executed")\n')
    assert architecture.check_architecture(synthetic)['status'] == 'PASS'
    assert not sentinel.exists()


def test_package_initializers_are_edges_even_for_dotted_import(synthetic):
    write(synthetic, 'src/anovel/platform/__init__.py', 'import openai\n')
    write(synthetic, 'src/anovel/platform/helper.py', 'VALUE = 1\n')
    write(synthetic, 'src/anovel/domain/value.py', 'import anovel.platform.helper\n')
    assert 'ARCH_DOMAIN_DEPENDENCY' in codes(architecture.check_architecture(synthetic))


@pytest.mark.parametrize('source,code', [('def broken(', 'ARCH_SOURCE'), ('from ... import escape', 'ARCH_RELATIVE')])
def test_syntax_and_relative_root_escape_fail(synthetic, source, code):
    write(synthetic, 'src/anovel/domain/value.py', source + '\n')
    assert code in codes(architecture.check_architecture(synthetic))


def test_symlink_sources_and_directories_fail(synthetic):
    external = write(synthetic, 'plan/archive/old.py', 'import openai\n')
    (synthetic / 'src/anovel/old.py').symlink_to(external)
    (synthetic / 'src/anovel/legacy').symlink_to(external.parent, target_is_directory=True)
    report = architecture.check_architecture(synthetic)
    assert 'ARCH_PATH' in codes(report)
    assert len([item for item in report['findings'] if item['code'] == 'ARCH_PATH']) == 2


def test_empty_discovery_and_scan_narrowing_fail(synthetic):
    (synthetic / 'src/anovel/__init__.py').unlink()
    assert 'ARCH_EMPTY' in codes(architecture.check_architecture(synthetic))
    assert 'ARCH_PACKAGE' in codes(architecture.check_architecture(synthetic, package='src/anovel/domain'))


def test_ambiguous_module_file_and_package_fail(synthetic):
    write(synthetic, 'src/anovel/domain.py', '')
    write(synthetic, 'src/anovel/domain/__init__.py', '')
    assert 'ARCH_MODULE' in codes(architecture.check_architecture(synthetic))


def test_required_p0_gates_cannot_be_disabled_or_deferred(synthetic):
    assert 'ARCH_GATE_DISABLED' in codes(architecture.check_architecture(synthetic, disabled_gates=['ARCH_FITNESS']))
    assert 'ARCH_PHASE' in codes(architecture.check_architecture(synthetic, phase='P14'))
    path = synthetic / 'plan/machine/ci-gates.yaml'
    data = yaml.safe_load(path.read_text())
    gate = next(item for item in data['gates'] if item['id'] == 'ARCH_FITNESS')
    gate['activation_phase'] = 'P14'
    path.write_text(yaml.safe_dump(data))
    assert 'ARCH_GATE_PHASE' in codes(architecture.check_architecture(synthetic))


@pytest.mark.parametrize('mutation,expected', [
    (lambda data: data['gates'][0].update(allow_failure=True), 'ARCH_GATE_DISABLED'),
    (lambda data: data['gates'].pop(0), 'ARCH_GATE_MISSING'),
    (lambda data: data['gates'].append(data['gates'][0]), 'ARCH_GATES'),
])
def test_weakened_or_malformed_gate_policy_fails(synthetic, mutation, expected):
    path = synthetic / 'plan/machine/ci-gates.yaml'
    data = yaml.safe_load(path.read_text())
    mutation(data)
    path.write_text(yaml.safe_dump(data))
    assert expected in codes(architecture.check_architecture(synthetic))


def test_future_gates_are_reported_as_not_applicable(synthetic):
    report = architecture.check_architecture(synthetic, disabled_gates=['LIVE_PROVIDER'])
    assert report['status'] == 'PASS'
    future = next(item for item in report['gates'] if item['id'] == 'LIVE_PROVIDER')
    assert future['result'] == 'NOT_APPLICABLE' and not future['applicable']
    assert 'ARCH_GATE_UNKNOWN' in codes(architecture.check_architecture(synthetic, disabled_gates=['TYPO']))


def test_cli_real_report_preserves_sources_and_previous_results(tmp_path):
    output = tmp_path / 'architecture.json'
    command = [sys.executable, '-B', str(ROOT / 'scripts/check_architecture.py'), '--output', str(output)]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    report = json.loads(output.read_text())
    assert report['status'] == 'PASS' and report['coverage']['file_count'] > 0
    original = output.read_bytes()
    again = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    assert again.returncode != 0 and output.read_bytes() == original
    blocked = subprocess.run([*command[:-1], str(ROOT / 'plan/architecture-output.json')], cwd=ROOT, capture_output=True, text=True)
    assert blocked.returncode != 0 and not (ROOT / 'plan/architecture-output.json').exists()


def test_cli_failed_hard_gate_returns_nonzero(tmp_path):
    output = tmp_path / 'failure.json'
    result = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/check_architecture.py'), '--disable-gate', 'ARCH_FITNESS', '--output', str(output)], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 1
    assert 'ARCH_GATE_DISABLED' in codes(json.loads(output.read_text()))
