"""Record bounded technical dispositions; grants no authority to weaken or expand scope."""
from pathlib import Path
import argparse, hashlib, json
R = Path(__file__).resolve().parents[6]; B = R / 'plan/validation/execution/V2-003/followup'
p = argparse.ArgumentParser(); p.add_argument('--scan', required=True, type=Path); p.add_argument('--output', required=True, type=Path); p.add_argument('--final', action='store_true'); args = p.parse_args()
assert not args.output.exists()
scan = json.loads(args.scan.read_text()); assert not scan['errors'] and not scan['scope_findings']
baseline = json.loads((R / scan['baseline_pin']['ref']).read_text())
reasons = {
 'AGENTS.md': 'Replaces the optional CLI-pin description with mandatory packet-bound checks for restricted actions, before and after dispatch; retains same-permission and remote CI limitations.',
 'plan/machine/ai-execution-policy.yaml': 'AI-EXEC-02/03 capability descriptions match reproduced corrections. AI-EXEC-02 is temporarily reopened and restored only with local evidence. Existing obligations, owners, scenarios and minimum requirements are identical to opening; AI-EXEC-03 overall remains pending V2-004.',
 'plan/schemas/execution-packet.schema.json': 'Only adds typed optional change_review with complete scope pair and dependent review pair. All prior schema constraints remain byte-for-byte semantically equal; optionality preserves historical packets, while restricted entry requires the binding unconditionally.',
 'plan/scripts/architecture_checks.py': 'Adds name resolution for literal reflective namespace subscripts and vars aliases; unknown keys emit ARCH_DYNAMIC_UNKNOWN. Existing import, transitive and Canon rules are retained. Disallowed builtin loaders fail and legal literal standard-library imports pass.',
 'plan/scripts/change_review.py': 'Production findings now require a prior exact explicit_scope_change_authorization, never generic technical review. All exception grants must match a regular pre-change file identity at the pinned scope commit. Positive exact authorization, stale bytes and bundled-after-the-fact grants are tested without a real production grant.',
 'plan/scripts/task_entry.py': 'Restricted check/run/resume unconditionally load scope/review from the task packet. Missing binding or CLI overrides fail before dispatch. Existing packet/ADR/budget/action/resume/race checks remain. No-flag legal dispatch passes both diff checks and no-flag escaping child fails after dispatch.',
 'plan/scripts/weakening_checks.py': 'Adds conservative review for new or changed conftest, collection hooks/plugins/ignores and known INI test-discovery settings. Parse errors fail; legal fixtures can pass exact technical review. No existing weakening rule, selection threshold or protected path was removed.',
 'tests/architecture/test_change_review.py': 'Adds actual Git positive and negative cases for mandatory binding, exact prior production grants and conftest review. Existing two entry mocks now supply the newly required packet binding, preserving actual Git/diff execution. Existing test functions, decorators and every assertion are retained.',
 'tests/architecture/test_dependency_boundaries.py': 'Only appends eight builtin/reflection cases, including a legal standard-library positive control. Existing test functions, decorators and assertions are retained; the initial fixture misuse and corrected complete rerun are preserved as separate raw records.',
 'tests/architecture/test_weakening_checks.py': 'Only appends twelve collection/configuration coverage cases, with unchanged-config positive controls. Existing test functions, decorators and assertions remain.',
 'tests/contract/test_task_execution.py': 'Legacy isolated seed now freezes real scope commits and binds packets instead of bypassing the actual diff check. Existing assertions/decorators remain, legal execution adds before/after PASS assertions, and two no-CLI cases prove missing-binding interception and escaping-child failure. Broad paths and empty protected_paths exist only in synthetic fixtures; production scope remains frozen and unchanged.'
}
records = ['002_regression', '003_governance', '004_bootstrap', '007_preservation']
if args.final: records = ['009_postcommit_tests', '010_postcommit_governance', '011_postcommit_bootstrap', '012_postcommit_preservation', '013_postcommit_entry', '014_final_governance']
artifacts = []
for name in records:
    path = B / 'raw' / (name + '.json'); data = path.read_bytes(); assert json.loads(data)['exit_code'] == 0, name
    artifacts.append({'ref': str(path.relative_to(R)), 'sha256': hashlib.sha256(data).hexdigest()})
rows = []
for finding in scan['findings']:
    assert finding['severity_kind'] == 'REVIEW' and finding['path'] in reasons, finding
    row = {key:finding[key] for key in ['path', 'layer', 'code', 'old_sha', 'new_sha']}
    row.update(finding_id=finding['id'], disposition='REVIEWED_NO_WEAKENING', reason=reasons[finding['path']], impact='Confirms only these exact strengthening changes against the fixed opening baseline; no test/acceptance deletion or production scope expansion.', reviewer='Codex primary implementer and verifier; same operator, no independent review', replacement_validation='Actual positive/negative regression, governance and opening preservation artifacts listed below. Retained assertions alone are not a semantic proof; the substantive file-specific review above applies.', authorization_source=baseline['authorization_source'], verification_artifacts=artifacts)
    rows.append(row)
args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps({'task_id':'V2-003', 'baseline_pin':scan['baseline_pin'], 'dispositions':rows, 'limitation':'Local same-operator technical review only; no exception grants or remote authority'}, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'dispositions':len(rows), 'output':str(args.output)}))
