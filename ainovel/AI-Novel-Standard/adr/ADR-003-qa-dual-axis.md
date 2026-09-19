# ADR-003: QA Dual-Axis Model

- **Status:** Accepted (Frozen, ANES v2 Phase 1)
- **Date:** 2026-06-30
- **Supersedes:** —
- **Superseded by:** —

## Context

Narrative quality has two fundamentally different kinds of check, and mixing
them in one gate makes a CI pipeline unrunnable. Schema validity and timeline
consistency are objective and cheap and give the same answer every time. "Is
the voice consistent?" and "is the pacing good?" are probabilistic judgments
made by an LLM-as-judge that legitimately fluctuate run to run.

If an LLM-judge result can block the build, the pipeline goes green today, red
tomorrow, green the day after — with no underlying change. The build becomes
noise.

## Decision

QA is organized on **two axes**, not one. The structural axis is the usual
pyramid (Unit = scene, Integration = volume, System = novel). The orthogonal
axis is the *nature* of the check:

```
                Deterministic (gate)              Evaluative (trend)
                pass/fail, cheap, every run        probabilistic, judge, sampled
Unit (scene)    schema check / invariant assert    voice consistency / scene tension
Integration(vol)timeline DAG / setup-payoff ledger pacing curve / transition smoothness
System (novel)  global invariant regression /      theme delivery / overall readability
                reference integrity
```

The hard rule:

- **Only Deterministic checks may block a build (gate).**
- **Evaluative judgments are trend-monitored and sampled only. They never hard-fail a build.**

Evaluative results feed dashboards, regression-trend alerts, and human review
queues — they inform, they do not gate.

## Consequences

- Gates are reproducible: a red build means a real, objective defect.
- LLM-judge jitter is contained to monitoring; it cannot stall delivery.
- Validation Contracts (ADR-002) are tagged Deterministic or Evaluative; the
  tag decides whether a failure gates or trends.

## Relationships

- Consumes Validation Contracts from [ADR-002](ADR-002-contract-layer.md).
- Asserts against invariants/facts defined under [ADR-006](ADR-006-registry-facts-only.md).
