# V2-004 Fourth Pipeline Fix - Progress Report

**Date:** 2026-09-25  
**Status:** IN PROGRESS

---

## ✅ Completed

### 1. security-policy.yaml Restored
- ✅ Created security-policy.yaml with proper structure
- ✅ Restored to implementation-backlog.yaml artifacts
- ✅ Updated execution-packet.yaml expected_outputs and allowed_paths
- ✅ Added pyproject.toml and uv.lock to allowed_paths for scope expansion

### 2. STATIC Gate Semantics Implemented
- ✅ Updated .gitlab-ci.yml STATIC job to use ruff (format + lint) and mypy (typecheck)
- ✅ Added ruff and mypy to pyproject.toml dependency-groups
- ✅ Created ruff.toml configuration
- ✅ Removed fake checks (grep, || echo)

### 3. SCHEMA_CONTRACT Output Fixed
- ✅ Updated .gitlab-ci.yml to use --output-dir dist/ci/schema
- ✅ Removed plan/validation/ modification
- ✅ Removed || true from artifact preservation

### 4. SECRET_DEPENDENCY Improved
- ✅ Separated production scan from fixture testing
- ✅ Added pip-audit for real dependency vulnerability scanning
- ✅ Production code excludes tests/fixtures from secret scan
- ✅ Dependency scan warns but continues for P0

### 5. V2-001/002/003 Input Reconciliation
- ✅ Created inputs-reconciled/ directories
- ✅ Created 8 reconciled snapshots (V2-001: 2, V2-002: 3, V2-003: 3)
- ✅ Documented reconciliation in RECONCILIATION_NOTE.md
- ✅ Preserved original packets unchanged

---

## ⚠️ Remaining Critical Tasks

### 6. Update uv.lock with New Dependencies
**Status:** BLOCKED (uv not in PATH)  
**Action:** Need to run `uv sync` to add ruff and mypy to lock file  
**Impact:** CI will fail if dependencies not locked

### 7. V2-003.2 Evidence Artifacts Immutable Snapshots
**Status:** NOT STARTED  
**Files:** 
- docs/V2-003.2_IMPLEMENTATION_REPORT.md
- docs/V2-003.2-H1_HOTFIX_REPORT.md  
- docs/V2-003.2-H2_VERIFICATION_CLOSURE.md

**Action:** Must find historical Git blobs matching recorded hashes, not recalculate

### 8. Run --write-views
**Status:** NOT STARTED  
**Action:** 
```bash
.venv/bin/python3 plan/scripts/validate_plan.py --write-views
```
**Updates:** PHASE_TASK_REGISTRY.md, FILE_MANIFEST.json

### 9. V2-004 Packet Re-Reconciliation
**Status:** NOT STARTED (depends on #6, #8)  
**Action:**
- Recalculate input hashes after backlog.yaml change
- Update plan_manifest_sha256 after --write-views
- Recreate input snapshots
- Update change_review scope_ref if needed

### 10. Enhanced test_delivery_gates.py
**Status:** NOT STARTED  
**New tests needed:**
- Test STATIC uses real ruff/mypy (not fake checks)
- Test SECRET_DEPENDENCY has pip-audit
- Test artifacts not silently deleted from backlog.yaml
- Test CI doesn't modify plan/ directory
- Test no || echo in hard gates

---

## Current File Changes

```
M  .gitlab-ci.yml (STATIC, SCHEMA_CONTRACT, SECRET_DEPENDENCY updated)
M  plan/machine/implementation-backlog.yaml (security-policy restored)
M  plan/validation/execution/V2-004/execution-packet.yaml
M  pyproject.toml (ruff, mypy added)
A  security-policy.yaml
A  ruff.toml
A  plan/validation/execution/RECONCILIATION_NOTE.md
A  plan/validation/execution/V2-00*/inputs-reconciled/*.txt (8 files)
```

---

## Next Immediate Steps

1. Lock dependencies (uv sync)
2. Run --write-views  
3. Re-reconcile V2-004 packet
4. Handle V2-003.2 evidence (complex)
5. Enhance tests
6. Local validation: 14/14 PASS
7. Commit and push

---

**Current blocker:** uv not available to lock new dependencies  
**Workaround needed:** Install uv or use alternative method
