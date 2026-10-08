# V2-004-P0-MAINLINE-UNBLOCK-001 — Scope and Impact

This is a V2-004 local P0 engineering sub-work-package, authorized by the latest direct human instruction transcribed in `AUTHORIZATION.md`. It does not create V2-005 or any new backlog task. The primary checkout is `dev_gpt @ 9fe51abf5ba2e050b7f48204f5c26927ace712af`; existing 29 worktree differences and ignored evidence are preserved, not attributed to this implementation.

## Authorized implementation paths

- `scripts/ci/secret_exceptions.py`: strict schema/authority/identity validator and exact finding consumer.
- `scripts/ci/check_security.py`: integration after raw scanner results, preserving fail-closed scanning and detected findings.
- `tests/contract/test_secret_exceptions.py`: positive and negative controls, collected by the existing unit gate.
- `docs/V2-004_SECRET_EXCEPTION_CONSUMER.md`: implementation, formats, usage and limits.
- `plan/validation/execution/V2-004/mainline-unblock-20261007/`: this execution record, schemas, exact known-finding manifest, pending authority and single Owner input design.
- `security-policy.yaml`: only if required to bind the exact consumer; no unrelated setting change.
- `dist/validation/v2004-mainline-unblock-20261007/`: new local test/diff/runtime evidence; remains outside the normative plan manifest.

No `.gitlab-ci.yml`, `.gitleaks.toml`, runner/trusted-CI file, existing tests, package dependency, canonical disposition, existing execution packet/context, machine backlog/test catalog/state or historical evidence change is authorized here. If later implementation requires any unlisted change, stop that specific change and report it.

## Baseline, historical evidence and authority

The existing canonical 45 findings remain historical OPEN records. The 38 non-Owner exact exception requests and 7 Owner-required historical findings are disjoint. This task accounts for the fixed known set through a new exact identity/disposition layer, without editing that canonical or declaring findings CLOSED. SF-037 remains independently unresolved; it must not be semantically assigned to a credential group.

Stop H2/H3/H4 credential evidence acquisition: no key screenshot, deletion log, service event time, ownership supplement or historical-key investigation. Preserve acquired evidence without turning old assertions or example paths into verified facts. A single exact-set Owner risk-acceptance input replaces additional credential collection for the historical credential set. Input design is not execution of approval; no credential value is requested or copied.

Exception approval, authority verification, consumer application and finding closure are separate states. Do not manufacture approval, expiry, service status or a rotation/revocation claim. A strict consumer may make an accounted-for security run pass only when the actual exact set and valid authority contract pass. Missing authority remains a technical failure with explicit remaining blockers.

## Exact consumer boundaries

Match finding identity, scanner rule, repository/path identity, worktree/history target, applicable revision/baseline and authority record. Retain source/fingerprint/content identities needed to reject drift. Count is never a match criterion. An additional finding must not be accepted even if total count stays at or below 45.

No global/rule/path/filetype suppression, broad historical ignore, scanner coverage reduction, gate deletion, threshold weakening or `allow_failure` change. All six mandatory gates remain mandatory. Raw detection results must remain separate from approved-and-consumed results.

Positive/negative matrix covers exact approved consumption, new secret, path/fingerprint drift, scope mismatch, absent authority, malformed approval, unused approval reporting, and additional finding. Unknown or malformed state must fail closed. Approved test fixtures are local controls, not actual production approval.

## Fixed Git pin constraint

The existing `task_execution.py` IMPLEMENT path requires a packet-bound fixed Git scope/review baseline. Its scope/review files are read from Git objects and cannot be created truthfully by editing a candidate worktree file. The historical scope-ci-v3 baseline starts at `6ed09939bdc7715fd582338675cd0443777aac50`, has no preserved opening dirty snapshot, and does not authorize this work package's new test/docs paths. It cannot be reused as a claim that this new package has passed exact scope review.

The preceding human instruction froze the existing 29 worktree differences and prohibited their commit. This task authorizes bounded local implementation and tests, with no push or remote actions; no new immutable review pin is created in this run, and the old packet/backlog is preserved. Thus a new committed fixed scope/review pin cannot be constructed within this authorization. The new packet truthfully records `action: IMPLEMENT`, `change_review: null`, and `TASK_ENTRY_FIXED_PIN = NOT_SATISFIED`. The latest direct human task instruction authorizes this bounded local implementation and tests; it does not weaken or modify the task-entry program. No PREPARE relabeling, invented commit, synthetic review pin or task-entry PASS is allowed.

The exact local diff, source hashes, preserved opening differences and test outputs support subsequent independent review. A future immutable exact revision / fixed-pin or equivalent protected approval binding remains a separate prerequisite for final trusted CI. Do not infer final acceptance from this local packet or local tests.

## Acceptance mapping and impact

- AT-V2-004-01 / 02: mandatory failure propagation and new-secret/invalid-exception rejection, plus valid exact evidence acceptance.
- AT-V2-004-04 / 08: no mandatory-gate deletion or widening of scanner exclusion; review actual before/after source and policy diff.
- AT-V2-004-05 / 06: local artifacts report commands, source identities and failures, but no new remote provenance or trusted execution is claimed.
- AT-V2-004-07: authority reference validation is implemented/tested; actual remote identity/least-privilege experiments are neither executed nor inferred from local fixtures.
- AT-V2-004-03: no new PostgreSQL infrastructure or remote job is needed here; existing scenario remains mandatory for final same-SHA acceptance.

V2-004 has no required ADR in the current backlog and decision register. ADR-001 remains ACCEPTED for the existing runtime/locking environment; no dependency/runtime change or future-domain interface decision is introduced.

## Exit and stop

Produce implementation diff, consumer schema, authority/disposition schema, test matrix, local results, remaining blockers and final trusted-CI candidate assessment. Do not run remote CI, change GitLab, activate runner, commit/push/MR or invoke a paid Provider. Do not independently claim approval/review on the basis of parallel shared-workspace agents. Complete local work and STOP for independent review; V2-004 stays IN_PROGRESS and P0 stays NOT_VERIFIED.
