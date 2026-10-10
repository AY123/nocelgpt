# V2-004 Repository Baseline Report
## Read-Only PREPARE Phase Entry

**Date:** 2026-09-25  
**Phase:** PREPARE (Read-Only)  
**Engineer:** Claude Opus 5.5

---

## Repository State

### Branch and Revision

```
branch: dev_cc
HEAD: 73e029b353034727540047a8c08bf120cd2e80f1
```

### Worktree Status

```
M  plan/validation/plan-validation.json (expected from V2-003.2)
M  审核报告.txt (user file, will preserve)
```

**Clean except for expected artifacts from V2-003.2 completion.**

### Recent Commits

```
73e029b fix(V2-003.2): correct evidence binding to conform to schema
ebd5bb6 docs(V2-003.2): correct evidence integrity and machine binding
7cbd9ae docs(V2-003.2-H2): bind verification closure evidence
efab339 test(V2-003.2-H2): add verification closure tests
109eb0d docs(V2-003.2-H1): bind hotfix evidence and final status
406977f fix(V2-003.2-H1): harden PREPARE content identity enforcement
3ad4fef docs(V2-003): bind V2-003.2 closure evidence and handoff
af63cb7 fix(V2-003): close PREPARE semantic and collection-control authorization gaps
fbab87d governance(review): add external review triage contracts
882d0cd docs(V2-003): seal confirmed review corrections and handoff
```

---

## V2-004 Task Status

### From implementation-backlog.yaml

```yaml
task_id: V2-004
title: Secret and dependency CI gates
phase: P0
priority: P0
status: OPEN
execution_packet_ref: null
readiness: READY_TO_START
```

### Acceptance Criteria (from backlog)

1. 适用硬门禁失败使 CI 失败
2. 无害 Secret 与违规依赖夹具被阻断
3. PostgreSQL job 实际连接且当前提交 CI 证据可查
4. 远程合并保护的实际状态可核验
5. 普通实施身份不能同时修改实现、削弱保护和批准例外
6. 治理校验器/基线/测试变更不能由同次改动移除检查后自行放行

### Artifacts (expected)

```
.gitlab-ci.yml
security-policy.yaml
tests/contract/test_delivery_gates.py
```

---

## CI Gates Status (from ci-gates.yaml)

### P0 Gates (Must Implement)

```yaml
STATIC: NOT_IMPLEMENTED, allow_failure: false
UNIT: NOT_IMPLEMENTED, allow_failure: false
SCHEMA_CONTRACT: NOT_IMPLEMENTED, allow_failure: false
ARCH_FITNESS: NOT_IMPLEMENTED, allow_failure: false
SECRET_DEPENDENCY: NOT_IMPLEMENTED, allow_failure: false
POSTGRES_ENV: NOT_IMPLEMENTED, allow_failure: false
```

### Future Gates (Must NOT Implement)

```yaml
CANON_CAS_IDEMPOTENCY: P2, NOT_IMPLEMENTED
DETERMINISTIC_E2E: P7, NOT_IMPLEMENTED
GENRE_SMOKE: P8, NOT_IMPLEMENTED
LIVE_PROVIDER: P10, NOT_IMPLEMENTED
```

**Constraint:** Future gates must remain NOT_IMPLEMENTED with their activation_phase preserved.

---

## Current State

### Execution Packet

```
Status: DOES NOT EXIST
Location: plan/validation/execution/V2-004/ (expected)
Required: YES (for IN_PROGRESS)
```

### GitLab CI

```
.gitlab-ci.yml: DOES NOT EXIST
Status: NOT_IMPLEMENTED
```

### Delivery Tests

```
tests/contract/test_delivery_gates.py: DOES NOT EXIST
Status: NOT_IMPLEMENTED
```

### Security Policy

```
security-policy.yaml: DOES NOT EXIST
Status: NOT_IMPLEMENTED
```

---

## Dependencies Status

### Prerequisite Tasks

```
V2-001: IMPLEMENTED
V2-002: IMPLEMENTED  
V2-003: IMPLEMENTED
```

**All dependencies satisfied.**

### Test Suites

From test-catalog.yaml:
```
AT-V2-001: IMPLEMENTED
AT-V2-002: IMPLEMENTED
AT-V2-003: IMPLEMENTED
AT-V2-004: PLANNED (target: tests/contract/test_delivery_gates.py)
```

---

## Python Environment

### From pyproject.toml

```
python = ">=3.12,<4"
requires-python = ">=3.12"
```

### Current Lock

```
uv.lock exists
Python 3.12.14 (from V2-003 evidence)
uv 0.12.17 (from V2-003 evidence)
```

### Pytest Configuration

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--strict-config --strict-markers -ra"
```

---

## Normative Specifications

V2-004 references:
1. 07_PLATFORM_SECURITY_AND_DELIVERY.md
2. 09_TASK_EXECUTION_GUIDE.md
3. PHASE_0_REPOSITORY_BOOTSTRAP_EXECUTION.md
4. AI_EXECUTION_PROTOCOL.md

All exist and have been read.

---

## V2-003.2 Transferred Gaps

From V2-003.2 final status:

### F-001: PREPARE E2E Integration

```
Status: NOT YET VERIFIED
Reason: Test infrastructure limitation (no PREPARE packets)
Required: End-to-end PREPARE action tests
Owner: V2-004 (if feasible)
```

### F-002: Authorization Chain E2E

```
Status: NOT FULLY TESTED
Reason: Structure validated, full chain not integrated
Required: apply_dispositions() E2E verification
Owner: V2-004 (if feasible)
```

---

## Remote GitLab State

### Access Status

```
API Access: UNKNOWN (will investigate in PREPARE)
Project: UNKNOWN
Branch Protection: UNKNOWN
Pipeline History: UNKNOWN
Runner Availability: UNKNOWN
```

**Must verify during PREPARE without making changes.**

---

## Constraints and Principles

### No Fabricated Evidence

- ✅ Local pytest PASS ≠ trusted CI PASS
- ✅ Committed JSON/YAML ≠ remote CI evidence
- ✅ Pipeline URL string ≠ verified pipeline provenance
- ✅ Branch protected configuration ≠ effective permission isolation

### Implementation Discipline

- ✅ P0 gates only (STATIC, UNIT, SCHEMA_CONTRACT, ARCH_FITNESS, SECRET_DEPENDENCY, POSTGRES_ENV)
- ✅ allow_failure: false for all P0 gates
- ✅ Future gates remain NOT_IMPLEMENTED
- ✅ No weakening of existing tests/ACs/gates/thresholds
- ✅ Locked dependencies (uv sync --frozen)

### Evidence Requirements

- ✅ Typed evidence records (not Markdown as evidence)
- ✅ Current revision binding
- ✅ Real CI provenance verification
- ✅ Honest state transitions

---

## PREPARE Phase Objectives

1. **Establish Execution Packet**
   - Create plan/validation/execution/V2-004/execution-packet.yaml
   - Bind inputs, allowed_paths, acceptance criteria
   - Freeze scope for IMPLEMENT

2. **GitLab Capability Investigation**
   - Check GitLab API access (read-only)
   - Verify project, branch, runner availability
   - Identify protection/permission boundaries

3. **CI Design**
   - Design .gitlab-ci.yml structure
   - Plan P0 gate implementations
   - Plan artifact generation
   - Plan provenance verification

4. **Test Design**
   - Design test_delivery_gates.py structure
   - Plan negative fixtures (harmless)
   - Plan provenance verification tests

5. **Scope Freeze**
   - Define allowed_paths precisely
   - Identify required changes
   - Document out-of-scope items

---

## Stop Conditions

Will STOP if encountering:
- ❌ Requires changing frozen architecture
- ❌ Requires weakening minimum P0 gates
- ❌ Requires real secret exposure
- ❌ Requires destructive remote permission tests
- ❌ Requires unapproved GitLab permission expansion
- ❌ Cannot authenticate pipeline provenance
- ❌ CI runner unavailable with no alternative
- ❌ Security scanner requires unacceptable exposure

---

## Next Steps

**PREPARE Phase Actions:**
1. Read remaining normative specs in detail
2. Investigate GitLab state (read-only)
3. Design execution packet
4. Design CI structure
5. Design tests
6. Create execution packet
7. Request approval to enter IMPLEMENT

**Status:** READY TO BEGIN PREPARE

---

**Report Complete.**  
**Phase:** PREPARE (Read-Only Investigation)  
**No implementation mutations permitted in PREPARE.**
