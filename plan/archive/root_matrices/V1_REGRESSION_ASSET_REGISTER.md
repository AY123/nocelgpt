# V1 Regression Asset Register

**Document Type**: V2 Regression Requirements  
**Source**: V1 Documented Failures (PROJECT_DEEP_ANALYSIS.md, reproduce_findings.py, audit reports)  
**Purpose**: Convert V1 failures into V2 "must not regress" requirements  
**Date**: 2026-09-19  
**Status**: DRAFT

---

## Executive Summary

This register extracts 23 documented V1 failures and converts them into actionable V2 regression requirements. Each failure includes:
- Failure ID and description
- V1 evidence location (file:line)
- Root cause analysis
- V2 requirement type
- Acceptance criteria

**Priority Distribution**:
- P0 (Critical - Data Integrity & Security): 2 failures
- P1 (High - Production Reliability): 19 failures
- P2 (Medium - Maintainability): 2 failures

---

## P0 Failures - Critical Security & Data Integrity

### RF-001: Secret Leakage in Git-Tracked Documentation

**V1 Failure**: Git-tracked documentation contains API keys and tokens in plain text.

**V1 Evidence**:
- `/ainovel/AI-Novel-Runtime/PHASE1-INTEGRATION-SESSION-SUMMARY.md:188`
- `/ainovel/docs/archive/2026-08-history/BALANCE_ISSUE_REPORT.md:17`
- `/ainovel/docs/archive/2026-08-history/RETRY_CC_VIBE.md:9`
- 6 token literals across 5 documents, 3 distinct fingerprints

**Root Cause**:
- No pre-commit secret scanning
- Developers copy-pasted credentials into documentation during troubleshooting
- `.env` exclusion doesn't protect values copied into markdown

**V2 Requirement Type**: **Security Certification Failure Case**

**V2 Acceptance Criteria**:
1. Pre-commit hook blocks commits containing token patterns (API key, Bearer token, etc.)
2. CI pipeline fails on secret detection in any tracked file
3. Documentation templates never include credential placeholders
4. Secret scanning covers full Git history, not just current HEAD
5. Regression test: Attempt to commit file with mock API key → MUST be rejected

**V2 Test Asset**: `test_secret_scanning_prevents_commit`
- Input: Mock commit with `API_KEY=sk-abc123xyz` in markdown
- Expected: Commit rejected with clear error message
- Scope: Pre-commit, CI, periodic audit

---

### RF-002: Mint Atomic Commit Failure (Partial State on I/O Failure)

**V1 Failure**: Mint's "validate then write" lacks atomic commit. I/O failure during registry-version write leaves facts updated but registry metadata stale.

**V1 Evidence**:
- `/ainovel/AI-Novel-Runtime/runtime/mint/executor.py:363` (write facts loop)
- `/ainovel/AI-Novel-Runtime/runtime/mint/executor.py:509` (write registry-version)
- `reproduce_findings.py:72-87` - Reproduction shows `fact_version=2`, `registry_version=1`, `receipt_count=0`

**Root Cause**:
- Sequential file writes without transaction boundary
- No rollback mechanism
- No write-ahead log or two-phase commit
- ID ledger lock doesn't cover entire fact transaction

**V2 Requirement Type**: **Architecture Fitness Rule + Integration Test**

**V2 Acceptance Criteria**:
1. Fact commit, registry head, changeset, and receipt written atomically (DB transaction or equivalent)
2. Any I/O failure leaves system in complete OLD state or complete NEW state
3. Same idempotency key with same payload returns original receipt
4. Same key with different payload is conflict, not silent overwrite
5. Concurrent commit conflict detection with CAS (compare-and-swap)
6. Parent head validation prevents lost updates

**V2 Test Asset**: `test_mint_atomic_commit_on_failure`
- Setup: Valid changeset ready to commit
- Fault injection: Simulate disk failure after facts written but before receipt
- Assertions:
  - Either all artifacts present OR none present
  - Registry head matches fact versions
  - Re-execution with same key returns same receipt or clear failure
  - No orphan facts without receipts
  - No receipts without facts

**V2 Architecture Rule**: `ARCH-ATOM-001`
- Rule: All Canon state mutations must occur within a single transaction boundary
- Verification: Static analysis of CanonCommitService, database transaction scope inspection
- Failure Mode: Find any code path that writes Canon fact followed by non-transactional operation

---

## P1 Failures - Production Reliability

### RF-003: BLOCKED State Doesn't Prevent Chapter Progression

**V1 Failure**: When ProductionDecisionEngine returns BLOCKED, the system still increments chapter count and continues to next chapter.

**V1 Evidence**:
- `/ainovel/AI-Novel-Runtime/runtime/serialize/loop.py:1788` (state projection advances before decision check)
- `/ainovel/AI-Novel-Runtime/runtime/serialize/loop.py:2603` (`can_advance=False` only sets `chapter_ok=False`, doesn't break loop)
- `reproduce_findings.py:90-94` - Two BLOCKED chapters → `produced=2, skipped=0`, both `ok=False`, event counts `[1, 2]`

**Root Cause**:
- State projection happens before final decision check
- `can_advance=False` is advisory, not enforced
- "Subjective scores shouldn't gate builds" misapplied to deterministic failures

**V2 Requirement Type**: **Contract Test + Regression Fixture**

**V2 Acceptance Criteria**:
1. BLOCKED decision prevents dependent chapter generation
2. Chapter N+1 cannot start if chapter N is BLOCKED
3. Workflow status reflects blocked state, not "completed"
4. Resume from blocked state requires manual intervention or fix
5. Blocked chapter doesn't advance Canon head or event cursor

**V2 Test Asset**: `test_blocked_decision_prevents_progression`
- Setup: 3-chapter plan, inject BLOCKED on chapter 2
- Assertions:
  - Chapter 1 completes normally
  - Chapter 2 receives BLOCKED verdict
  - Chapter 3 is NOT generated
  - Workflow status = BLOCKED, not COMPLETED
  - Event cursor stops at chapter 2's last event
  - Canon head doesn't advance past chapter 1

**V2 Contract**: `ChapterDependencyContract`
- Pre-condition: Parent chapter has valid CommitPermit with ALLOW decision
- Violation: Attempting to generate chapter N+1 when chapter N is BLOCKED/DENIED
- Enforcement: WorkflowEngine pre-flight check

---

### RF-004: Resume Cursor Inconsistent with Completion Tracking

**V1 Failure**: Resume cursor and completed chapter list don't reflect actual state. Failed chapters marked as "cursor+1", successful history gets overwritten.

**V1 Evidence**:
- `/ainovel/AI-Novel-Runtime/runtime/serialize/workflow_scheduler.py:295`
- `reproduce_findings.py:39-55` - Three reproduction scenarios:
  1. Chapters [1✓, 2✗, 3✓] → `completed=[1,3], cursor=4` (should revisit 2)
  2. 1 chapter BLOCKED → `status=completed, completed=[]` (wrong status)
  3. Run 1 completes ch1, Run 2 completes ch2 → `completed=[2]` (lost history)

**Root Cause**:
- Cursor set to max chapter + 1 regardless of gaps
- Status update happens after entire `_run_one` batch, not per-chapter
- Completed list replaced instead of merged
- No explicit "failed chapters need revalidation" tracking

**V2 Requirement Type**: **Integration Test + Architecture Fitness Rule**

**V2 Acceptance Criteria**:
1. Cursor points to first incomplete/failed chapter, not arbitrary next
2. Completed chapters accumulate across runs (merge, not replace)
3. Failed chapter list persists until explicitly resolved
4. Workflow status reflects blocking failures (not "completed" when chapters failed)
5. Cost accumulates across runs, not replaced
6. Each chapter has durable checkpoint with attempt history

**V2 Test Asset**: `test_resume_cursor_handles_gaps_and_failures`
- Test Case 1: Gap scenario
  - Complete ch1, fail ch2, complete ch3
  - Assert: cursor=2, completed=[1,3], failed=[2]
  - Resume → attempts ch2 first, validates ch3 dependencies
- Test Case 2: Blocked workflow
  - 1 chapter blocked, 0 skipped
  - Assert: status=BLOCKED, completed=[], cursor=1
- Test Case 3: History accumulation
  - Run 1: complete ch1
  - Run 2: complete ch2
  - Assert: completed=[1,2] (not just [2])
- Test Case 4: Cost accumulation
  - Run 1: cost=$5
  - Run 2: cost=$3
  - Assert: total_cost=$8

---

### RF-005: Completed Task Re-enters Generation on Resume with Changed Input

**V1 Failure**: Resuming a completed workflow re-executes generation even when inputs changed, bypassing input consistency check.

**V1 Evidence**:
- `/ainovel/AI-Novel-Runtime/runtime/serialize/workflow_scheduler.py:247` (status=completed resume path)
- `/ainovel/AI-Novel-Runtime/runtime/serialize/workflow_scheduler.py:175` (input check happens after resume branch)
- `reproduce_findings.py:57-62` - Changed prompt_version from 1.0 to 2.0, resume called serial generation with new version

**Root Cause**:
- Resume logic branches on status before input validation
- `_input_hash` only covers partial parameters (missing facts head, model, schema, code version)
- Replay directory stored but not verified for binding
- Budget check not unified across entry points

**V2 Requirement Type**: **Contract Test + Regression Fixture**

**V2 Acceptance Criteria**:
1. Completed task with changed input is rejected or creates new run
2. Input hash covers: prompt version, model, facts head, schema version, genre pack, contracts
3. Resume verifies replay binding if replay_dir specified
4. Unified entry point for budget/input validation across start/resume/step
5. Idempotency: Same input → same result; different input → new run or explicit error

**V2 Test Asset**: `test_completed_task_rejects_changed_input_on_resume`
- Setup: Complete 1-chapter workflow with prompt v1.0
- Change: Update prompt to v2.0
- Action: Call resume()
- Expected: Reject with "input changed, completed result no longer valid" OR create new workflow run
- Also test changes to: model, schema version, facts head, genre pack

**V2 Contract**: `WorkflowInputIntegrityContract`
- Input hash includes all semantic inputs
- Resume operation validates hash against stored baseline
- Violation triggers new run creation or user confirmation requirement

---

### RF-006: Unknown State Cursor Exposes All Events (No Bounds Check)

**V1 Failure**: Requesting state with unknown event cursor returns all events instead of erroring.

**V1 Evidence**:
- `/ainovel/AI-Novel-Runtime/runtime/memory/state.py:117`
- `reproduce_findings.py:64-67` - Request `EVT-99999` (doesn't exist), returns all 3 events with invalid cursor still in response

**Root Cause**:
- Only truncates event list if cursor exists in order
- Missing existence validation
- No distinction between "initial state", "all state", "head state"

**V2 Requirement Type**: **Contract Test**

**V2 Acceptance Criteria**:
1. Unknown cursor raises explicit error
2. "Initial state" (no events) is explicit request, not fallback
3. "Current head" is explicit request
4. State projection never silently ignores invalid cursor
5. Cursor validation before projection computation

**V2 Test Asset**: `test_state_projection_rejects_unknown_cursor`
- Test invalid cursor (EVT-99999) → raises CursorNotFoundError
- Test null cursor → returns initial state (explicitly)
- Test "HEAD" sentinel → returns current head
- Test valid historical cursor → returns correct prefix

---

### RF-007: Novel-Dushi Facts Validation Failed (60 Schema Errors)

**V1 Failure**: Production instance contains 30 events with Standard-illegal fields; all 30 chapter-finals invalidated.

**V1 Evidence**:
- `project-analysis-2026-09-18/novel-dushi-validation.log`
- 30 Events contain disallowed `date`, `location` (natural language string in `LOC-*` reference field)
- `/ainovel/novel-dushi/generate_events_from_bible.py:80` - Bypass script writes facts without validation

**Root Cause**:
- Bypass script directly writes registry without going through Mint
- No validation at write time
- Schema evolution without data migration

**V2 Requirement Type**: **Regression Fixture + Architecture Fitness Rule**

**V2 Acceptance Criteria**:
1. All fact writes go through unified validation gateway (no bypass scripts)
2. Schema validation runs before commit
3. Invalid facts cannot enter Canon
4. Data migration tool for schema evolution
5. All imported data validated against current schema

**V2 Test Asset**: `test_invalid_facts_rejected_at_commit`
- Negative test suite from novel-dushi errors:
  - Event with `date` field (not in schema) → REJECT
  - Event with natural language in `locations` (expects `LOC-*` reference) → REJECT
  - Bypass attempt (direct file write) → detected by integrity check

**V2 Architecture Rule**: `ARCH-FACT-001`
- Rule: All fact mutations MUST go through CanonCommitService
- Verification: No code path writes to facts directory except via commit boundary
- Enforcement: File system permissions, integrity scan

---

### RF-008: Genre Confusion - Xianxia Rebirth Misclassified as Urban

**V1 Failure**: Input describing xianxia cultivation with rebirth mechanism classified as "都市" (urban) due to "rebirth" keyword bonus.

**V1 Evidence**:
- `/ainovel/AI-Novel-Runtime/runtime/outline/analyzer.py:86`
- `reproduce_findings.py:96-99` - Input: "他重生于仙门，修炼灵气，突破境界，掌握飞剑，踏上渡劫之路。" → Output: `["都市", "都市重生", "玄幻"]`

**Root Cause**:
- "Rebirth" is narrative mechanism, not reality model
- Keyword scoring conflates mechanism with genre
- Genre rules scattered (keywords, templates, outline, finalizer, v14/v15 branches)
- No unified GenrePack architecture

**V2 Requirement Type**: **Regression Fixture + Contract Test**

**V2 Acceptance Criteria**:
1. Xianxia content with rebirth correctly classified as Eastern Fantasy
2. Urban content with rebirth correctly classified as Urban
3. Genre determined by: reality model (cultivation qi/mundane physics), setting era, progression system
4. Narrative mechanisms (rebirth, transmigration, system) don't override reality model
5. Unified GenrePack compilation includes: world rules, progression axis, narrative mechanisms, fusion rules

**V2 Test Asset**: `test_genre_classification_xianxia_rebirth`
- Positive cases:
  - Xianxia + rebirth → Eastern Fantasy Cultivation (not Urban)
  - Urban + rebirth → Urban Fantasy (with rebirth mechanism)
  - Xianxia without rebirth → Eastern Fantasy Cultivation
- Negative cases (must reject or warn):
  - Urban businessman suddenly flying sword (reality model violation)
  - Cultivation world with stock market (unless explicitly fusion genre)

**V2 GenrePack Contract**: Each pack declares:
- Reality model (mundane physics vs cultivation qi vs magic)
- Allowed progressions (realm/level/skill/wealth)
- Allowed mechanisms (rebirth, transmigration, system)
- Cross-contamination rules

---

### RF-009: Missing or Exceptional Contract Check Passes as Success

**V1 Failure**: Contract validation exceptions or disabled checks treated as "pass"; unclear distinction between "not run", "error", "pass", "fail".

**V1 Evidence**:
- `/ainovel/AI-Novel-Runtime/runtime/serialize/loop.py:1710` (contract check requires flag AND specific prompt version)
- `/ainovel/AI-Novel-Runtime/runtime/serialize/loop.py:1775` (exception → error-only object)
- `/ainovel/AI-Novel-Runtime/runtime/serialize/loop.py:2495` (contract_status defaults to pass, only changed if requires_revision)
- `strict_mode=False` hardcoded

**Root Cause**:
- Fail-open default for missing checks
- No distinction between PASS / FAIL / ERROR / NOT_RUN
- Optional switches and branches without unified semantics
- Rule capability bound to specific prompt string instead of workflow policy

**V2 Requirement Type**: **Contract Test + Architecture Fitness Rule**

**V2 Acceptance Criteria**:
1. Contract check results use 4-state model: PASS / FAIL / ERROR / NOT_RUN
2. Production mode: FAIL, ERROR, NOT_RUN all block commit (fail-closed)
3. Required checks enforced by workflow policy, not prompt version string
4. Exception during check → ERROR state, not pass
5. Missing check implementation → NOT_RUN, blocks production commit

**V2 Test Asset**: `test_contract_validation_fail_closed`
- Test Case 1: Contract check raises exception → status=ERROR, commit BLOCKED
- Test Case 2: Required check not implemented → status=NOT_RUN, commit BLOCKED
- Test Case 3: Check disabled in dev mode → status=NOT_RUN, allowed in dev, blocked in prod
- Test Case 4: Check returns FAIL → commit BLOCKED
- Test Case 5: All checks PASS → commit ALLOWED

**V2 Architecture Rule**: `ARCH-FAILCLOSED-001`
- Rule: Default to deny in production; explicit pass required
- Verification: Code review of decision gates, QualityDecision → Permit logic
- Test: Inject each failure mode (exception, not run, missing) → all block prod

---

### RF-010: Continuity Failure Treated as Warning Only

**V1 Failure**: Continuity validation failures don't block progression; treated as warnings.

**V1 Evidence**: Documented in PROJECT_DEEP_ANALYSIS.md findings; observed in loop.py review

**Root Cause**:
- Q0-Q3 quality gates not uniformly enforced
- Warnings vs errors not clearly separated by severity
- "Subjective quality shouldn't block" misapplied to factual continuity

**V2 Requirement Type**: **Contract Test**

**V2 Acceptance Criteria**:
1. Q0 (factual continuity) failures MUST block commit
2. Q1 (character identity) failures MUST block commit
3. Q2 (genre constraints) failures MUST block commit
4. Q3 (plot coherence) violations configurable by policy
5. Q4-Q7 (aesthetic) are advisory, don't block by default

**V2 Test Asset**: `test_continuity_violation_blocks_commit`
- Setup: Chapter with character name change, impossible timeline
- Q0 check detects violations
- Assert: QualityDecision = DENY, no CommitPermit issued

---

### RF-011: Multiple Verdict Centers Create Inconsistent Decisions

**V1 Failure**: Multiple decision sources (ChapterReviewer, finalizer, decision engine, production card) produce conflicting verdicts.

**V1 Evidence**:
- `/ainovel/AI-Novel-Runtime/runtime/chapter/reviewer.py:25` (heuristic scores, fixed 0.7 for consistency)
- `/ainovel/AI-Novel-Runtime/runtime/serialize/loop.py:1969` (another decision path)
- `/ainovel/AI-Novel-Runtime/runtime/chapter/finalizer.py`
- Observed samples: `final_review.pass=ready` + `production_decision.revise` + `production_state.invalidated`

**Root Cause**:
- No single source of truth for production decision
- ChapterReviewer generates publish_readiness without real validation
- Internal chapter_pipeline runs before unified decision
- Heuristic scores labeled as real quality metrics

**V2 Requirement Type**: **Architecture Fitness Rule + Integration Test**

**V2 Acceptance Criteria**:
1. Single QualityDecisionEngine produces authoritative verdict
2. All quality inputs feed into decision engine, don't make independent commit decisions
3. Heuristic scores explicitly labeled, don't fill real reader-signal fields
4. Production state has single source: the CommitPermit decision
5. Review/analysis tools separate from commit authority

**V2 Test Asset**: `test_single_decision_authority`
- Multiple quality inputs (extraction, validation, review)
- Assert: Single QualityDecision output
- Assert: CommitPermit references that decision
- Assert: No other code path can mark chapter "production ready"

**V2 Architecture Rule**: `ARCH-AUTHORITY-001`
- Rule: Only QualityDecisionEngine + PermitIssuer can authorize commits
- Verification: Static analysis of Canon commit call sites
- No scattered `production_state` assignments

---

### RF-012: Placeholder Hash and Empty Provenance in Finals

**V1 Failure**: Final chapter artifacts missing provenance (model, checks, parent Canon); hash present but can't verify generation chain.

**V1 Evidence**:
- PROJECT_DEEP_ANALYSIS.md: "都市 30 finals 全部缺 provenance; 玄幻 7/30 缺失"
- Hash recomputation matches, but no chain to model/contract/parent

**Root Cause**:
- Provenance not enforced at creation time
- Hash verification separate from chain-of-custody
- No immutable artifact envelope

**V2 Requirement Type**: **Architecture Fitness Rule + Integration Test**

**V2 Acceptance Criteria**:
1. Every final text has complete Provenance: model, prompt version, contract hash, parent Canon commit
2. Artifact envelope includes: schema, producer, input refs, timestamps
3. Missing provenance blocks publication
4. Hash verification includes input binding
5. Audit trail can reconstruct generation chain

**V2 Test Asset**: `test_final_text_complete_provenance`
- Generate chapter
- Retrieve final artifact
- Assert presence: model_id, prompt_version, contract_version, parent_commit_id, generation_timestamp
- Assert: Can reconstruct input context from provenance
- Negative: Missing any provenance field → blocks publication

---

### RF-013: God Package - Excessive Coupling in serialize/loop.py

**V1 Failure**: Single 2907-line file handles context, prompts, contracts, revisions, decisions, facts, checkpoints.

**V1 Evidence**:
- `/ainovel/AI-Novel-Runtime/runtime/serialize/loop.py` - 2907 lines
- PROJECT_DEEP_ANALYSIS.md: "增加检查器往往需要在该函数插入新分支"

**Root Cause**:
- Incremental feature addition without refactoring
- No separation of concerns (orchestration vs decision vs I/O)
- Difficult to test individual stages

**V2 Requirement Type**: **Architecture Fitness Rule**

**V2 Acceptance Criteria**:
1. No single module > 500 lines (excluding data/config)
2. Clear separation: Orchestration / Compilation / Generation / Validation / Decision / Commit
3. Each stage has explicit interface and test seam
4. Adding new quality check doesn't require editing orchestrator

**V2 Architecture Rule**: `ARCH-COUPLING-001`
- Rule: Core production pipeline composed of single-responsibility services
- Verification: Module size limit, dependency graph analysis
- Fitness function: `max_module_lines <= 500`, `cyclomatic_complexity < 15`

**V2 Test Asset**: Fitness test runs on every commit, fails if module exceeds limits

---

### RF-014: Duplicate Orchestration Implementations

**V1 Failure**: Multiple overlapping orchestration paths (main serial, scheduler wrapper, contract integration wrapper, chapter internal orchestrator); some unreachable.

**V1 Evidence**:
- PROJECT_DEEP_ANALYSIS.md: "当前有主串行流程、scheduler 包装器、另一个合同集成包装器，以及 `chapter` 内部再一套生产 orchestrator"
- Fitness report: 8 unreachable modules including contract integration

**Root Cause**:
- Multiple refactoring attempts without removing old code
- Unclear migration status between implementations
- "Design forming" vs "production active" not distinguished

**V2 Requirement Type**: **Architecture Fitness Rule**

**V2 Acceptance Criteria**:
1. Single canonical production workflow implementation
2. No unreachable modules in production code
3. Experimental/alternative implementations in separate namespace, not mixed with production
4. Clear deprecation markers and migration plan for old code

**V2 Architecture Rule**: `ARCH-REACHABILITY-001`
- Rule: All production modules must be reachable from main entry points
- Verification: Static call graph analysis
- Unreachable modules → move to experimental/ or delete

**V2 Test Asset**: `test_no_unreachable_production_modules`
- Build call graph from CLI/API entry points
- Assert: All modules in production/ reachable
- Report unreachable modules as failures

---

### RF-015: Provider-Domain Coupling (Hardcoded Model Assumptions)

**V1 Failure**: Domain logic coupled to specific provider capabilities; difficult to swap models.

**V1 Evidence**: Documented in architecture review as coupling risk

**Root Cause**:
- No clear provider abstraction boundary
- Capability negotiation not explicit
- Model-specific prompt engineering in domain logic

**V2 Requirement Type**: **Contract Test + Architecture Fitness Rule**

**V2 Acceptance Criteria**:
1. Domain logic depends on ModelCapability interface, not specific provider
2. Provider capabilities declared explicitly (context length, streaming, JSON mode)
3. Model selection based on capability requirements, not hardcoded names
4. Switching provider doesn't require domain code changes

**V2 Test Asset**: `test_provider_swappable`
- Execute same workflow with Provider A, then Provider B
- Assert: Same inputs → equivalent outputs (allowing model variance)
- Assert: No provider-specific logic in domain modules

**V2 Architecture Rule**: `ARCH-PROVIDER-001`
- Rule: Domain modules import from provider abstraction, not concrete clients
- Verification: Dependency analysis, no direct imports of openai/anthropic/etc in domain

---

### RF-016: Unlocked Dependency Versions

**V1 Failure**: requirements.txt uses lower-bound only (no upper bound or lock); test environment not reproducible.

**V1 Evidence**:
- PROJECT_DEEP_ANALYSIS.md: "没有发现 pyproject/pytest 配置或 Python 依赖锁；requirements 主要是下界版本"

**Root Cause**:
- No lock file (requirements.lock, poetry.lock, Pipfile.lock)
- Dependencies can break builds on minor updates
- Tests succeed locally, fail in different environments

**V2 Requirement Type**: **Architecture Fitness Rule + CI Gate**

**V2 Acceptance Criteria**:
1. Locked dependency file (requirements.lock or poetry.lock)
2. Reproducible builds across environments
3. Automated dependency update workflow with tests
4. CI uses locked dependencies

**V2 Test Asset**: `test_dependency_lock_present`
- CI checks for presence of lock file
- CI installs from lock file, not loose requirements
- Security scan of dependencies

---

### RF-017: Test False-Pass Due to Return Statement

**V1 Failure**: Tests return False instead of asserting; pytest collects them as passing.

**V1 Evidence**:
- PROJECT_DEEP_ANALYSIS.md: "37 条 warning 中多项为 `PytestReturnNotNoneWarning`"
- Three confirmed false-pass tests:
  - `test_end_to_end_genre.py::test_dushi_end_to_end_consistency`
  - `test_p0_fixes.py::test_p0_3_no_fantasy_world_rules`
  - `test_xuanhuan_regression.py::test_power_system_in_xuanhuan`

**Root Cause**:
- Return statement instead of assert
- pytest warnings not escalated to errors
- False sense of test coverage

**V2 Requirement Type**: **CI Gate + Regression Fixture**

**V2 Acceptance Criteria**:
1. All tests use assert, not return
2. pytest configured to treat return-not-none as error
3. CI fails on any pytest warnings
4. Test audit identifies false-pass patterns

**V2 Test Asset**: `test_no_false_pass_tests`
- CI linter scans for `return True/False` in test functions
- pytest.ini: `--strict-markers`, `-Werror`
- All V1 false-pass tests converted to real assertions

---

### RF-018: Hardcoded Character Details

**V1 Failure**: Character attributes hardcoded in prompts/code instead of derived from facts.

**V1 Evidence**: Referenced in V1 analysis findings

**Root Cause**:
- Shortcut during development
- No enforcement that character data comes from Canon
- Template/prompt contains facts instead of referencing them

**V2 Requirement Type**: **Contract Test**

**V2 Acceptance Criteria**:
1. Character details loaded from Canon facts, not hardcoded
2. Prompts reference fact IDs, don't duplicate content
3. Character context compiled from current Canon head
4. Test: Change Canon fact → prompt context changes

**V2 Test Asset**: `test_character_details_from_canon`
- Define character in Canon
- Generate context for scene
- Assert: Character details from fact, not template
- Change fact attribute → context reflects change

---

### RF-019: Budget Tracking Incomplete (Replaced Instead of Accumulated)

**V1 Failure**: Budget spent replaced on each run instead of accumulated; historical cost lost.

**V1 Evidence**:
- PROJECT_DEEP_ANALYSIS.md: "`budget_spent` 也直接替换为本轮值，累计运行可能漏掉历史成本"

**Root Cause**:
- Budget state overwritten instead of merged
- No persistent cost ledger
- Resume doesn't account for previous attempts

**V2 Requirement Type**: **Integration Test**

**V2 Acceptance Criteria**:
1. Budget accumulates across runs (addition, not replacement)
2. Persistent cost ledger per workflow/project
3. Cost breakdown by: run, chapter, model call
4. Resume loads historical cost before checking remaining budget

**V2 Test Asset**: `test_budget_accumulation_across_runs`
- Run 1: Generate 1 chapter, cost $5
- Run 2: Generate 1 more chapter, cost $3
- Assert: total_cost = $8 (not $3)
- Assert: Remaining budget = initial - $8

---

### RF-020: Resume Workflow Without Input Validation Entry Point

**V1 Failure**: Different workflow entry points (start, resume, step, run_batch) don't share unified validation; budget checks inconsistent.

**V1 Evidence**:
- PROJECT_DEEP_ANALYSIS.md: "budget 检查只在部分入口调用：`step`、`run_batch`、`run_to_completion` 没有共享同一个准入入口"

**Root Cause**:
- Code duplication across entry points
- No unified pre-flight check
- Inconsistent validation leads to bypass vulnerabilities

**V2 Requirement Type**: **Architecture Fitness Rule + Contract Test**

**V2 Acceptance Criteria**:
1. Single WorkflowGateway validates all entries
2. Budget, input hash, authorization checked uniformly
3. No direct access to workflow executor bypassing gateway
4. Gateway enforces: project scope, budget, input consistency, authorization

**V2 Test Asset**: `test_workflow_gateway_enforces_all_entries`
- Attempt start/resume/step with: insufficient budget, invalid input, unauthorized project
- Assert: All entry points reject uniformly
- No bypass path exists

**V2 Architecture Rule**: `ARCH-GATEWAY-001`
- Rule: All workflow operations go through unified gateway
- Verification: No direct instantiation of workflow executor outside gateway

---

### RF-021: AI Writing Pattern Leakage (39% of Chapters)

**V1 Failure**: AI writing patterns detected in 39% of chapters ("深吸", "瞳孔", "心头" repetition).

**V1 Evidence**:
- `/ainovel/audit-reports/FINAL_AUDIT_REPORT.md` - 61 instances across 39/100 chapters

**Root Cause**:
- No stylistic diversity enforcement
- Pattern detection post-hoc, not preventive
- No phrase usage tracking during generation

**V2 Requirement Type**: **Integration Test + Quality Gate**

**V2 Acceptance Criteria**:
1. Phrase repetition detection during generation (not just audit)
2. Configurable pattern blocklist per genre
3. Q4/Q5 (style quality) includes repetition metrics
4. Warning threshold: >2 instances per chapter
5. Block threshold: >5 instances (configurable)

**V2 Test Asset**: `test_ai_pattern_detection_blocks_excessive_repetition`
- Generate text with 10 instances of "深吸一口气"
- Assert: Quality check detects pattern
- Assert: Decision engine flags for revision or rejects
- Assert: Pattern metrics in quality report

---

## P2 Failures - Maintainability

### RF-022: Build Reproducibility Missing (No CI Config, No Lock)

**V1 Failure**: No CI configuration, no pytest config, no dependency lock; tests depend on excluded artifacts or old paths.

**V1 Evidence**:
- PROJECT_DEEP_ANALYSIS.md: "没有发现 GitLab/GitHub CI 配置、pyproject/pytest 配置或 Python 依赖锁"
- Tests depend on `.gitignore` excluded artifacts or hardcoded paths

**Root Cause**:
- Manual testing workflow, no automation
- No infrastructure-as-code for test environment
- Path dependencies not portable

**V2 Requirement Type**: **CI Gate + Architecture Fitness Rule**

**V2 Acceptance Criteria**:
1. CI configuration present (.github/workflows or .gitlab-ci.yml)
2. pytest.ini with test discovery, coverage, markers
3. pyproject.toml or setup.py with dependencies
4. All tests pass in clean checkout with locked dependencies
5. No hardcoded absolute paths in tests

**V2 Test Asset**: CI pipeline itself
- Clean checkout
- Install from lock file
- Run all tests
- Coverage report
- Fail on <80% coverage for core modules

---

### RF-023: Stale Documentation (README vs Actual Capabilities)

**V1 Failure**: README lists scheduler/Genesis/approval queue as missing, but code already implements them; CLAUDE.md emergency items already done.

**V1 Evidence**:
- PROJECT_DEEP_ANALYSIS.md: "README 仍把 scheduler、真实 Genesis、审批队列、长弧规划列为缺失，但源码已有相关模块"

**Root Cause**:
- Documentation not updated with code
- No doc-code sync validation
- Old planning docs persist as status docs

**V2 Requirement Type**: **Process Requirement**

**V2 Acceptance Criteria**:
1. Documentation status matches actual implementation
2. Automated doc generation for APIs/schemas
3. Manual docs reviewed quarterly
4. Clear marking: [IMPLEMENTED] / [PLANNED] / [DEPRECATED]
5. ADRs record why features added/removed

**V2 Test Asset**: Documentation audit checklist
- Cross-reference README features with module presence
- Flag mismatches
- Update docs or code to align

---

## Summary Statistics

| Category | Count | Test Assets | Architecture Rules | Contracts |
|---|---|---|---|---|
| P0 Critical | 2 | 2 | 2 | 0 |
| P1 High | 19 | 15 | 8 | 8 |
| P2 Medium | 2 | 1 | 1 | 0 |
| **Total** | **23** | **18** | **11** | **8** |

---

## V2 Integration Requirements

### Regression Test Suite Structure

```
tests/
  regression/
    v1_failures/
      test_rf001_secret_scanning.py
      test_rf002_atomic_commit.py
      test_rf003_blocked_progression.py
      ...
    fixtures/
      v1_failure_scenarios/
        blocked_workflow.yaml
        gap_resume.yaml
        genre_confusion.yaml
        ...
```

### Architecture Fitness Functions

```python
# fitness/arch_rules.py
def check_atomic_commit_boundary():
    """ARCH-ATOM-001: Canon mutations in transaction"""
    
def check_single_decision_authority():
    """ARCH-AUTHORITY-001: Only decision engine authorizes commits"""
    
def check_module_coupling():
    """ARCH-COUPLING-001: No god objects > 500 lines"""
    
def check_provider_abstraction():
    """ARCH-PROVIDER-001: Domain isolated from provider details"""
```

### Contract Test Matrix

| Contract | Positive Cases | Negative Cases | Edge Cases |
|---|---|---|---|
| ChapterDependencyContract | Valid parent permit | Blocked parent | Concurrent commits |
| WorkflowInputIntegrityContract | Unchanged input resume | Changed input resume | Partial change |
| GenrePackContract | Pure urban, pure xianxia | Xianxia+rebirth→urban | Fusion genre |
| CanonCommitContract | Complete provenance | Missing model_id | Orphan facts |

---

## Acceptance Gate for V2

V2 CANNOT ship to production until:

1. All P0 regression tests pass (RF-001, RF-002)
2. All P1 regression tests implemented and pass (RF-003 through RF-021)
3. Architecture fitness rules enforced in CI (11 rules)
4. Contract tests cover identified failure modes (8 contracts)
5. V1 failure reproduction suite runs on every commit
6. Zero false-pass tests (RF-017)
7. Build reproducibility verified (RF-022)

---

## Maintenance

This register is a living document:
- Add new V1 failures as discovered
- Update when V2 tests implemented
- Track regression prevention in ADRs
- Review quarterly for coverage gaps

**Next Update**: After V2 P0 completion (V2-001 through V2-004)
