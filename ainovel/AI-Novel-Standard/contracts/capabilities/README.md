# Capability Contract format (ANES v2, ADR-002)

- **Status:** Frozen (format v1.0)
- **Governed by:** [ADR-002](../../adr/ADR-002-contract-layer.md), [ADR-003](../../adr/ADR-003-qa-dual-axis.md), [ADR-005](../../adr/ADR-005-execution-layer-split.md)
- **Location:** `contracts/capabilities/<name>.capability.yaml`

## Purpose

A Capability Contract is the coarse-grained contract (ADR-002): *what an agent
can do*, declared as data so the Runtime and downstream agents reference it
instead of a bare `capability` string. Each contract names its input artifact,
its output artifact, and — critically — the **determinism** and **idempotency**
metadata that make retry/cache/rollback engineerable (ADR-002, ADR-005).

## Fields

```yaml
contract_format: "1.0"
capability: <PascalCaseName>      # the value a TaskDefinition.capability must match
description: <one line>
input:
  artifact: <artifact contract id>   # e.g. anes:contract:task-package:1.0
  constraints:                        # optional input semantics (enforced by Runtime)
    seed_types: [CHR, EVT]            # type codes a seed may have (omit = any)
    min_seeds: <int>                  # minimum seed count (default 1)
    max_seeds: <int>                  # maximum seed count (omit = unbounded)
    required_extra: [<key>, ...]      # keys that must be present in task.extra
output:
  artifact: <artifact name or contract id>
  kind: prose | structured           # prose = human text; structured = schema'd
  schema: <filename>                  # output Artifact Contract (in contracts/) the output must satisfy
determinism: deterministic | generative
  # deterministic: same input => same output (validation, compilation)
  # generative   : output legitimately varies (writing) — never gates a build (ADR-003)
idempotency:
  safe_to_retry: <bool>              # re-running cannot corrupt state
  cacheable: <bool>                  # output may be cached & replayed
retry:
  max_attempts: <int>
  backoff: none | linear | exponential
gating: deterministic | evaluative   # which QA axis judges this output (ADR-003)
notes: <free text>
```

## Rules

- A `TaskDefinition.capability` MUST match a `capability` declared by some
  Capability Contract; the Runtime rejects unknown capabilities.
- `input.constraints`, when present, are enforced by the Runtime BEFORE compile:
  a task whose seeds violate `seed_types`/`min_seeds`/`max_seeds`, or that omits
  a `required_extra` key, is rejected. This makes a task semantically valid, not
  merely name-valid (the seeds match what the capability can actually consume).
- `determinism: generative` outputs are judged on the **evaluative** axis only;
  they MUST NOT be a deterministic build gate (ADR-003).
- `input.artifact` referencing the Task Package contract pins the consumer to
  the authored envelope, not the Runtime compiler's internals (§ contract layer).
- `output.schema` declares the Artifact Contract the capability's output must
  satisfy. The Runtime loads it FROM the capability contract — it must never be a
  constant hardcoded in execution code, so a new capability cannot drift from
  (or silently reuse) the wrong output schema.
