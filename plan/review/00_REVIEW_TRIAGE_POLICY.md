# External Review Triage Policy

**Version:** 1.0  
**Status:** NORMATIVE  
**Authority:** Plan-level operational policy

---

## 1. Purpose

This policy governs how external audit reports, security reviews, and third-party assessments are triaged, validated, and selectively adopted into the project.

External reviews are valuable inputs but are not authoritative sources of truth. All findings must be independently verified against current repository state, normative specifications, and project evidence before adoption.

---

## 2. Core Principles

### 2.1 Audit Report Is Input, Not Truth

External review reports are classified as:

```
REVIEW INPUT
```

They are **not**:
- SSOT (Single Source of Truth)
- Normative specifications
- ADRs (Architecture Decision Records)
- Acceptance evidence
- Implementation authorization

### 2.2 Triage Before Implementation

**No code, test, specification, gate, execution packet, or machine SSOT modification is permitted until:**

1. A formal **Finding Triage Matrix** is completed
2. An **Approved Remediation Plan** is produced
3. Explicit **implementation authorization** is granted

### 2.3 No Fabricated Evidence

All claims about repository state, code behavior, test results, or CI status must be derived from:
- Actual tool invocations, OR
- Explicitly provided user materials

When verification is not possible, use:
- `NO_TOOL_ACCESS`
- `CANNOT_VERIFY`
- `NEEDS_MORE_EVIDENCE`

**Never simulate, guess, or fabricate** tool outputs, test results, or evidence.

---

## 3. Findings vs Observations

### 3.1 Findings

A **Finding** describes:
- A potential defect
- A real risk
- A constraint violation
- A protection gap
- Behavior that could lead to errors

Findings enter the formal **Finding Triage Matrix**.

### 3.2 Observations

An **Observation** is:
- A design confirmation
- Quality confirmation of already-fixed issues
- Expected future work
- Background context
- Non-actionable notes

Observations are tracked separately and **do not count** toward finding totals, confirmation rates, or adoption metrics.

---

## 4. Evidence Levels

Evidence levels are determined by **evidence type**, not model confidence:

| Level | Definition | Examples |
|-------|------------|----------|
| **E0** | Report claim only | No independent verification |
| **E1** | Path/code exists | File found, but issue not reproduced |
| **E2** | Deterministic proof | Static analysis, reproduction, fixture |
| **E3** | Execution evidence | Test run, runtime log, trusted CI output |
| **E4** | Real-world evidence | Production data, user reports, market signals |

Even with high confidence, without actual execution evidence, maximum level is typically **E2**.

---

## 5. Five-Dimensional Triage

Every Finding must be evaluated across five dimensions:

### 5.1 Verification

```
CONFIRMED
PARTIALLY_CONFIRMED
ALREADY_FIXED
FALSE_POSITIVE
THEORETICAL_ONLY
NEEDS_MORE_EVIDENCE
CANNOT_VERIFY
```

### 5.2 Severity

Select **one** value (no combinations):

```
BLOCKER
P0
P1
P2
P3
N/A
```

### 5.3 Recommendation Validity

```
VALID
PARTIAL
OVERENGINEERED
WRONG_SOLUTION
NOT_NEEDED
```

### 5.4 Decision

```
ADOPT_NOW
ADOPT_WITH_MODIFICATION
DEFER
TRACK_ONLY
REJECT
```

### 5.5 Owner

```
CURRENT_TASK
V2-xxx (specific task)
FUTURE_PHASE
ADR
PLATFORM
NONE
```

---

## 6. Logical Consistency Rules

### 6.1 Prohibited Combinations

The following combinations are **logically inconsistent** and must fail validation:

```
FALSE_POSITIVE + ADOPT_NOW          → FAIL
ALREADY_FIXED + ADOPT_NOW           → FAIL
CANNOT_VERIFY + ADOPT_NOW           → FAIL
NEEDS_MORE_EVIDENCE + ADOPT_NOW     → FAIL
```

### 6.2 Problem vs Solution

A Finding may be:

```
CONFIRMED (problem exists)
+ OVERENGINEERED (proposed solution is excessive)
+ ADOPT_WITH_MODIFICATION (use simpler fix)
```

This separation is valid because **problem validity ≠ solution validity**.

---

## 7. P0/BLOCKER Requirements

### 7.1 Target Invariant Mandatory

Every P0 or BLOCKER Finding must define a **testable target invariant**:

```
Invariant: <system behavior constraint that must hold after fix>
```

Example:
```
PREPARE SHALL NOT leave Git-visible persistent implementation
changes in repository-controlled state.
```

### 7.2 Adversarial Challenge Mandatory

P0/BLOCKER fixes must undergo **invariant-oriented adversarial validation**:

- Test goal: Can another **legal path** reach the **prohibited final state**?
- Not just: "Does the original PoC still work?"

Adversarial tests must verify:
1. Different parameters
2. Different actions/modes
3. Different callers
4. Legal but malicious input combinations
5. CLI omissions
6. Packet-provided values

If any legal alternative path violates the invariant:
```
REMEDIATION_INCOMPLETE → Fix must be revised
```

---

## 8. Scope Gate

Even if a Finding is **CONFIRMED**, it does not automatically expand current task scope.

Example:
```
Verification: CONFIRMED
Current Task: V2-003
Owner: V2-004
Decision: DEFER
```

This is a **valid and correct** outcome.

---

## 9. No Self-Weakening

Remediation must not:
- Delete failing tests
- Add `skip` or `xfail`
- Lower thresholds
- Expand excludes
- Delete or weaken ACs
- Remove gates
- Change `ERROR` to `WARNING`
- Change `UNKNOWN` to `PASS`
- Modify baselines to self-approve

If existing rules are genuinely incorrect, enter formal **Rule Revision** or **ADR** process.

---

## 10. Status Discipline

Local implementation and local test completion **do not automatically equal**:
- `VERIFIED`
- `CLOSED`
- Gate satisfaction

Status must follow project-defined state machines and be backed by:
- Required evidence types
- CI gates (when applicable)
- Acceptance criteria

---

## 11. Triage Lifecycle

```
External Audit Report
        ↓
Independent Verification
        ↓
Finding Triage Matrix
        ↓
Approved Remediation Plan
        ↓
Authorization Gate
        ↓
Implementation
        ↓
Regression + Adversarial Validation
        ↓
Evidence Binding
```

---

## 12. Machine Enforcement

Key rules from this policy are enforced by:
- `plan/scripts/review_triage_checks.py` (validator)
- `plan/schemas/review-triage-report.schema.json` (schema)
- `tests/contract/test_review_triage_policy.py` (tests)

Machine validators fail closed on:
- Invalid verification/decision combinations
- Fake E3 without execution evidence
- P0 without target invariant
- P0 without adversarial validation
- Observations counted as Findings

---

## 13. Authority Hierarchy

When conflicts arise:

```
Current Normative Specifications
  > Machine SSOT
  > Accepted ADRs
  > Current Implementation
  > Tests & Evidence
  > Historical References
  > External Audit Reports
  > Model Opinions
```

---

## Final Principle

The goal is not to:
- Accept the most audit recommendations
- Reject the most audit recommendations

The goal is to:

> **Adopt only those changes supported by current facts and evidence, that genuinely reduce risk, fit current architecture and task scope, where benefits exceed complexity, and where candidate solutions maintain target invariants and solve root causes rather than merely blocking example PoCs.**

---

**Document Status:** NORMATIVE  
**Last Updated:** 2026-09-25  
**Related:** `01_DAILY_REVIEW_PROMPT.md`, `review-triage-policy.yaml`
