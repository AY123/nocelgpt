# V2-004 exact secret exception consumer

Current local delta (2026-10-15): the active candidate ledger contains52 exact identities:43 precise exceptions and9 historical risk-accepted rule hits. The original45 rows and their disposition kinds are unchanged; five public identifiers and two rule hits of one historical token-shaped source line were explicitly approved by the Project Owner. All52 findings remain OPEN. The original exact expiry2027-01-06T06:07:49Z is retained. Active policy uses four immutable authority records under `mainline-unblock-20261007/history-delta-20261015/`. The original45-item canonical, old approvals and pending inputs remain historical evidence. This local candidate has no final same-SHA trusted CI acceptance.

Work package: `V2-004-P0-MAINLINE-UNBLOCK-001`, 2026-10-07. Local implementation
and tests only; no remote CI, project setting change, runner start, push or P0
acceptance. Credential evidence acquisition under H2/H3/H4 is stopped.

## Behavior

The existing pinned Gitleaks invocation still scans every tracked worktree file
and the complete Git history with the default rules, an empty ignore file and
candidate inline allowances disabled. No scanner exclusion or CI gate is changed.
`check_security.py` consumes exact dispositions **after** detection. Its report
retains raw per-target exit codes and `raw_status`, alongside `exception_consumption`.
The six mandatory jobs and `allow_failure=false` remain unchanged. The new test
file is automatically collected by the existing UNIT directory command and is
format/lint checked separately during local validation. Gate commands and the
accepted remote verifier command contract remain unchanged.

The new ledger explicitly enumerates the canonical 45 identities: 38 non-Owner
precise exceptions and 7 historical findings bound to one Owner risk input.
Existing canonical dispositions and H3/H4 evidence are unchanged; their OPEN
state is not rewritten. SF-037 remains unresolved, without credential grouping.
Risk acceptance is neither revocation evidence nor finding closure.

## Machine contracts

The files under `plan/validation/execution/V2-004/mainline-unblock-20261007/` are:

- `finding-exception-consumer.schema.json`: repository binding, ledger ref/hash,
  and zero or more fixed authority Git revision/ref/blob/SHA anchors.
- `finding-disposition.schema.json`: exact identity, finding ID, classification,
  disposition and authority ID. Unknown fields are rejected.
- `finding-approval.schema.json`: exact authority scope, actor/role, decision,
  approval timestamp, expiry, reason, approved ledger SHA-256, explicit approval
  kind and enumerated identity hashes.
- `KNOWN_FINDING_DISPOSITIONS.json`: new accounted-for identity layer, with
  canonical source ref/hash and per-finding canonical identity hashes.
- `EXCEPTION_APPROVAL_INPUT.json`: PENDING scope for the exact 38 findings.
- `OWNER_RISK_ACCEPTANCE_INPUT.json`: one PENDING input for the exact 7 historical
  findings. The previously stated Owner is retained; no screenshots, service
  logs, credential values, ownership supplements or historical-key investigation
  are requested. Only the bounded risk decision and approval period are missing.

Pending inputs are not trusted anchors. They do not enable scanner consumption.
No approval timestamp, expiry or authenticated actor evidence is invented.

## Exact identity and baseline

Each identity binds repository/project, scanner rule, worktree/history target,
strict repository-relative path, line, historical commit where applicable,
source revision, source file SHA-256, Git blob OID, source line SHA-256 and
normalized scanner fingerprint SHA-256. Numeric line values reject booleans.
Absolute paths, traversal, path wildcards, backslashes and control characters
are rejected.

Gitleaks 8.21.2 constructs worktree fingerprints from File/RuleID/StartLine;
history adds Commit. The consumer checks that scanner structure exactly, then
removes only the actual temporary-copy prefix. The original scratch-dependent
hashes remain in the historical canonical. Worktree content identity is computed
from the copied bytes actually scanned, avoiding a later read of mutable source.

The ledger uses the existing e927 baseline. HEAD must descend from that baseline,
and the exact source bytes/blob/line identity must still match. This permits a
future implementation revision without a self-referential commit SHA in the
ledger; it does not authorize any new finding at that revision. Changing path,
fingerprint, source bytes or worktree/history identity fails exact matching.

## Authority boundary

The consumer reads approved authority records only from `git show`-equivalent
immutable Git objects whose full revision, path, blob and SHA are explicitly
pinned in `security-policy.yaml`. It never trusts a candidate worktree approval
file merely because that file says APPROVED or names an Owner. Expiry is mandatory;
naive/future timestamps, inverted intervals, duplicate scopes/JSON keys and
malformed records fail closed. Historical risk acceptance requires PROJECT_OWNER.

Every authority also carries the exact `approved_ledger_sha256` and an explicit
`approval_kind` (`PRECISE_EXCEPTION` or `OWNER_RISK_ACCEPTANCE`). The digest must
match the verified ledger bytes, and the kind must match each consumed finding's
disposition. An earlier ordinary Owner approval cannot become risk acceptance
after ledger reclassification. Any ledger byte change, including classification,
another row or formatting, invalidates both groups' previous approvals. An
explicit new bounded decision is required; old fields are not inferred or
upgraded automatically. This binds approval semantics without requesting any
credential evidence or creating a hash cycle with the separate authority anchors.

The policy/consumer/schema/ledger and authority anchors must themselves be covered
by the final trusted source-integrity boundary. Git object hashes alone do not
authenticate an approver or prevent a Developer from rewriting an unprotected
policy. Local synthetic approvals prove behavior, not real authority or GitLab
permissions. At the original design stage, `trusted_authorities: []` granted no approval.
The current local candidate uses the explicitly approved immutable anchors described above; historical pending inputs do not describe its current authority state.

## Decision and reporting

The report separates `detected`, `known`, `approved_and_consumed`, `unapproved`,
`expired`, `unmatched_findings`, `unmatched_approvals` and `unused_approvals`.
Every approved identity consumes at most one actual finding. Duplicate findings,
new/unmatched findings, absent authority, malformed metadata and extra findings
fail. Unused approvals are reported and also fail, preserving the earlier stricter
acceptance requirement. A finding count, including a count below 45, never grants
permission.

Scanner errors cannot be converted to approval: only exit 0 with no findings or
exit 1 with nonempty findings is a complete scan. Exit 2, inconsistent reports,
missing reports, timeout and parser failures remain hard failures.

## Review handoff and remaining prerequisites

Local test results, negative-control matrix, preservation proof and exact diff
are in the new ignored validation directory. The review object is the base SHA
plus recorded file/patch hashes; no immutable implementation commit is created
in this run. The existing dirty primary execution context is preserved, not
silently repaired. Formal task-entry scope/review pin remains unsatisfied.

The implementation can be reviewed independently. Final trusted-CI readiness
still requires real exact authority decisions (with expiry), immutable approved
source/policy bindings and the final candidate revision. This run does not claim
V2-004 VERIFIED, P0 accepted or any product phase started. After independent review,
resume the final candidate path without reopening credential evidence collection.

The ledger retains the exactly approved `canonical_ref`/hash as a logical review-artifact identity. That unchanged preapproval observation is delivered under `dist/validation/v2004-history-delta-20261015/evidence/`, as explicitly recorded in OWNER_DECISION_RECEIPT.json; it is not tracked source or a runtime input. Runtime approval matching verifies every exact source blob/line and immutable authority directly. Scan reports remain execution artifacts.
