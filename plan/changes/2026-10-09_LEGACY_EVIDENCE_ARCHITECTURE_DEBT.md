# Legacy Evidence Architecture Debt

**Document ID**: LEGACY-EVIDENCE-DEBT  
**Date**: 2026-10-09  
**Status**: REGISTERED_TECHNICAL_DEBT  
**Authority**: Governance Reconciliation H3

---

## Problem Statement

Historical V2-005 and V2-006 task closures (completed before governance reconciliation) used evidence files located in:
- `docs/reports/` (closure reports, ratification)
- `docs/` (implementation contracts, contract reviews)
- `src/`, `tests/`, `specs/` (direct code/test references)

The current plan validation system expects typed evidence records under `plan/validation/` with structured metadata.

This mismatch generates 59 legacy evidence architecture findings categorized as:
- `EVIDENCE_RECORD`: Evidence files outside plan/ package (22 findings)
- `LOCAL_REF`: References outside plan/ (21 findings)
- `EVIDENCE_ARTIFACT`: Missing artifact bindings (7 findings)
- `EVIDENCE_COVERAGE`: Missing typed coverage checks (6 findings)
- `TASK_SUITE_EVIDENCE`: Test results not linked to suite (2 findings)
- `TASK_NORMATIVE`: Normative specifications outside plan/ (1 finding)

Additionally, 3 current derived-artifact findings exist:
- `GENERATED_VIEW`: Stale or missing generated views (2 findings)
- `MANIFEST`: Stale file manifest (1 finding)

These derived-artifact findings are blocked by evidence_checks and would regenerate if legacy evidence were migrated.

Additionally, 2 execution packet absence findings exist:
- `EXEC_PACKET_ABSENT`: V2-005 and V2-006 have no genuine historical execution packets (registered debt)

These absence findings are truthful representations, not schema violations.

## Existing Real Evidence

Both V2-005 and V2-006 have **legitimate closure evidence**:

### V2-005 (v2.005-complete @ bd303e6)
- Implementation: `src/anovel/domain/identity.py`
- Tests: `tests/contract/test_v2_005.py`
- Schema: `specs/schemas/entity-identity.schema.json`
- Closure: `docs/reports/V2-005_FINAL_CLOSURE_REPORT.md` (8/8 steps VERIFIED)
- Ratification: `docs/reports/V2-005_FINAL_RATIFICATION.md`
- Tag: `v2.005-complete` @ bd303e64dab6475bd12b69d273afa6c64eaa38ad

### V2-006 (v2.006-complete @ bba1061)
- Implementation: `src/anovel/domain/relationship.py`
- Tests: `tests/contract/test_v2_006*.py` (447/447 PASS)
- Schema: `specs/schemas/entity-relationship.schema.json`
- Contract: `docs/V2-006_IMPLEMENTATION_CONTRACT.md` v1.0.1
- Closure: `docs/archive/v2-005-remediation/V2-006_FINAL_CLOSURE_CANDIDATE.md`
- Authorization: `docs/reports/V2-006_IMPLEMENTATION_AUTHORIZATION.md`
- External CI: Pipeline 2925763616 @ TomAy47287015/aianovelcc (GitLab, 899/899 tests, 6/6 gates)
- Tag: `v2.006-complete` @ bba1061ef27669ece55530bfdd846767b2fe21af

## What This Debt Does NOT Mean

❌ **Does NOT** invalidate V2-005/V2-006 historical closure  
❌ **Does NOT** require reimplementation  
❌ **Does NOT** allow future tasks to bypass typed evidence  
❌ **Does NOT** create V2-005/V2-006 governance bypass  

## What This Debt DOES Mean

✅ Historical evidence exists but **not in current typed format**  
✅ Tags and commits remain **authoritative closure proof**  
✅ Future work toward **evidence framework migration** is needed  
✅ New tasks must follow **current evidence standards**  

## Impact on V2-061

**V2-061 can proceed** because:
1. V2-005 and V2-006 are **legitimately closed** (immutable tags)
2. Machine backlog now correctly shows **CLOSED** status
3. Dependencies are **satisfied** by real implementations
4. Legacy evidence path structure **does not block new work**

## Disposition

### Immediate (H3 Scope)
✅ Mark V2-005/V2-006 as CLOSED in machine sources  
✅ Record evidence via immutable tag references  
✅ Align acceptance criteria  
✅ Fix backlinks  
✅ Register this technical debt  

### Deferred (Future Governance Task)
⏸ Migrate V2-005/V2-006 evidence to typed plan/validation/ structure  
⏸ Create retrospective certification packets (clearly marked as post-hoc)  
⏸ Establish evidence migration policy for closed tasks  
⏸ Audit evidence path conventions across all P0-P1 tasks  

## Validator Findings Classification

After H3.2 truth and validation closure:

```
Total findings: 64
├─ Legacy evidence architecture: 59
│  ├─ EVIDENCE_RECORD: 22 (files in docs/, src/, tests/)
│  ├─ LOCAL_REF: 21 (references outside plan/)
│  ├─ EVIDENCE_ARTIFACT: 7 (G-P0 superseding revalidation)
│  ├─ EVIDENCE_COVERAGE: 6 (missing typed checks)
│  ├─ TASK_SUITE_EVIDENCE: 2 (V2-005, V2-006)
│  └─ TASK_NORMATIVE: 1 (contract in docs/)
├─ Current derived-artifact consistency: 3
│  ├─ GENERATED_VIEW: 2 (blocked by evidence_checks)
│  └─ MANIFEST: 1 (blocked by evidence_checks)
└─ Execution packet absence (registered historical debt): 2
   ├─ EXEC_PACKET_ABSENT V2-005: no genuine historical execution packet exists
   └─ EXEC_PACKET_ABSENT V2-006: no genuine historical execution packet exists
```

The 2 EXEC_PACKET_ABSENT findings are registered debt, not schema violations. Absence records are truthful representations of historical fact, not fabricated execution packets.

## Acceptance Criteria for Debt Resolution

When this technical debt is addressed in the future, resolution requires:

1. ✅ V2-005/V2-006 evidence migrated to plan/validation/ structure
2. ✅ Retrospective certification packets created (clearly marked)
3. ✅ All evidence records have valid ref/revision/status fields
4. ✅ Evidence coverage checks implemented for code/tests/ci/acceptance
5. ✅ Generated views and manifest regenerate successfully
6. ✅ `validate_plan --check` returns PASS
7. ✅ Policy documented for handling closed tasks with legacy evidence
8. ✅ No fabrication of historical timestamps or execution contexts

## References

- V2-005 Final Closure: docs/reports/V2-005_FINAL_CLOSURE_REPORT.md
- V2-006 Final Closure: docs/archive/v2-005-remediation/V2-006_FINAL_CLOSURE_CANDIDATE.md
- V2-006 Implementation Contract: docs/V2-006_IMPLEMENTATION_CONTRACT.md
- Immutable tags: v2.005-complete, v2.006-complete
- H3 reconciliation commit: d49cdd8

---

**Status**: This debt is **registered and accepted** for deferred resolution. It does not block V2-061 contract refinement.
