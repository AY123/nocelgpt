# Governance Baseline Change: Add V2-061 to M1

**Date**: 2026-10-09  
**Change Type**: Milestone membership correction  
**Authority**: H3.1 Current Authority Micro-Closure

---

## Change

Updated `governance-baseline.yaml` M1 (Narrative Kernel) `required_tasks` to include V2-061:

**Before**:
```yaml
M1:
  required_tasks:
  - V2-005
  - V2-006
  - V2-007
  - V2-008
```

**After**:
```yaml
M1:
  required_tasks:
  - V2-005
  - V2-006
  - V2-061
  - V2-007
  - V2-008
```

## Reason

V2-061 (Character Knowledge & Intent Core) is a P1 phase task and belongs to the Narrative Kernel milestone. The omission was an oversight in H3 that incorrectly claimed M1 consistency while V2-061 was missing from both `milestones.yaml` and `governance-baseline.yaml`.

## Impact

- M1 milestone membership now matches P1 phase membership
- All P1 tasks are correctly represented in the Narrative Kernel milestone
- No change to CI requirements, gate definitions, or enforcement policy
- No weakening of governance baseline

## Validator Update Required

New SHA-256 for `plan/machine/governance-baseline.yaml`: `a7b1a29c9495d19615f3a5c758dcb6ca7046113a43a80b8c7749319f191c2eef`

Update `APPROVED_GOVERNANCE_BASELINE` in `plan/scripts/validate_plan.py`.

---

**Approved By**: H3.1 Current Authority Micro-Closure  
**Commits**: H3.1 final commit
