# V2-004 Fourth Pipeline Fix - Current Status

**Date:** 2026-09-25 (Latest Update)  
**Phase:** Pre-fourth-push governance closure

---

## ✅ Completed Tasks

### 1. security-policy.yaml Restored ✅
- Created comprehensive security-policy.yaml
- Restored to V2-004 artifacts in implementation-backlog.yaml
- Updated execution-packet.yaml

### 2. CI Gates Improved ✅
- **STATIC:** ruff format/check + mypy (real tools, not fake checks)
- **SCHEMA_CONTRACT:** --output-dir dist/ci/schema (no plan/ modification)
- **SECRET_DEPENDENCY:** pip-audit added, production scan excludes fixtures

### 3. Enhanced test_delivery_gates.py ✅
Added 8 new tests:
- test_security_policy_yaml_is_required_artifact
- test_security_policy_yaml_exists
- test_static_gate_uses_real_tools
- test_secret_dependency_has_real_vulnerability_scanner
- test_ci_does_not_modify_plan_directory
- test_ci_references_exist
- test_production_scan_isolated_from_fixtures
- Enhanced test_no_failure_swallowing_in_p0_jobs

### 4. V2-001/002/003 Input Reconciliation ✅
- 8 reconciled snapshots created
- RECONCILIATION_NOTE.md documented

### 5. Configuration Files ✅
- pyproject.toml: added ruff, mypy
- ruff.toml: created

---

## 🚨 Blocking Issues

### 1. V2-003.2 Evidence Artifacts Missing ❌
**Status:** BLOCKED - requires decision

Three evidence artifacts do not exist in Git history:
- V2-003.2_IMPLEMENTATION_REPORT.md
- V2-003.2-H1_HOTFIX_REPORT.md  
- V2-003.2-H2_VERIFICATION_CLOSURE.md

**Options:**
- Mark evidence as ARTIFACT_LOST
- Reconstruct if possible
- Accept incomplete historical evidence

**Documented in:** `plan/validation/execution/V2-003/supplementary/ARTIFACTS_ISSUE.md`

### 2. uv.lock Not Updated ❌
**Status:** READY TO FIX

Dependencies added to pyproject.toml but not locked:
- ruff >=0.8,<1
- mypy >=1.11,<2

**Next:** Install uv 0.12.17 and run `uv lock`

---

## 📋 Remaining Tasks

### Immediate
1. **Decision on V2-003.2 artifacts** (user input required)
2. **Lock dependencies:** uv lock, verify with uv sync --frozen
3. **Run --write-views:** After all machine changes frozen
4. **V2-004 packet re-freeze:** Update all hashes, manifest, scope
5. **Full local validation:** ALL tests PASS

### Before Fourth Push
- validate_plan --check: PASS
- All tests: PASS
- uv sync --frozen: PASS
- No WIP commits

---

## Current Changes (13 files)

```
M  .gitlab-ci.yml
M  plan/machine/implementation-backlog.yaml
M  plan/validation/execution/V2-004/execution-packet.yaml
M  pyproject.toml
M  tests/contract/test_delivery_gates.py
A  security-policy.yaml
A  ruff.toml
A  docs/V2-004_FOURTH_FIX_PROGRESS.md
A  plan/validation/execution/RECONCILIATION_NOTE.md
A  plan/validation/execution/V2-003/supplementary/ARTIFACTS_ISSUE.md
A  plan/validation/execution/V2-00*/inputs-reconciled/*.txt (8 files)
```

---

## Next Steps

**Awaiting user decision on V2-003.2 artifacts to unblock.**

Once decided, continue with:
1. uv lock
2. --write-views
3. Packet re-freeze
4. Full validation
5. Fourth push
