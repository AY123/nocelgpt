# ANovel V2 Architecture Risk Register

**Document ID**: CONV-RISK-0001  
**Version**: 1.0  
**Status**: NORMATIVE  
**Created**: 2026-09-19  
**Authority**: CONVERGENCE-BASELINE  
**Depends On**:
- PROJECT_CONSTITUTION.md (Principles, Invariants, Prohibitions)
- NORMATIVE_INDEX.md (Truth Hierarchy T0-T7)
- AUTHORITY_MATRIX.md (Authority boundaries)
- V1_FORENSIC_LESSONS.md (Failure patterns)
- ARCHITECTURE_AUDIT_REPORT.md (Known defects)
- All policy files (canon-commit-policy.yaml, context-policy.yaml, workflow-policy.yaml, etc.)

**Purpose**: Document architecture risks that could undermine ANovel V2 system reliability, with threat assessment, mitigation strategies, detection methods, and related invariants.

---

## 0. Risk Assessment Framework

### 0.1 Threat Levels

| Level | Meaning | Impact |
|-------|---------|--------|
| **P0** | System-breaking | Canon corruption, second truth source, authority violation |
| **P1** | Production-blocking | Cannot certify 30 chapters, genre contamination, commit bypass |
| **P2** | Quality-degrading | Reliability issues, detection gaps, recovery failures |

### 0.2 Risk States

- **INHERENT**: Architecture design creates this risk
- **DETECTED**: V1 failure or audit finding confirms it happened
- **MITIGATED**: Controls in place, requires verification
- **RESIDUAL**: Cannot fully eliminate, requires monitoring

### 0.3 Detection Levels

- **E0-DETERMINISTIC**: Can be caught by schema/hash/constraint checks
- **E1-STRUCTURAL**: Requires domain validation logic
- **E2-AI-ASSISTED**: Needs model evaluation (calibration required)
- **E3-HUMAN**: Requires human review
- **E4-MARKET**: Only real reader/market signal can detect

---

## CANON & STATE RISKS

### RISK-C01: Second Canon (Duplicate Truth Source)

**Description**: A second storage or cache becomes a competing source of narrative truth, diverging from the canonical Event Log.

**Threat Level**: **P0**

**V1 Evidence**: Multiple verdict centers existed (QA pass, commercial rollback, pipeline revise, production invalidated) creating conflicting truth claims.

**Affected Phases**: P2 (Canon Transaction), P3-P14 (all dependent phases)

**Architecture Vulnerability**:
- Derived projections (StoryState, CharacterRoster, Timeline) cached without invalidation
- Worker-local "optimized" state copies
- Export/dashboard databases not marked read-only
- Repair systems maintaining parallel candidate state that leaks into production

**Mitigation Strategy**:
1. **INV-004 enforcement**: Canon writes ONLY through CanonCommit boundary
2. **PROHIBIT-002**: Explicit prohibition of second Canon Store
3. **Architecture Fitness Tests**:
   - Writer cannot import Canon write API
   - All projections derive from CanonEventLog with version binding
   - Database constraints: only CanonCommitService has INSERT on canon_commits
4. **Derived State Lifecycle**: ACTIVE/STALE/INVALIDATED with automatic cascade on parent change
5. **Audit Log**: All Canon writes logged with issuer identity

**Detection Method**:
- **E0**: Static analysis detects unauthorized Canon write imports
- **E0**: Database permission enforcement (only commit service can write)
- **E1**: Runtime assertion: every Canon read checks source authority
- **E3**: Manual audit of data flow diagrams

**Related Invariants**: INV-004, INV-003, INV-009  
**Related Prohibitions**: PROHIBIT-002, PROHIBIT-003  
**Related Principles**: P-001, P-004, P-006

**Verification Gates**: M1 (architecture fitness), M2 (Canon transaction), all subsequent milestones

---

### RISK-C02: Authority Drift (Authority Boundaries Blur Over Time)

**Description**: Components gradually accumulate authority they shouldn't have, blurring the separation between proposal, validation, and commitment.

**Threat Level**: **P1**

**V1 Evidence**: Reviewers, judges, and diagnostic systems accumulated decision-making weight without clear authority boundaries.

**Affected Phases**: All phases (ongoing risk)

**Architecture Vulnerability**:
- "Convenience" methods that bypass validation ("quick commit for testing")
- Diagnostic outputs stored in same tables as authoritative state
- Judge scores used directly in production decisions without policy layer
- Reference intelligence gradually allowed to "suggest" Canon changes
- Market signals auto-updating Genre rules without human gate

**Mitigation Strategy**:
1. **Authority Matrix (CONV-0004)**: Explicit documentation of who can trigger/block each operation
2. **T0-T7 Truth Hierarchy**: Lower tiers cannot override higher tiers
3. **Separation of Concerns**:
   - Evidence collection (T5-T7) separated from decision execution (T0-T4)
   - QualityReport is diagnostic (T7), CommitPermit is gate artifact, CanonCommit is execution
4. **Human Authority Gates** (Section 20 of CONSTITUTION):
   - R3 Retcon requires human approval
   - Major Genre changes require human approval
   - Production policy deployment requires human approval
   - Publishing requires human approval
5. **Code Structure**:
   - Separate packages: `evidence/`, `policy/`, `execution/`
   - No cross-imports from evidence to execution
6. **Periodic Authority Audit**: Quarterly review of actual authority vs. documented authority

**Detection Method**:
- **E0**: Architecture fitness tests verify import boundaries
- **E1**: Authorization checks at every state transition
- **E3**: Code review checklist includes authority boundary verification
- **E3**: Quarterly manual audit comparing implementation to Authority Matrix

**Related Invariants**: INV-008 (Model not proposal+approver+authority)  
**Related Prohibitions**: PROHIBIT-003, PROHIBIT-009  
**Related Principles**: P-006, P-010, P-011

**Verification Gates**: P0 (architecture baseline), M2, M4, periodic audits

---

### RISK-C03: Schema False Positive (Validation Passes Bad Data)

**Description**: JSON Schema or domain validation accepts malformed or semantically invalid data due to overly permissive constraints.

**Threat Level**: **P1**

**V1 Evidence**: Character schema accepted Location as entity_type, "injured" as lifecycle status, missing required extractions returned as "skip validation."

**Audit Findings**:
- **AR-03**: Character extended fields rejected by base schema `additionalProperties: false`
- **AR-04**: NarrativeDelta operations lack typed value constraints
- **AR-05**: CommitPermit can have empty validation_refs with ALLOW decision

**Affected Phases**: P1 (Genre/Domain), P2 (Canon), P4 (Planning), P6 (Quality)

**Architecture Vulnerability**:
- `additionalProperties: true` used excessively
- Operations with arbitrary `value: {}` fields
- Enums not enforced (free-form strings accepted)
- Optional fields that should be conditionally required
- Empty arrays/objects interpreted as "passed" instead of "not checked"
- `allOf` composition with closed base schemas blocking legitimate extensions

**Mitigation Strategy**:
1. **Schema Design Principles**:
   - Use `unevaluatedProperties: false` at appropriate layers
   - Define explicit operation types with typed payloads
   - Required vs. optional based on lifecycle state
   - Conditional schemas for context-dependent requirements
2. **Positive and Negative Test Coverage**:
   - Every schema must have valid positive examples
   - Every schema must have invalid examples that should fail
   - Boundary cases (empty, null, wrong type, wrong enum, missing required)
3. **Domain Validation Layer**:
   - Schema validates structure
   - Domain validators check semantic correctness (e.g., Character can't have Location lifecycle)
   - Cross-entity constraints checked at service layer
4. **AR-03 Fix**: Correct Character/NarrativeEntity composition (V2-006)
5. **AR-04 Fix**: Define typed operation algebra (V2-008-010)
6. **AR-05 Fix**: Require check execution records, not just empty evidence (V2-026)

**Detection Method**:
- **E0**: JSON Schema validation in CI
- **E0**: Test matrix includes boundary and negative cases (114 test IDs in audit)
- **E1**: Domain validation tests with known-bad data
- **E3**: Manual schema review against domain specifications

**Related Invariants**: INV-001, INV-005, INV-010  
**Related Principles**: P-019 (Deterministic Facts outrank Semantic Preference)

**Verification Gates**: V2-006 (Character schema fix), V2-026 (Permit validation), M3 (Genre certification)

---

### RISK-C04: Schema False Negative (Validation Rejects Good Data)

**Description**: Overly restrictive validation blocks legitimate use cases, forcing workarounds that bypass proper validation.

**Threat Level**: **P2**

**Audit Findings**:
- **AR-03**: Character identity fields rejected due to closed base schema
- **AR-10**: SceneContract missing genre_pack_hash field, cannot directly bind Genre

**Affected Phases**: P1-P4 (domain modeling), ongoing

**Architecture Vulnerability**:
- Base schemas too restrictive for extensions
- Enum lists incomplete (missing valid Genre fusion modes, valid operations)
- Hash/version binding fields not consistently available
- Legal domain combinations rejected (urban rebirth, cultivation + business)

**Mitigation Strategy**:
1. **Extensibility Design**:
   - Open base + closed leaves strategy
   - Explicit extension registration
   - Genre-specific schema variants
2. **Positive Example Coverage**:
   - All documented capabilities must have valid schema examples
   - Genre boundary cases (legal fusion) explicitly tested
3. **AR-03 Fix**: Allow Character-specific fields in derived schemas
4. **AR-10 Fix**: Ensure all contracts can bind required parent artifacts
5. **Extension Registry**: Unregistered extensions blocked early, not after generation

**Detection Method**:
- **E0**: Positive test coverage (all legal cases pass)
- **E1**: Regression tests from false negative reports
- **E3**: User feedback when legitimate operations fail

**Related Invariants**: INV-001 (GenrePack binding), INV-014 (Genre pollution tests)  
**Related Principles**: P-002 (Genre is Foundational Domain)

**Verification Gates**: V2-006, V2-015-016 (dual Genre anchor), M3

---

### RISK-C05: Duplicate Commit (Same Change Committed Twice)

**Description**: Retry or recovery logic accidentally commits the same narrative change twice, causing state duplication or corruption.

**Threat Level**: **P1**

**V1 Evidence**: V1 regression requirement "REG-V1-RETRY-001: Same commit stage retry must not duplicate Canon event."

**Affected Phases**: P3 (Canon), P8 (Workflow Recovery)

**Architecture Vulnerability**:
- Missing or weak idempotency keys
- Idempotency key not covering semantic payload (only metadata)
- Retry logic that doesn't check for existing commit before re-executing
- Response lost after successful commit (client thinks it failed, retries)
- Multiple workers attempting same commit concurrently

**Mitigation Strategy**:
1. **Idempotency Keys**:
   - Every commit requires unique idempotency_key (INV-006)
   - Key covers: project, branch, sequence, content_hash, attempt_id
   - Database UNIQUE constraint on idempotency_key
2. **Optimistic Locking**:
   - CAS (Compare-And-Swap) on parent_commit_hash
   - Commit only succeeds if parent_hash matches current HEAD
3. **Retry Protocol**:
   - Before retry: check if commit with same idempotency_key exists
   - If exists: return existing commit receipt (idempotent success)
   - If parent changed: reject as conflict, require rebase
4. **Receipt Protocol**:
   - Every successful commit returns verifiable receipt
   - Receipt includes: commit_id, sequence, content_hash, timestamp
   - Client can query by idempotency_key to recover lost receipt
5. **Audit Trail**:
   - All commit attempts logged (success/failure/duplicate)
   - Monitoring alerts on duplicate attempts

**Detection Method**:
- **E0**: Database constraint violation on duplicate idempotency_key
- **E1**: Unit test: same commit attempted twice, second returns existing
- **E1**: Integration test: simulate response lost after commit success
- **E1**: Concurrent commit test: two workers, one succeeds, one rejected

**Related Invariants**: INV-003 (valid parent), INV-006 (no duplicate side effects), INV-010 (RunFingerprint)  
**Related Policy**: canon-commit-policy.yaml: `idempotency_key` required, `parent_mismatch: BLOCK`

**Verification Gates**: V2-009-010 (Canon transaction), V2-027-028 (recovery), M2

---

### RISK-C06: Partial Commit (Commit Succeeds Partially, State Inconsistent)

**Description**: Database transaction commits Event Log but fails to update Snapshot or HEAD, leaving Canon in inconsistent state.

**Threat Level**: **P0**

**Affected Phases**: P3 (Canon), ongoing

**Architecture Vulnerability**:
- Long transaction scope including LLM calls (AR-09 in audit)
- Event append succeeds, projection fails, no rollback
- HEAD update fails after event committed
- Distributed transaction across multiple storage systems (DB + object storage)
- Network partition during commit

**Mitigation Strategy**:
1. **Short DB Transactions** (AR-09 remediation):
   - Generate and validate candidate BEFORE opening transaction
   - Transaction scope: INSERT event + UPDATE head + basic metadata
   - Keep DB transaction under 100ms
2. **Atomic Commit Protocol**:
   ```sql
   BEGIN TRANSACTION;
     -- Verify parent still current (CAS)
     SELECT version FROM canon_head WHERE project_id=? AND branch_id=? FOR UPDATE;
     -- Insert event
     INSERT INTO canon_events (...) VALUES (...);
     -- Update HEAD atomically
     UPDATE canon_head SET commit_id=?, sequence=?, version=version+1 WHERE project_id=? AND branch_id=? AND version=?;
     -- Check exactly 1 row updated (CAS success)
     IF affected_rows != 1 THEN ROLLBACK;
   COMMIT;
   ```
3. **Projection as Async/Compensating**:
   - Projection rebuilding happens AFTER commit succeeds
   - Projection failures don't rollback commit
   - STALE projections can be rebuilt from Event Log (INV-009)
4. **Immutable Content First**:
   - If using object storage: upload immutable content BEFORE commit
   - Commit references content by hash/ID
   - Orphan content can be garbage collected
5. **Health Checks**:
   - Monitor: HEAD points to valid commit in Event Log
   - Monitor: Event Log sequence has no gaps
   - Repair tool: rebuild projections from Event Log

**Detection Method**:
- **E0**: Database constraint checks (foreign keys, sequence uniqueness)
- **E1**: Integration test with simulated failures (rollback, network cut, projection failure)
- **E1**: Health check: verify HEAD.commit_id exists in events
- **E1**: Health check: verify sequence continuity

**Related Invariants**: INV-003 (valid parent), INV-009 (rebuildable from Event Log)  
**Related Issues**: AR-09 (transaction boundary confusion)

**Verification Gates**: V2-009-010, M2, ongoing monitoring

---

### RISK-C07: Cross-Project Leakage (One Project's Data Affects Another)

**Description**: Insufficient isolation allows one project's Canon, Context, or Cache to leak into another project.

**Threat Level**: **P0**

**Audit Findings**: **AR-13**: Project/branch isolation not consistently enforced across all schemas and queries.

**Affected Phases**: All phases (foundational issue)

**Architecture Vulnerability**:
- Missing project_id in query WHERE clauses
- Shared cache without project key scoping
- Context compiler reading from wrong project
- Global registries (Genre, Reference) not distinguished from project-specific (Canon, Plan)
- Branch names like "main" collide across projects if not scoped

**Mitigation Strategy**:
1. **Scope Taxonomy**:
   - GLOBAL: shared across all projects (GenrePack registry, ModelPolicy)
   - PROJECT: scoped to project (Canon, Story, Characters)
   - BRANCH: scoped to project branch (working drafts)
2. **Database Design**:
   - Every project-scoped table has project_id in primary key or UNIQUE constraint
   - Every query includes project_id (and branch_id if branch-scoped) in WHERE clause
   - Database-level row-level security (RLS) if supported
3. **Context Policy** (CTX-POL-003): Project and branch isolation enforced at Context Compiler
4. **Cache Keys**: Include scope in cache key: `{scope}:{project_id}:{branch_id}:{artifact_type}:{artifact_id}`
5. **Authorization Layer**: Service methods verify caller has permission for target project
6. **AR-13 Remediation**: Audit all schemas, add project_id/branch_id appropriately (V2-009-015)

**Detection Method**:
- **E0**: Schema validation requires project_id where needed
- **E1**: Integration test: two projects with same entity names, verify no cross-read
- **E1**: Integration test: cache test with concurrent projects
- **E3**: Code review: verify all queries include project_id

**Related Invariants**: INV-001 (Production binds GenrePack), INV-010 (RunFingerprint includes project)  
**Related Policy**: context-policy.yaml CTX-POL-003  
**Related Issues**: AR-13

**Verification Gates**: V2-009 (Canon keys), V2-013-015 (Context), M2

---

## GENRE & DOMAIN RISKS

### RISK-G01: Genre Contamination (Urban Gets Xianxia Elements)

**Description**: Production under one Genre incorrectly includes elements forbidden by that Genre's Hard Rules (e.g., urban realism contains cultivation).

**Threat Level**: **P1**

**V1 Evidence**: V1 explicitly documented Genre weak constraints causing type pollution. Keywords like "cultivation," "magic" appeared in urban projects.

**V1 Regression Case**: REG-V1-GENRE-001: Urban realistic business project with unauthorized cultivation/magic must be blocked by Genre Hard Rule.

**Affected Phases**: P1 (Genre), P2-P14 (all production)

**Architecture Vulnerability**:
- Genre validation only at end (detection not prevention)
- Keyword-based detection has false positives (metaphor, story-within-story) and false negatives (implicit supernatural)
- Extractor fails to detect Genre-violating elements
- Fusion modes not explicitly declared
- GenrePack not bound at production start (INV-001 violation)

**Mitigation Strategy**:
1. **Early Binding** (INV-001): Every production MUST bind versioned GenrePack before generation
2. **Hard Rules as Gates** (INV-002): Genre Hard Violations MUST block Canon Commit (Q2 gate)
3. **Multi-Layer Detection**:
   - **Schema Layer**: Forbidden capability types, stat types, entity types
   - **Extraction Layer**: NarrativeDelta checked against Genre extension registry
   - **Keyword Layer**: Supplementary detection (not sole mechanism)
   - **Semantic Layer**: AI judge calibrated for Genre boundaries (E2/E3)
4. **Fusion Declaration**: Legal cross-Genre elements explicitly registered in GenrePack
5. **Genre Certification** (INV-014): Production-ready GenrePack MUST have cross-type pollution negative tests
6. **AR-15 Remediation**: Define executable extension boundaries for dual anchor genres (V2-015-016)

**Detection Method**:
- **E0**: Schema rejects forbidden types (urban Pack doesn't have cultivation_level schema)
- **E1**: Extraction validates operations against Genre extension registry
- **E1**: Q2 gate blocks commit if Genre Hard Rule violated
- **E2**: Genre drift detector (calibrated AI judge)
- **E3**: Human review of Genre boundary cases

**Related Invariants**: INV-001, INV-002, INV-014  
**Related Prohibitions**: PROHIBIT-007 (no hardcoded hot topics)  
**Related Principles**: P-002 (Genre is Foundational Domain), P-009 (Market not Genre Truth)  
**Related Lessons**: LESSON-V1-001, LESSON-V1-002, LESSON-V1-003

**Verification Gates**: V2-007-008 (Genre foundation), V2-015-016 (dual anchor), M3 (Genre certification)

---

### RISK-G02: Context Omission (Mandatory Facts Missing from Context)

**Description**: Critical information (character identity, world rules, previous commitments) omitted from generation context, causing continuity errors.

**Threat Level**: **P1**

**V1 Evidence**: Novel-dushi chapter 1 referenced wrong protagonist name ("林远" instead of "陈默"), suggesting Story Bible information didn't reach Writer context.

**V1 Regression Case**: REG-V1-CHAR-001: Canon protagonist "陈默", text protagonist "林远" must fail identity contract.

**Affected Phases**: P5 (Context Intelligence), P6-P14 (all generation)

**Architecture Vulnerability**:
- Context token budget forces trimming, mandatory items included in trim pool
- Mandatory vs. optional not explicitly tagged
- Context compiler prioritizes recent over required
- Stale context (old Canon version) used for generation
- Character aliases not resolved, causing "unknown entity" in context

**Mitigation Strategy**:
1. **Mandatory Item Protection** (CTX-POL-001): Mandatory items NEVER trimmed
2. **Context Policy** (context-policy.yaml):
   - CTX-POL-001: Mandatory items never trimmed (HARD)
   - CTX-POL-004: Stale Canon or Contract blocks (HARD)
   - CTX-POL-006: Same-authority conflicts must resolve or block (HARD)
3. **Authority Priority** (SourcePrecedence): Higher-authority sources override lower when assembling context
4. **Mandatory Item Types**:
   - Protagonist identity and core attributes
   - Current timeline/location state
   - Genre Hard Rules
   - Active commitments (promises, relationships, knowledge boundaries)
   - Required transitions from Contract
5. **Compilation Verification**:
   - After compilation: verify all mandatory items present
   - If budget insufficient for mandatory: BLOCK generation, don't trim
6. **Staleness Detection**: Context artifacts versioned, stale versions rejected

**Detection Method**:
- **E0**: Context artifact schema requires mandatory_items list
- **E1**: Compiler asserts all mandatory items included post-compilation
- **E1**: Staleness check: Canon parent version matches Context Canon version
- **E3**: Spot check: generated text reviewed against mandatory items

**Related Invariants**: INV-001 (GenrePack bound), INV-003 (valid parent)  
**Related Policy**: context-policy.yaml (CTX-POL-001, CTX-POL-004, CTX-POL-006)  
**Related Principles**: P-016 (Context must be Compiled)

**Verification Gates**: V2-013-015 (Context Intelligence), M4 (single chapter E2E), M6 (10 chapters)

---

### RISK-G03: Extractor Omission (Important Story Changes Not Extracted)

**Description**: NarrativeDelta extraction misses significant narrative changes (new abilities, character deaths, promise violations), allowing them to bypass validation.

**Threat Level**: **P1**

**V1 Evidence**: V1 ROADMAP noted extractor couldn't see entity names/aliases, causing known entities to be extracted as "new."

**Audit Finding**: **AR-12**: "Must check for extraction omissions, not just validate extracted fields."

**Affected Phases**: P2 (Domain), P6 (Quality), P8-P14 (ongoing)

**Architecture Vulnerability**:
- Extractor returns empty delta, interpreted as "no changes" instead of "failed to extract"
- Unknown ≠ no change, but not enforced
- No coverage check (did extractor even attempt to check required dimensions?)
- Metaphor, implication, negation confuse extractor
- Aliases and pronouns cause entity resolution failures

**Mitigation Strategy**:
1. **Unknown ≠ No Change** (NARRATIVE_DOMAIN_SPEC principle): Empty extraction is suspicious, not clean
2. **Extraction Coverage**:
   - Contract defines "must-check" dimensions (identity, timeline, abilities, resources)
   - Extractor MUST produce verdict for each dimension: SUPPORTED / REFUTED / UNKNOWN / ERROR
   - UNKNOWN on critical dimensions requires human review or blocks commit
3. **Dual-Path Validation** (AR-12 remediation):
   - Path 1: Extract delta, validate delta against rules
   - Path 2: Check text directly against forbidden patterns (backstop)
   - Path 2 finds violations Path 1 missed → extraction improvement needed
4. **Entity Resolution**:
   - Alias registry maintained in Canon
   - Extractor uses alias resolution before "new entity" judgment
5. **Negative Test Cases**:
   - Text contains violation but extractor misses it → verify Path 2 catches it
   - Text has implicit changes (metaphor, dream, negation) → coverage tests

**Detection Method**:
- **E1**: Empty delta on chapter with significant text triggers warning
- **E1**: Contract-required dimensions with UNKNOWN verdict flagged
- **E2**: Secondary AI judge checks text for missed extractions
- **E3**: Human review samples text and delta for completeness

**Related Invariants**: INV-005 (evaluated text hash = committed text hash)  
**Related Issues**: AR-12  
**Related Lessons**: LESSON-V1-009 (extractor entity resolution failure)

**Verification Gates**: V2-020-021 (Quality/Extraction), V2-024-025 (Validation), M4, M6

---

## WORKFLOW RISKS

### RISK-W01: Retry Double Billing (Retry Charges Twice for Same Work)

**Description**: Transient failure causes retry, but both original and retry requests charge the account, doubling costs without additional value.

**Threat Level**: **P2**

**Affected Phases**: P5 (Model Integration), P8 (Workflow)

**Architecture Vulnerability**:
- No semantic request fingerprint (AR-14 audit finding)
- Cache misses treat retry as new request
- Provider response lost after success, client retries
- Idempotency not supported by provider
- Fallback treated as new request even with identical semantic payload

**Mitigation Strategy**:
1. **Semantic Request Fingerprint** (WF-POL-006):
   - Semantic: prompt, model, sampling params, max_output, tool_policy
   - Operational (excluded): timeout, retry_count, request_id, telemetry
2. **Response Caching**:
   - Cache by semantic fingerprint
   - Cache includes usage/cost metadata
   - Retry with same fingerprint returns cached response without new charge
3. **Provider Idempotency**:
   - If provider supports idempotency keys, use them
   - Pass provider-specific request ID for queryable recovery
4. **Cost Tracking**:
   - ModelRun records: attempt_number, cached (yes/no), usage, cost
   - Retry flagged as retry (not new request) in accounting
5. **Unknown Result Protocol** (AR-14 remediation):
   - SUCCEEDED / FAILED / CACHED / UNKNOWN / TIMEOUT
   - UNKNOWN: response fate unclear, may have charged, do not auto-retry without budget buffer

**Detection Method**:
- **E1**: Unit test: same semantic request twice, second marked CACHED
- **E1**: Integration test: simulate lost response, verify recovery doesn't double-charge
- **E3**: Cost reconciliation: provider invoice vs. internal cost records

**Related Invariants**: INV-006 (no duplicate side effects), INV-010 (RunFingerprint)  
**Related Policy**: workflow-policy.yaml (WF-POL-003, WF-POL-006)  
**Related Issues**: AR-14

**Verification Gates**: V2-018-019 (Model Integration), V2-027 (Recovery), M5

---

### RISK-W02: Unknown Provider Result (Don't Know If Request Succeeded)

**Description**: Network timeout or crash leaves system unable to determine if provider executed request, causing uncertainty about state and charges.

**Threat Level**: **P2**

**Audit Finding**: **AR-14**: Provider result unknown, ModelRun schema cannot represent this state.

**Affected Phases**: P5 (Model Integration), P8 (Workflow Recovery)

**Architecture Vulnerability**:
- Binary success/failure model (no "unknown" state)
- Timeout treated as transient failure, auto-retried
- No receipt or queryable request ID from provider
- Client crash after provider success but before recording response
- Cannot distinguish "definitely failed" from "maybe succeeded"

**Mitigation Strategy**:
1. **Extended Status Model** (AR-14 remediation):
   - PENDING: request sent, awaiting response
   - SUCCEEDED: response received and recorded
   - FAILED: provider returned error
   - TIMEOUT: deadline exceeded, result unknown
   - UNKNOWN: cannot determine (crash, network partition)
   - CACHED: served from cache, no provider call
2. **Provider Receipt Protocol**:
   - If provider supports queryable receipts (e.g., request_id), record it
   - On recovery: query provider to determine actual result
   - If provider doesn't support queries: state remains UNKNOWN
3. **Retry Policy for Unknown**:
   - UNKNOWN requires manual review or budget buffer before retry
   - Automatic retry could duplicate charges
   - Mark as "potentially duplicate" in cost tracking
4. **Idempotency Keys**: If provider supports, use them to make retries safe
5. **Budget Reservation**: Reserve budget before call, release on success, mark "uncertain" on unknown

**Detection Method**:
- **E1**: Integration test: simulate timeout, verify TIMEOUT or UNKNOWN status
- **E1**: Integration test: crash after provider success, verify recovery detects uncertainty
- **E1**: Manual test with real provider: timeout handling
- **E3**: Incident review: UNKNOWN cases reviewed for cost reconciliation

**Related Invariants**: INV-006 (no duplicate side effects), INV-010 (RunFingerprint)  
**Related Issues**: AR-14

**Verification Gates**: V2-018-019, V2-027-028, M5

---

### RISK-W03: Unversioned Policy (Policy Changes Silently Affect Production)

**Description**: Production policies (quality thresholds, retry limits, cost caps) change without versioning, breaking reproducibility and causing silent behavior shifts.

**Threat Level**: **P1**

**Affected Phases**: All phases (cross-cutting issue)

**Architecture Vulnerability**:
- Policy files edited directly in production
- No version binding in artifacts
- Active runs use policy version at query time (not start time)
- Policy promoted from experiments without freeze
- AI auto-learning modifies policy without human gate (Section 20 violation)

**Mitigation Strategy**:
1. **PROHIBIT-012**: No unversioned Prompt/Schema/Policy in Production
2. **Policy Versioning**:
   - Every policy file has version field
   - Semantic versioning: MAJOR.MINOR.PATCH
   - MAJOR change requires ADR
3. **Artifact Binding**:
   - Every artifact references policy_version used
   - WorkflowRun, CanonCommit, QualityReport all bind policy version
4. **Policy Deployment**:
   - Production policy changes require human authority (CONSTITUTION Section 20)
   - Experiment promotion requires passing promotion gate
   - Active runs complete under original policy or explicit migration
5. **Policy Registry**:
   - Historical policy versions retained
   - Reproducible runs reference exact policy version

**Detection Method**:
- **E0**: Schema validation: artifacts must have policy_version field
- **E1**: CI check: policy files have version field
- **E1**: Deployment gate: production policy change requires approval
- **E3**: Audit: compare production behavior before/after policy change

**Related Invariants**: INV-012 (AI Eval labels Evidence Level), INV-013 (Artifact has lifecycle)  
**Related Prohibitions**: PROHIBIT-012  
**Related Principles**: P-012 (Persistent Artifacts require Provenance)

**Verification Gates**: P0 (policy governance), all subsequent phases

---

## AI & JUDGMENT RISKS

### RISK-A01: Agent Hidden Memory (AI Uses Memory We Can't Audit)

**Description**: LLM agent maintains state in its conversation history or implicit "memory" that influences decisions but isn't captured in Canon or provenance.

**Threat Level**: **P1**

**Affected Phases**: P5-P14 (all AI-involved phases)

**Architecture Vulnerability**:
- Multi-turn agent conversations without full history logging
- Agent "remembers" facts not in Canon
- Model's conversation context used as state store
- Hidden tool calls or intermediate reasoning steps
- Agent memory systems (e.g., Claude Projects) not dumped to audit trail

**Mitigation Strategy**:
1. **PROHIBIT-011**: Hidden Mutable Agent Memory cannot be truth source
2. **Stateless Workers**:
   - Writer, Planner, Extractor, Judge are stateless
   - All input comes from explicit ContextArtifact
   - No persistent agent session between chapters
3. **Conversation Logging**:
   - Full request/response logged (prompt, sampling params, response, tool calls)
   - Intermediate reasoning (if available) captured
4. **Context-First Architecture**:
   - All necessary information compiled into Context
   - Agent doesn't "remember" prior chapters except via Canon in Context
5. **Audit Trail**:
   - Every ModelRun has complete provenance
   - Can reproduce generation given same Context + Model + Params

**Detection Method**:
- **E1**: Test: same context to fresh agent session produces consistent results
- **E1**: Provenance completeness: can reproduce result from logged artifacts
- **E3**: Spot check: agent behavior doesn't depend on prior unrelated conversations

**Related Invariants**: INV-010 (RunFingerprint), INV-012 (Evidence Level labeled)  
**Related Prohibitions**: PROHIBIT-011  
**Related Principles**: P-001 (Canon over Model Memory), P-016 (Context must be Compiled)

**Verification Gates**: V2-018-019 (Model Integration), M4, ongoing

---

### RISK-A02: Prompt-Only Hard Constraints (Critical Rules Only in Prompt, Not Validated)

**Description**: Essential constraints (don't change protagonist name, respect timeline) exist only in prompt text, not enforced by code, allowing violations to pass.

**Threat Level**: **P1**

**V1 Evidence**: V1 prompt-based Genre prevention insufficient, required architectural enforcement.

**Affected Phases**: All production phases

**Architecture Vulnerability**:
- Prompt says "protagonist is 陈默" but no post-generation identity check
- Prompt says "urban realistic, no magic" but no Genre gate
- Prompt says "current year 2025" but no timeline validation
- Over-reliance on model following instructions

**Mitigation Strategy**:
1. **PROHIBIT-004**: Critical Hard Constraints cannot exist only in Prompt
2. **Defense in Depth**:
   - **Layer 1 (Prompt)**: Clearly communicate constraints to model
   - **Layer 2 (Extraction)**: Extract facts from generation
   - **Layer 3 (Validation)**: Validate extracted facts against constraints
   - **Layer 4 (Gate)**: Block commit if validation fails
3. **Constraint Sources**:
   - GenrePack Hard Rules → Q2 gate
   - Contract required/forbidden transitions → Q3 gate
   - Canon immutable facts → Q1 gate
   - Schema integrity → Q0 gate
4. **Prompt as Guidance**: Prompts guide generation, validation enforces correctness

**Detection Method**:
- **E0**: Architecture audit: constraints documented, enforcement verified
- **E1**: Negative test: generation violates prompt constraint, gate catches it
- **E3**: Review: critical constraints identified, enforcement path documented

**Related Invariants**: INV-002 (Genre Hard Violation blocks commit)  
**Related Prohibitions**: PROHIBIT-004  
**Related Principles**: P-005 (Production is Fail-Closed), P-019 (Deterministic Facts outrank Semantic Preference)

**Verification Gates**: P6 (Quality gates), M4 (single chapter with validation), M6

---

### RISK-A03: Judge Over-Authority (AI Judge Can Override Hard Facts)

**Description**: AI quality judge's high scores allow commit even when deterministic violations (schema errors, hash mismatches, timeline conflicts) exist.

**Threat Level**: **P0**

**Affected Phases**: P6 (Quality), P7 (Integration)

**Architecture Vulnerability**:
- Judge score used as primary gate
- High subjective quality overrides low deterministic checks
- Q4-Q6 soft gates treated as blockers
- Single AI judge has commit authority (violates PROHIBIT-009)
- Evidence levels not distinguished (E0-E4 混淆)

**Mitigation Strategy**:
1. **PROHIBIT-009**: Single AI Judge cannot have Commit Authority
2. **P-010**: AI Judge is not Ground Truth
3. **Evidence Hierarchy** (E0 > E1 > E2 > E3 > E4):
   - E0 (deterministic): schema, hash, integrity → HARD BLOCK
   - E1 (structural): domain rules, Canon consistency → HARD BLOCK
   - E2 (AI eval): quality assessment → ADVISORY
   - E3 (human/sim): calibration → ADVISORY or GATE (if calibrated)
   - E4 (market): real reader signal → CALIBRATION DATA
4. **Gate Layering** (Quality Spec):
   - Q0 (integrity), Q1 (Canon), Q2 (Genre), Q3 (transitions) → HARD GATES
   - Q4-Q6 (quality, coherence, commercial) → SOFT GATES (feedback only)
5. **CommitPermit Requirements**:
   - ALL hard gates (Q0-Q3) must PASS
   - Soft gate failures provide feedback but don't block
6. **AR-05 Remediation**: Enforce check execution coverage (V2-026)

**Detection Method**:
- **E0**: Permit issuance checks all Q0-Q3 gates passed
- **E1**: Test: Q0 FAIL + Q4-Q6 PASS → commit blocked
- **E1**: Test: AI judge prefers AI-written text → bias detected, not blocking

**Related Invariants**: INV-008 (Model not proposal+approver+authority), INV-012 (Evidence Level labeled)  
**Related Prohibitions**: PROHIBIT-009  
**Related Principles**: P-010, P-019  
**Related Issues**: AR-05

**Verification Gates**: V2-020-026 (Quality/Validation), M4, M5

---

### RISK-A04: Benchmark Overfitting (Tuning to Test Set, Not Real Capability)

**Description**: System optimized to pass specific test cases or golden set examples but fails on novel scenarios or real production.

**Threat Level**: **P2**

**Affected Phases**: P11 (Calibration), P13 (Learning)

**Architecture Vulnerability**:
- Golden set used for both tuning and validation
- No holdout set
- Prompt tuned on same examples used for evaluation
- Test cases become known to optimization process
- Certification runs cherry-picked

**Mitigation Strategy**:
1. **Holdout Discipline**:
   - Training set: for prompt/policy development
   - Validation set: for iteration during development
   - Holdout set: for final evaluation, never seen during tuning
2. **Blind Evaluation**:
   - Evaluators don't know which output is baseline vs. candidate
   - Human reviewers isolated from optimization process
3. **Promotion Gate** (Learning Spec):
   - Candidate must beat baseline on holdout
   - Statistical significance required
   - Real reader signal (E4) preferred over AI-only metrics
4. **Diverse Test Corpus**:
   - Multiple genres, edge cases, boundary conditions
   - Negative examples (should fail)
   - Adversarial examples
5. **Certification Integrity**:
   - 10/30/100 chapter runs use fresh seeds
   - No cherry-picking successful runs
   - Failed attempts documented, not hidden

**Detection Method**:
- **E3**: Audit: verify holdout set never used in training
- **E3**: Statistical test: performance on training vs. holdout comparable
- **E4**: Real reader feedback doesn't correlate with AI metrics → overfitting suspected

**Related Principles**: P-020 (Reader/Market Signal calibrates AI Metrics)  
**Related Lessons**: LESSON-V1-010 (AI evaluation requires evidence levels)

**Verification Gates**: P11 (Calibration), P13 (Learning), not applicable to early phases

---

## REFERENCE & LEARNING RISKS

### RISK-R01: Reference Imitation (Too Similar to Source Material)

**Description**: Generated content too closely resembles reference works, creating copyright or originality concerns.

**Threat Level**: **P1**

**Affected Phases**: P10 (Genesis), ongoing

**Architecture Vulnerability**:
- Reference text included in Writer context (violates CTX-POL-002)
- Mechanism extraction insufficient, plot copied
- No originality verification
- Paraphrase of reference rather than original creation
- Character names, plot beats, dialogue structure directly copied

**Mitigation Strategy**:
1. **PROHIBIT-008**: Continuous reference text forbidden in Writer context by default
2. **CTX-POL-002**: writer_raw_reference_forbidden_by_default (HARD)
3. **Reference Intelligence Layer** (Genesis Spec):
   - Extract abstract mechanisms, not content
   - ReferencePack contains: patterns, functions, structures (not text)
   - Reference text stays in genesis phase, not production phase
4. **Originality Guard**:
   - Similarity check against reference corpus
   - Threshold for acceptable similarity
   - High similarity flags for human review
5. **Human Review**: Reference-guided genesis requires human approval before large-scale production

**Detection Method**:
- **E0**: Context compiler rejects raw reference text (CTX-POL-002 enforced)
- **E2**: Similarity detector compares output to reference corpus
- **E3**: Human review of reference-guided chapters
- **E4**: Copyright review before publication

**Related Invariants**: INV-007 (Reference MUST NOT write Canon directly)  
**Related Prohibitions**: PROHIBIT-008  
**Related Principles**: P-011 (Reference Evidence not Project Canon)  
**Related Policy**: context-policy.yaml CTX-POL-002  
**Related Lessons**: LESSON-V1-012

**Verification Gates**: V2-042-044 (Genesis), P10, deferred but planned

---

### RISK-R02: Reader Signal Confounding (Fake Engagement Signals)

**Description**: Reader engagement metrics (clicks, likes, subscriptions) manipulated or misinterpreted, leading to incorrect optimization.

**Threat Level**: **P2**

**Affected Phases**: P13 (Learning), long-term production

**Architecture Vulnerability**:
- Bot traffic counted as real readers
- A/B test confounded by author reputation, cover art, recommendation placement
- Small sample size, high variance
- Novelty effect (initial engagement not sustained)
- Platform algorithm changes affect metrics
- Self-selection bias (early readers not representative)

**Mitigation Strategy**:
1. **INV-011**: Market Snapshot MUST have platform/channel/time/source/confidence metadata
2. **Signal Qualification**:
   - Source authenticated (real platform data, not simulated)
   - Sample size sufficient for statistical power
   - Confounding factors documented
3. **Long-Term Metrics Preferred**:
   - Retention > clicks
   - Chapter 10-30 retention > chapter 1-3
   - Paid subscriptions > free reads
4. **Corpus Evaluation Protocol** (Learning Spec):
   - Baseline comparison (not absolute metrics)
   - Statistical significance tests
   - Multiple metrics (not single optimand)
5. **Human Calibration**: Reader signal calibrates AI metrics, doesn't replace human judgment

**Detection Method**:
- **E3**: Statistical review of A/B test results
- **E3**: Audit signal provenance and confounders
- **E4**: Real platform data vs. expected distribution

**Related Invariants**: INV-011 (Market Snapshot provenance)  
**Related Principles**: P-020 (Reader/Market Signal calibrates AI Metrics), P-009 (Market Trend not Genre Truth)

**Verification Gates**: P13 (Learning), deferred, not applicable to early phases

---

### RISK-R03: Narrative Engine Repetition (Same Patterns Every Time)

**Description**: System produces formulaic, repetitive story structures because underlying narrative engine lacks variety or fails to evolve.

**Threat Level**: **P2**

**Affected Phases**: P4 (Planning), P6 (Production), long-term

**Architecture Vulnerability**:
- Planning system uses same templates
- Scene-level generation repeats patterns (every chapter: problem → escalation → cliffhanger)
- Character arc templates rigidly applied
- Lack of controlled randomness
- No tracking of "pattern usage frequency"
- Model collapse: training/tuning on own outputs

**Mitigation Strategy**:
1. **Planning Diversity**:
   - Multiple arc templates
   - Controlled variation in scene structures
   - Avoid strict formula enforcement
2. **Pattern Tracking**:
   - Monitor narrative function usage frequency
   - Detect repetitive patterns (e.g., every chapter ends with cliffhanger)
   - Balance mechanism diversity
3. **Long-Term Success Criteria** (CONSTITUTION 3.2, 3.3):
   - 100 chapters: no large-scale repetition
   - 300 chapters: narrative engine still expanding
   - Middle/late chapters not just chapter 1 repeated
4. **Quality Metrics**: Pattern diversity, novelty, surprise tracked (soft metrics)
5. **Human Review**: Sample chapters checked for formulaic patterns

**Detection Method**:
- **E2**: Pattern diversity metrics (scene types, arc structures, conflict types)
- **E3**: Human reviewers flag repetitive patterns
- **E4**: Reader feedback on predictability

**Related Principles**: P-014 (Long-form Correctness before Feature Breadth)

**Verification Gates**: M5 (100 chapters), M6 (300 chapters)

---

## LONG-TERM PRODUCTION RISKS

### RISK-L01: Long-Run Promise Debt (Promises Accumulate, Never Pay Off)

**Description**: System generates numerous promises, mysteries, and commitments but fails to track or resolve them, leading to reader dissatisfaction.

**Threat Level**: **P2**

**Affected Phases**: P4 (Planning), long-term tracking

**Architecture Vulnerability**:
- Promise/mystery creation not tracked
- No "open commitment" ledger
- Planning system doesn't account for prior commitments
- Forgotten plot threads (character introduced, never returns)
- Setup without payoff
- Resolution tracking weak

**Mitigation Strategy**:
1. **Promise Ledger** (Domain Spec):
   - All promises, mysteries, commitments tracked in Canon
   - Status: OPEN / PARTIALLY_RESOLVED / RESOLVED / ABANDONED
   - Abandoned requires justification (not accidental)
2. **Planning Integration**:
   - Arc planning considers open promises
   - Major promises have resolution arcs
   - Timeline for promise resolution
3. **Quality Check**: Long-running promises flagged for review
4. **Long-Term Success Criteria** (CONSTITUTION 3.2, 3.3):
   - 100 chapters: key commitments tracked
   - 300 chapters: long arc promises resolved

**Detection Method**:
- **E1**: Query open promises, age distribution
- **E2**: AI judge detects unresolved threads
- **E3**: Human review of promise ledger

**Related Principles**: P-014 (Long-form Correctness)

**Verification Gates**: M5 (100 chapters), M6 (300 chapters)

---

### RISK-L02: Progression Inflation (Power Creep Makes Stakes Meaningless)

**Description**: Character power/resources/influence inflate continuously without grounded constraints, making stakes feel arbitrary.

**Threat Level**: **P2**

**Affected Phases**: P1 (Genre/Domain), P4 (Planning), long-term

**Architecture Vulnerability**:
- No upper bounds on progression
- Each arc requires "bigger threat" without justification
- Economic/power inflation unchecked
- Costs become meaningless (character infinitely rich)
- Capability inflation (can solve anything)

**Mitigation Strategy**:
1. **Genre-Specific Progression Models**:
   - Define progression dimensions (cultivation realm, wealth, influence, knowledge)
   - Establish progression rate constraints
   - Costs and time requirements for progression
2. **World Constraints**:
   - Upper bounds on capabilities within genre rules
   - Scarcity maintained (resources finite)
   - Power relative to world, not absolute
3. **Planning Balance**:
   - Escalation through complexity, not just power
   - Meaningful costs and tradeoffs
   - Setbacks and losses

**Detection Method**:
- **E1**: Track progression rate, flag abnormal inflation
- **E2**: AI judge evaluates stakes meaningfulness
- **E3**: Human review of progression curve

**Related Principles**: P-002 (Genre is Foundational Domain)

**Verification Gates**: M5, M6 (long-term stability)

---

### RISK-L03: Human Intervention Hidden (Human Fixes Not Recorded in Provenance)

**Description**: Human manually edits Canon, fixes continuity errors, or adjusts state without recording the intervention, breaking provenance and reproducibility.

**Threat Level**: **P1**

**Affected Phases**: All phases, ongoing

**Architecture Vulnerability**:
- Manual database edits bypass audit log
- Human fixes not recorded as explicit operations
- "Hot fix" to production state
- Correction doesn't update provenance
- Can't distinguish "AI generated correctly" from "human fixed quietly"

**Mitigation Strategy**:
1. **Human Authority Protocol** (CONSTITUTION Section 20):
   - Human interventions require explicit human_approval authority
   - R3 Retcon mechanism for major corrections
2. **Audit Trail**:
   - All Canon changes logged with actor identity
   - Human edits explicitly marked
   - Reason/justification recorded
3. **Database Permissions**:
   - Production database: only CanonCommitService and HumanReviewService can write
   - Direct SQL edits forbidden (or at minimum logged)
4. **Provenance Integrity**:
   - Human fixes create new Canon events, don't silently mutate
   - Lineage shows AI generation + human correction

**Detection Method**:
- **E0**: Database audit log captures all writes with actor
- **E1**: Provenance chain complete, no unexplained state changes
- **E3**: Incident review: any manual fix documented

**Related Invariants**: INV-004 (Canon only via Commit), INV-009 (rebuildable from Event Log)  
**Related Prohibitions**: PROHIBIT-010 (no Silent Retcon)  
**Related Principles**: P-012 (Persistent Artifacts require Provenance)

**Verification Gates**: P0 (audit baseline), M2 (Canon), ongoing monitoring

---

## RISK SUMMARY MATRIX

| Risk ID | Risk Name | Threat Level | Affected Phases | V1 Evidence | Key Mitigation | Detection |
|---------|-----------|--------------|-----------------|-------------|----------------|-----------|
| **RISK-C01** | Second Canon | P0 | P2-P14 | Multiple verdict centers | INV-004, PROHIBIT-002, fitness tests | E0, E1 |
| **RISK-C02** | Authority Drift | P1 | All | Accretion of authority | Authority Matrix, T0-T7 hierarchy | E0, E1, E3 |
| **RISK-C03** | Schema False Positive | P1 | P1-P6 | AR-03, AR-04, AR-05 | Negative tests, domain validators | E0, E1 |
| **RISK-C04** | Schema False Negative | P2 | P1-P4 | AR-03, AR-10 | Positive test coverage, extension registry | E0, E1 |
| **RISK-C05** | Duplicate Commit | P1 | P3, P8 | REG-V1-RETRY-001 | Idempotency keys, CAS, receipt protocol | E0, E1 |
| **RISK-C06** | Partial Commit | P0 | P3+ | AR-09 | Short transactions, projection as async | E0, E1 |
| **RISK-C07** | Cross-Project Leakage | P0 | All | AR-13 | Scope taxonomy, CTX-POL-003 | E0, E1 |
| **RISK-G01** | Genre Contamination | P1 | P1+ | LESSON-V1-001, REG-V1-GENRE-001 | INV-001, INV-002, Q2 gate | E0, E1, E2 |
| **RISK-G02** | Context Omission | P1 | P5+ | Novel-dushi protagonist error | CTX-POL-001, mandatory items | E0, E1 |
| **RISK-G03** | Extractor Omission | P1 | P2, P6+ | AR-12, extractor entity failure | Coverage checks, dual-path validation | E1, E2 |
| **RISK-W01** | Retry Double Billing | P2 | P5, P8 | AR-14 | Semantic fingerprint, caching | E1 |
| **RISK-W02** | Unknown Provider Result | P2 | P5, P8 | AR-14 | Extended status, receipt protocol | E1 |
| **RISK-W03** | Unversioned Policy | P1 | All | Policy drift | PROHIBIT-012, versioning, human gate | E0, E1 |
| **RISK-A01** | Agent Hidden Memory | P1 | P5+ | - | PROHIBIT-011, stateless workers | E1, E3 |
| **RISK-A02** | Prompt-Only Constraints | P1 | All | V1 Genre prompt weakness | PROHIBIT-004, defense in depth | E0, E1 |
| **RISK-A03** | Judge Over-Authority | P0 | P6-P7 | AR-05 | PROHIBIT-009, E0-E4 hierarchy | E0, E1 |
| **RISK-A04** | Benchmark Overfitting | P2 | P11, P13 | - | Holdout sets, blind eval | E3, E4 |
| **RISK-R01** | Reference Imitation | P1 | P10+ | - | PROHIBIT-008, CTX-POL-002, originality guard | E0, E2, E3 |
| **RISK-R02** | Reader Signal Confounding | P2 | P13 | - | INV-011, statistical rigor | E3, E4 |
| **RISK-R03** | Narrative Engine Repetition | P2 | P4, P6+ | - | Pattern tracking, diversity metrics | E2, E3 |
| **RISK-L01** | Long-Run Promise Debt | P2 | P4+ | - | Promise ledger, arc integration | E1, E2, E3 |
| **RISK-L02** | Progression Inflation | P2 | P1, P4+ | - | Genre progression models, constraints | E1, E2, E3 |
| **RISK-L03** | Human Intervention Hidden | P1 | All | - | Audit log, explicit human authority | E0, E1, E3 |

---

## PHASE-SPECIFIC RISK PROFILES

### P0 (Repository Bootstrap): Critical Risks

- **RISK-C02**: Authority Drift (establish baseline controls)
- **RISK-W03**: Unversioned Policy (establish versioning from day 1)
- **RISK-L03**: Human Intervention Hidden (audit logging baseline)

**P0 Exit Criteria**: Architecture fitness tests prevent INV-004 violations, secret scanning, policy versioning enforced.

### P1-P2 (Domain & Canon Foundation): Critical Risks

- **RISK-C01**: Second Canon
- **RISK-C03**: Schema False Positive
- **RISK-C05**: Duplicate Commit
- **RISK-C06**: Partial Commit
- **RISK-C07**: Cross-Project Leakage
- **RISK-G01**: Genre Contamination

**M2 Exit Criteria**: Canon transaction with CAS, idempotency, single write boundary verified. Genre Hard Rules block commits.

### P3-P5 (Planning, Context, Integration): Critical Risks

- **RISK-G02**: Context Omission
- **RISK-G03**: Extractor Omission
- **RISK-A01**: Agent Hidden Memory
- **RISK-A02**: Prompt-Only Constraints

**M4 Exit Criteria**: Single chapter E2E with mandatory context items, Q0-Q3 gates enforcing constraints.

### P6-P9 (Quality, Repair, Workflow, Certification): Critical Risks

- **RISK-A03**: Judge Over-Authority
- **RISK-W01**: Retry Double Billing
- **RISK-W02**: Unknown Provider Result

**M7 Exit Criteria**: 30 chapters dual-genre with recovery testing, evidence hierarchy enforced.

### P10+ (Genesis, Learning, Long-Term): Critical Risks

- **RISK-R01**: Reference Imitation
- **RISK-R02**: Reader Signal Confounding
- **RISK-R03**: Narrative Engine Repetition
- **RISK-L01**: Long-Run Promise Debt
- **RISK-L02**: Progression Inflation

**M5-M6 Exit Criteria**: 100-300 chapter stability, pattern diversity, promise tracking, provenance integrity.

---

## VERIFICATION & MONITORING

### Architecture Fitness Tests (Continuous)

Must verify:
- Canon write only through CanonCommit boundary (RISK-C01)
- Writer cannot import Canon write API (RISK-C01)
- Reference cannot import Canon commit (RISK-R01)
- Single Canon store only (RISK-C01)
- Genre can block commits (RISK-G01)
- Draft never auto-becomes Canon (RISK-C02)
- AI judge no commit authority (RISK-A03)
- Contract binds genre and parent (RISK-G01)
- Permit requires all hard gates (RISK-A03)
- Human authority enforced for R3 (RISK-L03)

### Runtime Assertions (Production)

Must verify:
- Commit has valid permit (RISK-C05)
- Permit binds exact draft hash (RISK-C03)
- Parent hash matches Canon HEAD (RISK-C05, RISK-C06)
- Idempotency key unique (RISK-C05)
- Genre pack version bound (RISK-G01)
- Contract version bound (RISK-C02)
- Policy version bound (RISK-W03)
- Provenance complete (RISK-L03)

### Periodic Audits (Quarterly)

Must review:
- Authority boundaries: implementation vs. documentation (RISK-C02)
- Provenance integrity: all Canon changes traceable (RISK-L03)
- Policy adherence: hard rules actually enforced (RISK-A02)
- Schema coverage: positive and negative tests (RISK-C03, RISK-C04)

### Long-Term Monitoring (M5-M6)

Must track:
- Pattern diversity (RISK-R03)
- Promise ledger (RISK-L01)
- Progression curves (RISK-L02)
- Human intervention frequency (RISK-L03)
- Cost vs. expected (RISK-W01, RISK-W02)

---

## RESIDUAL RISKS

Some risks cannot be fully eliminated:

1. **Creative Quality**: E2/E3 quality metrics are proxies, not truth. Real reader calibration (E4) eventual, not immediate.
2. **Model Limitations**: LLMs have inherent limitations (reasoning, long-term coherence). Mitigation reduces but doesn't eliminate.
3. **Novel Scenarios**: Test coverage is finite. Novel edge cases may expose gaps.
4. **Human Judgment**: Even with protocols, human review has variance and bias.
5. **Market Dynamics**: Reader preferences evolve, platform algorithms change. Continuous adaptation required.

These residual risks are **accepted** with monitoring and iterative improvement.

---

## CONCLUSION

This Architecture Risk Register documents 23 identified risks across Canon/State, Genre/Domain, Workflow, AI/Judgment, Reference/Learning, and Long-Term Production categories. Each risk includes:

- Clear description and threat level
- V1 evidence or audit findings where applicable
- Affected implementation phases
- Concrete mitigation strategies tied to invariants, prohibitions, and principles
- Specific detection methods with evidence levels
- Verification gates

**Key Insights**:

1. **P0-level risks** (Second Canon, Partial Commit, Cross-Project Leakage, Judge Over-Authority) require foundational architecture controls, not just careful coding.
2. **V1 lessons** directly inform 8 risks with explicit regression cases.
3. **Audit findings** (AR-03 through AR-14) map to 7 specific risks with remediation tasks.
4. **Multi-layered defense** is essential: E0 (schema) + E1 (domain) + E2 (AI) + E3 (human) + E4 (market).
5. **Verification is phase-specific**: P0-P2 focus on foundational integrity, P6-P9 on production robustness, P10+ on long-term sustainability.

All risks are **traceable** to:
- Constitution principles (P-001 to P-020)
- Core invariants (INV-001 to INV-015)
- Architecture prohibitions (PROHIBIT-001 to PROHIBIT-014)
- V1 lessons (LESSON-V1-001 to LESSON-V1-012)
- Policy files (canon-commit-policy.yaml, context-policy.yaml, workflow-policy.yaml)
- Authority Matrix (CONV-0004)
- Normative Index (CONV-0002)

This register should be **living documentation**: updated when new risks discovered, when mitigations implemented, when verification results obtained.

---

**Document Status**: NORMATIVE  
**Maintenance**: Update when new risks identified, mitigations deployed, or phase milestones achieved  
**Next Review**: After M2 (Canon Transaction certification)

---

**END OF ARCHITECTURE RISK REGISTER**
