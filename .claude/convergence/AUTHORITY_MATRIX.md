# ANovel V2 Authority Matrix

**Document ID**: CONV-0004  
**Version**: 1.0  
**Status**: NORMATIVE  
**Created**: 2026-09-19  
**Authority**: CONVERGENCE-BASELINE  
**Depends On**:
- PROJECT_CONSTITUTION.md (Section 9: Authority Model, Section 20: Human Authority)
- NORMATIVE_INDEX.md (T0-T7 Truth Hierarchy)
- TERMINOLOGY_BASELINE.md (Authority definitions)
- canon-commit-policy.yaml
- context-policy.yaml
- All domain specifications

**Purpose**: Define who/what can perform each critical operation in ANovel V2, with authority levels, gate conditions, and invariants.

---

## 0. Authority Model Foundation

### 0.1 Authority Types (from CONSTITUTION Section 9)

| Authority | Meaning | Can Direct Write Canon | Truth Tier |
|-----------|---------|------------------------|------------|
| **constitution** | Project root principles | No (principles, not narrative) | T0 |
| **architecture** | Approved architectural rules | No | T1 |
| **genre** | Genre domain rules | No (can block commits) | T2 |
| **canon** | Committed story facts | Is Canon (already truth) | T3 |
| **contract** | Production constraints | No (validates, doesn't write) | T4 |
| **plan** | Future intentions | No | T4 |
| **human_approval** | Human authorization | Yes (via approval trigger) | Override |
| **reference** | Reference evidence | No | T5 |
| **corpus** | Aggregated corpus evidence | No | T5 |
| **market** | Market evidence | No | T5 |
| **model** | LLM output | No | T6/T7 |
| **diagnostic** | Evaluation/analysis | No | T7 |
| **draft** | Candidate text | No | T6 |

### 0.2 Key Principles

**INV-004**: Canon writes ONLY through CanonCommit boundary  
**P-003**: Draft is NOT Canon  
**P-010**: AI Judge is not Ground Truth  
**P-011**: Reference Evidence cannot write Canon directly  
**PROHIBIT-003**: Draft/Writer/Reviewer cannot write Canon directly  
**PROHIBIT-009**: Single AI Judge cannot have Commit Authority

---

## 1. OPERATION: Produce Candidate (Draft Text)

### 1.1 Who Can Trigger

| Entity | Can Trigger | Authority Level | Conditions |
|--------|-------------|-----------------|------------|
| **Production Workflow** | ✅ YES | System | Valid WorkflowRun, Stage=GENERATE |
| **Writer Worker** | ✅ YES | Worker | Valid ContextArtifact provided |
| **Human** | ✅ YES | Human Override | Manual generation mode |
| **Repair Worker** | ✅ YES | Worker | After RepairPlan approved |

### 1.2 Who Can Block

| Entity | Can Block | Authority Level | Block Condition |
|--------|-----------|-----------------|-----------------|
| **Missing Contract** | ✅ YES | Production Policy | canon-commit-policy.yaml: missing_contract=BLOCK |
| **Stale Canon Parent** | ✅ YES | Production Policy | context-policy.yaml: CTX-POL-004 |
| **Missing Context** | ✅ YES | Production Policy | No valid ContextArtifact |
| **Invalid Project/Branch** | ✅ YES | Production Policy | context-policy.yaml: CTX-POL-003 |

### 1.3 Gate Conditions (MUST be true)

```yaml
preconditions:
  - valid_context_artifact_exists: true
  - context_has_mandatory_items: true
  - chapter_contract_or_scene_contract_exists: true
  - canon_parent_is_current: true
  - genre_pack_bound: true
  - project_branch_isolation: true
```

### 1.4 Invariants (MUST preserve)

- **Draft produced ≠ Canon updated** (P-003, PROHIBIT-003)
- **Draft has no Authority** (T6 artifact)
- **Draft MUST have content hash** for later validation binding
- **Writer MUST NOT read Canon write API** (Architecture Fitness)

### 1.5 Output Authority

**Authority**: `draft` (T6)  
**Can Become Canon**: No (requires full validation + CommitPermit + CanonCommit)

---

## 2. OPERATION: Write Draft (Synonym: Produce Candidate)

*Same as Operation 1 above.*

---

## 3. OPERATION: Write Plan

### 3.1 Who Can Trigger

| Entity | Can Trigger | Authority Level | Conditions |
|--------|-------------|-----------------|------------|
| **Planner Worker** | ✅ YES | Worker | Valid Canon state, SeriesVision |
| **Production Workflow** | ✅ YES | System | Stage=PLANNING |
| **Human** | ✅ YES | Human Override | Manual planning mode |
| **Genesis Phase** | ✅ YES | System | Initial SeriesVision creation |

### 3.2 Who Can Block

| Entity | Can Block | Authority Level | Block Condition |
|--------|-----------|-----------------|-----------------|
| **Genre Constitution** | ✅ YES | T2 | Plan violates Genre Hard Rules |
| **Canon** | ✅ YES (implicitly) | T3 | Plan cannot contradict committed Canon |
| **Missing GenesisSpec** | ✅ YES | Production Policy | No foundation for planning |

### 3.3 Gate Conditions

```yaml
preconditions:
  - genesis_spec_or_series_vision_exists: true
  - genre_pack_bound: true
  - canon_head_known: true
  - plan_does_not_violate_genre_hard_rules: true
  - plan_does_not_contradict_canon: true
```

### 3.4 Invariants

- **Plan is intention, Canon is history** (P-017, PLANNING spec principle 3)
- **Plan vs Canon conflict → Plan must re-plan** (CONSTITUTION Section 8)
- **Plans are versioned and replaceable** (PLANNING spec principle 4)
- **Plan cannot directly mutate Canon** (PLANNING spec principle 18)
- **Plan cannot override Genre Constitution** (PLANNING spec principle 19)

### 3.5 Output Authority

**Authority**: `plan` (T4)  
**Can Become Canon**: No (guides production, doesn't write truth)

---

## 4. OPERATION: Write Contract (ChapterContract, SceneContract)

### 4.1 Who Can Trigger

| Entity | Can Trigger | Authority Level | Conditions |
|--------|-------------|-----------------|------------|
| **Planner Worker** | ✅ YES | Worker | From ArcPlan/ChapterPlan |
| **Production Workflow** | ✅ YES | System | Stage=CONTRACT_COMPILATION |
| **Human** | ✅ YES | Human Override | Manual contract authoring |

### 4.2 Who Can Block

| Entity | Can Block | Authority Level | Block Condition |
|--------|-----------|-----------------|-----------------|
| **Genre Constitution** | ✅ YES | T2 | Contract requires forbidden transitions |
| **Canon State** | ✅ YES | T3 | Contract assumes impossible state |
| **Missing Plan** | ⚠️ SHOULD | Production Policy | No plan to derive contract from |

### 4.3 Gate Conditions

```yaml
preconditions:
  - parent_plan_exists: true (SHOULD)
  - canon_parent_bound: true
  - genre_pack_bound: true
  - required_transitions_defined: true
  - forbidden_transitions_defined: true
  - contract_does_not_violate_genre: true
```

### 4.4 Invariants

- **Contract binds Canon parent** (PLANNING spec principle 6)
- **Contract binds GenrePack version** (PLANNING spec principle 6)
- **Contract declares required/forbidden/protected transitions** (PLANNING spec principle 7)
- **Contract missing in Production = BLOCK** (PLANNING spec principle 8)
- **Contract cannot directly mutate Canon** (PLANNING spec principle 18)

### 4.5 Output Authority

**Authority**: `contract` (T4)  
**Can Block Production**: YES (missing contract blocks in Production mode)

---

## 5. OPERATION: Sign Permit (CommitPermit)

### 5.1 Who Can Trigger

| Entity | Can Trigger | Authority Level | Conditions |
|--------|-------------|-----------------|------------|
| **CanonCommit Service** | ✅ YES (only path) | System | After all validations pass |
| **Validation Orchestrator** | ✅ YES | System | Coordinates validation layers |

### 5.2 Who Can Block

| Entity | Can Block | Authority Level | Block Condition |
|--------|-----------|-----------------|-----------------|
| **Q0 Deterministic Integrity** | ✅ YES | Hard Gate | Schema/hash/integrity failure |
| **Q1 Canon Consistency** | ✅ YES | Hard Gate | Canon conflict detected |
| **Q2 Genre Fidelity** | ✅ YES | Hard Gate | Genre Hard Rule violated |
| **Q3 Transition Correctness** | ✅ YES | Hard Gate | Required transition missing or forbidden transition present |
| **Missing Contract** | ✅ YES | Production Policy | canon-commit-policy.yaml: missing_contract=BLOCK |
| **Missing Valid Parent** | ✅ YES | Production Policy | canon-commit-policy.yaml: parent_mismatch=BLOCK |
| **Text Hash Mismatch** | ✅ YES | Production Policy | canon-commit-policy.yaml: text_hash_mismatch=BLOCK |
| **Immutable Fact Mutation** | ✅ YES | Production Policy | canon-commit-policy.yaml: immutable_fact_mutation=BLOCK |
| **Unregistered Extension** | ✅ YES | Production Policy | canon-commit-policy.yaml: unregistered_extension=BLOCK |
| **Continuity Hard Error** | ✅ YES | Production Policy | canon-commit-policy.yaml: continuity_hard_error=BLOCK |

**Note**: Q4-Q6 (soft gates) provide feedback but cannot block Permit.

### 5.3 Gate Conditions (ALL MUST pass)

```yaml
hard_gates_passed:
  Q0_deterministic_integrity: PASS
  Q1_canon_consistency: PASS
  Q2_genre_fidelity: PASS
  Q3_transition_correctness: PASS

permit_requirements:
  - valid_parent: true
  - valid_changeset: true
  - source_text_hash_bound: true
  - contract_hash_bound: true
  - genre_pack_hash_bound: true
  - policy_hash_bound: true
  - idempotency_key: present
```

### 5.4 Invariants

- **Permit MUST reference exact Draft hash** (INV-005: evaluated text hash = accepted text hash)
- **Permit MUST bind Contract** (canon-commit-policy.yaml)
- **Permit MUST bind GenrePack** (canon-commit-policy.yaml)
- **Permit MUST bind Policy version** (canon-commit-policy.yaml)
- **Permit does NOT authorize Canon write** (only confirms eligibility)

### 5.5 Who Can Sign (Authority to Issue)

**ONLY**: CanonCommit Service (after validation orchestration completes)

**Cannot Sign**:
- ❌ Writer Worker
- ❌ Single AI Judge (PROHIBIT-009)
- ❌ Quality Reviewer alone
- ❌ Draft process
- ❌ Reference material

### 5.6 Output Authority

**Authority**: `commit_permit` (gate artifact)  
**Effect**: Enables CanonCommit operation (does not execute it)

---

## 6. OPERATION: Modify Canon (via CanonCommit)

### 6.1 Who Can Trigger

| Entity | Can Trigger | Authority Level | Conditions |
|--------|-------------|-----------------|------------|
| **CanonCommit Service** | ✅ YES (ONLY PATH) | System | Valid CommitPermit + ChangeSet |
| **Human via Approval** | ✅ YES | Human Override | Triggers CanonCommit with approval |

**Prohibited Triggers** (PROHIBIT-003, INV-004):
- ❌ Writer Worker directly
- ❌ Draft process directly
- ❌ Reviewer directly
- ❌ Reference system
- ❌ Any second Canon store
- ❌ Silent background process

### 6.2 Who Can Block

| Entity | Can Block | Authority Level | Block Condition |
|--------|-----------|-----------------|-----------------|
| **Missing Permit** | ✅ YES | Production Policy | canon-commit-policy.yaml: missing_permit=BLOCK |
| **Idempotency Violation** | ✅ YES | System | Duplicate idempotency_key |
| **Parent Mismatch** | ✅ YES | Production Policy | Parent hash doesn't match Canon HEAD |

### 6.3 Gate Conditions

```yaml
preconditions:
  - commit_permit_valid: true
  - changeset_valid: true
  - parent_hash_matches_canon_head: true
  - idempotency_key_unique: true
  - all_hard_gates_passed: true
```

### 6.4 Invariants (CRITICAL)

- **INV-004**: Canon Commit is the ONLY write boundary
- **INV-003**: Canon Commit MUST reference valid parent snapshot/head
- **INV-005**: Hash of evaluated text = hash of committed text
- **INV-009**: Canon SHOULD be rebuildable from Event Log + reducer
- **P-004**: Canon Changes only through Canon Commit
- **PROHIBIT-002**: No second Canon Store
- **PROHIBIT-010**: No Silent Retcon (modification requires explicit Retcon operation)

### 6.5 Output Authority

**Authority**: `canon` (T3 - truth)  
**Effect**: Appends to Canon Event Log, updates Canon HEAD, creates new Canon Snapshot

---

## 7. OPERATION: Push Canon Head

### 7.1 Who Can Trigger

| Entity | Can Trigger | Authority Level | Conditions |
|--------|-------------|-----------------|------------|
| **CanonCommit Service** | ✅ YES (automatic) | System | After successful CanonCommit |

### 7.2 Who Can Block

*No additional blocks beyond CanonCommit blocks (Operation 6).*

### 7.3 Gate Conditions

```yaml
preconditions:
  - canon_commit_succeeded: true
  - event_log_append_succeeded: true
  - snapshot_build_succeeded: true
```

### 7.4 Invariants

- **Canon HEAD always points to latest valid commit**
- **HEAD movement is atomic with CanonCommit**
- **Old snapshots remain immutable**

---

## 8. OPERATION: Retcon (R1, R2, R3)

### 8.1 Who Can Trigger

| Retcon Level | Can Trigger | Authority Level | Conditions |
|--------------|-------------|-----------------|------------|
| **R1 (Soft)** | Annotator Service | System | Annotation/interpretation change |
| **R2 (Medium)** | Canon Service + Review | System + Approval | Minor fact correction |
| **R3 (Hard)** | **Human Authority REQUIRED** | Human | Major past rewrite |

**Source**: canon-commit-policy.yaml: `human_authority_default_for: [R3_retcon, world_rule_change, identity_correction, published_history_change]`

### 8.2 Who Can Block

| Entity | Can Block | Authority Level | Block Condition |
|--------|-----------|-----------------|-----------------|
| **Human Authority Required** | ✅ YES | Human Gate | R3 without human approval |
| **Published History** | ✅ YES | Human Gate | Modifying published content requires human authority |
| **World Rule Change** | ✅ YES | Human Gate | Requires human authority (canon-commit-policy.yaml) |
| **Identity Correction** | ✅ YES | Human Gate | Core identity changes require human authority |

### 8.3 Gate Conditions

```yaml
R1_soft_retcon:
  - annotation_change_only: true
  - no_fact_mutation: true

R2_medium_retcon:
  - state_correction_justified: true
  - impact_analysis_complete: true
  - invalidation_cascade_prepared: true

R3_hard_retcon:
  - human_authority_granted: true (REQUIRED)
  - major_rewrite_rationale: documented
  - invalidation_cascade_prepared: true
  - dependent_artifacts_identified: true
```

### 8.4 Invariants

- **PROHIBIT-010**: Silent Retcon is forbidden
- **Retcon MUST trigger invalidation cascade** (CANONICAL_STATE_SPEC)
- **Retcon MUST be logged in Canon Event Log**
- **R3 always requires human authority** (canon-commit-policy.yaml)

### 8.5 Output Authority

**Authority**: `canon` (T3 - modifies truth with explicit justification)  
**Effect**: Invalidates dependent artifacts, updates Canon state, logs Retcon event

---

## 9. OPERATION: Modify Genre Hard Rule

### 9.1 Who Can Trigger

| Entity | Can Trigger | Authority Level | Conditions |
|--------|-------------|-----------------|------------|
| **Human Authority** | ✅ YES | Human | Major genre change |
| **Genre Designer** | ✅ YES (with approval) | Human-supervised | GenrePack versioning |

**Source**: CONSTITUTION Section 20: "Major Genre Change" requires Human Authority

### 9.2 Who Can Block

| Entity | Can Block | Authority Level | Block Condition |
|--------|-----------|-----------------|-----------------|
| **Active Production** | ⚠️ SHOULD | Policy | Changing rules mid-production risks inconsistency |
| **Committed Canon** | ⚠️ WARNING | T3 | Rule change may retroactively invalidate Canon |

### 9.3 Gate Conditions

```yaml
preconditions:
  - human_authority_granted: true
  - genre_pack_version_incremented: true
  - impact_on_existing_canon_analyzed: true
  - migration_path_defined: true (if mid-production)
```

### 9.4 Invariants

- **P-002**: Genre is foundational domain (changes cascade widely)
- **P-009**: Market trend cannot silently modify Genre truth
- **INV-001**: Production MUST bind versioned GenrePack
- **Genre Hard Rule changes require new GenrePack version**
- **Existing Canon committed under old rules remains valid** (unless Retcon applied)

### 9.5 Output Authority

**Authority**: `genre` (T2)  
**Effect**: New GenrePack version, future production uses new rules

---

## 10. OPERATION: Modify Policy

### 10.1 Who Can Trigger

| Entity | Can Trigger | Authority Level | Conditions |
|--------|-------------|-----------------|------------|
| **Human Authority** | ✅ YES | Human | Policy change approval |
| **Learning System** | ❌ NO (auto) | System | Cannot auto-modify production policy (CONSTITUTION Section 20) |
| **Experiment Promotion** | ✅ YES (gated) | System | After promotion gate passes |

**Source**: CONSTITUTION Section 20: "从 diagnostic signal 自动学习并修改 Production Policy" requires Human Authority

### 10.2 Who Can Block

| Entity | Can Block | Authority Level | Block Condition |
|--------|-----------|-----------------|-----------------|
| **Human Approval Required** | ✅ YES | Human Gate | Auto-learning cannot deploy to production |
| **Failed Promotion Gate** | ✅ YES | System | Experiment didn't beat baseline |
| **Insufficient Evidence** | ✅ YES | System | No E4 (real reader) validation |

### 10.3 Gate Conditions

```yaml
preconditions:
  - human_authority_granted: true (for production policy)
  - experiment_passed_promotion_gate: true (if from learning)
  - real_reader_signal_exists: true (E4 evidence, if available)
  - policy_version_incremented: true
  - backward_compatibility_assessed: true
```

### 10.4 Invariants

- **Policy changes MUST be versioned** (PROHIBIT-012)
- **Active runs MUST complete under original policy** (or explicit migration)
- **Policy cannot violate Constitution principles** (T0 > T1)
- **Diagnostic signal alone cannot auto-deploy policy** (CONSTITUTION Section 20)

### 10.5 Output Authority

**Authority**: `architecture` / `policy` (T1)  
**Effect**: New policy version active for future runs

---

## 11. OPERATION: Publish

### 11.1 Who Can Trigger

| Entity | Can Trigger | Authority Level | Conditions |
|--------|-------------|-----------------|------------|
| **Human Authority** | ✅ YES (REQUIRED) | Human | External publishing decision |
| **Publishing Service** | ✅ YES (with approval) | System | After human approval |

**Source**: CONSTITUTION Section 20: "外部发布" and "平台上架" require Human Authority

### 11.2 Who Can Block

| Entity | Can Block | Authority Level | Block Condition |
|--------|-----------|-----------------|-----------------|
| **Human Approval Missing** | ✅ YES | Human Gate | No external action without approval |
| **Not PUBLISH_READY** | ✅ YES | Production State | Must reach PUBLISH_READY state first |
| **Uncommitted Draft** | ✅ YES | System | Only committed Canon can be published |

### 11.3 Gate Conditions

```yaml
preconditions:
  - human_approval_granted: true (REQUIRED)
  - production_state: PUBLISH_READY
  - canon_committed: true
  - platform_requirements_met: true
  - copyright_check_passed: true
```

### 11.4 Invariants

- **PUBLISH_READY ≠ auto-publish** (CONSTITUTION Section 13: state is qualification, not trigger)
- **Publishing is irreversible external action** (requires human gate)
- **Published content requires provenance** (for auditability)

### 11.5 Output Authority

**Authority**: `human_approval` (override)  
**Effect**: Content visible on external platform

---

## 12. OPERATION: Promote New Prompt/Model/Policy

### 12.1 Who Can Trigger

| Entity | Can Trigger | Authority Level | Conditions |
|--------|-------------|-----------------|------------|
| **Learning System** | ✅ YES (if gated) | System | After promotion gate passes |
| **Human Authority** | ✅ YES | Human | Manual promotion decision |
| **Experiment Framework** | ✅ YES (automated) | System | Gates passed + policy allows |

### 12.2 Who Can Block

| Entity | Can Block | Authority Level | Block Condition |
|--------|-----------|-----------------|-----------------|
| **Promotion Gate** | ✅ YES | System | Experiment didn't beat baseline |
| **Insufficient Evidence** | ✅ YES | System | No statistical significance |
| **Real Reader Signal Missing** | ⚠️ SHOULD | System | E4 evidence preferred for production |
| **Human Approval** | ✅ YES (for prod) | Human | Production deployment requires approval |

### 12.3 Gate Conditions

```yaml
promotion_gate_requirements:
  - experiment_vs_baseline: win
  - statistical_significance: true
  - holdout_set_validation: passed
  - real_reader_signal_positive: true (E4, if available)
  - regression_suite_passed: true
  - cost_impact_acceptable: true
  - human_approval_granted: true (for production)

versioning:
  - prompt_version_incremented: true
  - model_policy_version_incremented: true
  - provenance_recorded: true
```

### 12.4 Invariants

- **P-020**: Reader/Market signal eventually calibrates AI metrics
- **PROHIBIT-012**: No unversioned Prompt/Schema/Policy in Production
- **Promotion requires beating baseline** (CORPUS_EVALUATION_LEARNING_SPEC)
- **E1-E3 signals are diagnostic** until calibrated with E4 (real reader)

### 12.5 Output Authority

**Authority**: `architecture` / `policy` (T1, after promotion)  
**Effect**: New model/prompt/policy active for production

---

## 13. REFERENCE MATERIAL AUTHORITY

### 13.1 What Reference Can Do

| Operation | Permitted | Authority Level | Notes |
|-----------|-----------|-----------------|-------|
| **Inform Genesis** | ✅ YES | T5 (evidence) | Via ReferencePack |
| **Inform Planning** | ✅ YES | T5 (evidence) | Mechanism learning |
| **Provide Evidence** | ✅ YES | T5 (evidence) | Pattern extraction |
| **Suggest Patterns** | ✅ YES | T5 (evidence) | Narrative functions |

### 13.2 What Reference Cannot Do

| Operation | Prohibited | Principle | Consequence |
|-----------|------------|-----------|-------------|
| **Write Canon Directly** | ❌ FORBIDDEN | P-011, INV-007 | Reference is evidence, not truth |
| **Override Genre** | ❌ FORBIDDEN | T5 < T2 | Genre rules supersede reference |
| **Enter Writer Context Raw** | ❌ FORBIDDEN (default) | PROHIBIT-008, CTX-POL-002 | Continuous reference text forbidden |
| **Become Canon** | ❌ FORBIDDEN | T5 ≠ T3 | Must go through full production pipeline |

### 13.3 Authority Level

**Authority**: `reference` (T5)  
**Truth Status**: Evidence, not Canon  
**Relationship to Canon**: Reference → Genesis/Planning → Production → CanonCommit

### 13.4 Gate Enforcement

```yaml
reference_firewall:
  - reference_cannot_write_canon: true (INV-007)
  - reference_pack_is_abstracted: true (mechanism, not content)
  - originality_guard_active: true
  - writer_raw_reference_forbidden_by_default: true (CTX-POL-002)
```

---

## 14. MARKET SIGNAL AUTHORITY

### 14.1 What Market Signal Can Do

| Operation | Permitted | Authority Level | Notes |
|-----------|-----------|-----------------|-------|
| **Calibrate AI Metrics** | ✅ YES | T5 / E4 | Strongest commercial signal |
| **Inform Genre Design** | ✅ YES | T5 (evidence) | Via MarketTrendSnapshot |
| **Validate Experiments** | ✅ YES | E4 | Real reader data |
| **Guide Policy Tuning** | ✅ YES | T5 (evidence) | Informs learning |

### 14.2 What Market Signal Cannot Do

| Operation | Prohibited | Principle | Consequence |
|-----------|------------|-----------|-------------|
| **Silently Modify Genre** | ❌ FORBIDDEN | P-009 | Market trend ≠ Genre truth |
| **Override Canon** | ❌ FORBIDDEN | T5 < T3 | Market doesn't change story facts |
| **Auto-Deploy Policy** | ❌ FORBIDDEN (alone) | Section 20 | Requires human authority |
| **Replace Genre Constitution** | ❌ FORBIDDEN | T5 < T2 | Market informs, doesn't dictate rules |

### 14.3 Authority Level

**Authority**: `market` (T5)  
**Truth Status**: Evidence, not operational truth  
**Evidence Level**: E4 (highest confidence for commercial predictions)

### 14.4 Gate Enforcement

```yaml
market_signal_boundaries:
  - market_cannot_modify_genre_silently: true (P-009)
  - market_trend_is_timestamped: true
  - market_snapshot_has_provenance: true (platform/channel/time/source)
  - market_signal_informs_not_commands: true
```

---

## 15. AI JUDGE AUTHORITY

### 15.1 What AI Judge Can Do

| Operation | Permitted | Authority Level | Notes |
|-----------|-----------|-----------------|-------|
| **Evaluate Quality** | ✅ YES | T7 (diagnostic) | QualityReport output |
| **Compare Candidates** | ✅ YES | T7 (diagnostic) | Ranking |
| **Diagnose Issues** | ✅ YES | T7 (diagnostic) | Issue detection |
| **Provide Repair Guidance** | ✅ YES | T7 (diagnostic) | RepairPlan suggestions |
| **Score Soft Gates (Q4-Q6)** | ✅ YES | T7 (advisory) | Cannot block commits |

### 15.2 What AI Judge Cannot Do

| Operation | Prohibited | Principle | Consequence |
|-----------|------------|-----------|-------------|
| **Override Deterministic Checks** | ❌ FORBIDDEN | E1 > E2 | High score cannot override schema/canon violations |
| **Write Canon** | ❌ FORBIDDEN | PROHIBIT-009 | Judge is evaluator, not truth writer |
| **Block Commits Alone** | ❌ FORBIDDEN (Q4-Q6) | P-010 | Soft gates are advisory |
| **Be Ground Truth** | ❌ FORBIDDEN | P-010 | Judge outputs are evidence (T7), not truth |
| **Auto-Deploy Policy** | ❌ FORBIDDEN | Section 20 | Scores alone don't change production rules |

### 15.3 Authority Level

**Authority**: `diagnostic` (T7)  
**Truth Status**: Evidence for decision support, not truth  
**Evidence Levels**:
- Q0-Q3 (Hard Gates): E1 deterministic, system-enforced
- Q4-Q6 (Soft Gates): E2/E3 AI judgment, advisory only

### 15.4 Gate Enforcement

```yaml
ai_judge_boundaries:
  - judge_output_is_evidence_not_truth: true (P-010)
  - high_score_cannot_override_hard_gate: true
  - judge_cannot_have_commit_authority: true (PROHIBIT-009)
  - judge_outputs_require_calibration: true (vs E3/E4)
  - same_model_bias_measurable: true
```

### 15.5 Integration with Authority Model

**Q0-Q3 Hard Gates** → Can block CommitPermit (but logic is deterministic, not Judge opinion)  
**Q4-Q6 Soft Gates** → Cannot block, provide feedback only  
**Q7-Q8** → Human/Real Reader authority supersedes AI judgment

---

## 16. HUMAN APPROVAL AUTHORITY

### 16.1 What Human Approval Can Do

| Operation | Permitted | Authority Level | Notes |
|-----------|-----------|-----------------|-------|
| **Authorize R3 Retcon** | ✅ YES | Human (REQUIRED) | Major past rewrites |
| **Authorize Publishing** | ✅ YES | Human (REQUIRED) | External actions |
| **Authorize Major Genre Change** | ✅ YES | Human (REQUIRED) | Genre Constitution modifications |
| **Authorize World Rule Change** | ✅ YES | Human (REQUIRED) | canon-commit-policy.yaml |
| **Authorize Identity Correction** | ✅ YES | Human (REQUIRED) | canon-commit-policy.yaml |
| **Authorize Policy Deployment** | ✅ YES | Human (REQUIRED) | Production policy changes |
| **Override Gates** | ✅ YES | Human (emergency) | With explicit justification |
| **Resolve High-Risk Canon Conflicts** | ✅ YES | Human (REQUIRED) | CONSTITUTION Section 20 |

### 16.2 What Human Approval Cannot Override

| Constraint | Cannot Override | Reason |
|------------|-----------------|--------|
| **Constitution Principles** | ❌ NO | T0 is root authority |
| **Architecture Invariants** | ❌ NO (without ADR) | INV-001 to INV-015 are mandatory |
| **Prohibitions** | ❌ NO (without ADR) | PROHIBIT-001 to PROHIBIT-014 are hard constraints |

### 16.3 Authority Level

**Authority**: `human_approval` (override level)  
**Truth Status**: Can trigger truth changes (via CanonCommit), authorize high-stakes operations  
**Supersedes**: T1-T7 (but not T0)

### 16.4 Required Human Authority Operations (from CONSTITUTION Section 20)

```yaml
human_authority_required:
  - formal_retcon: R3
  - external_publishing: true
  - platform_release: true
  - major_genre_change: true
  - story_constitution_change: true
  - high_risk_canon_conflict_resolution: true
  - copyright_boundary_exception: true
  - production_policy_auto_learning_deployment: true
  - world_rule_change: true (canon-commit-policy.yaml)
  - identity_correction: true (canon-commit-policy.yaml)
  - published_history_change: true (canon-commit-policy.yaml)
```

### 16.5 Internal Automation Allowed (Without Human Gate)

```yaml
automated_with_constraints:
  - candidate_selection: true (within Genre/Canon/Contract gates)
  - controlled_repair: true (with protected facts)
  - quality_evaluation: true (diagnostic)
  - context_compilation: true (per authority priority)
  - plan_generation: true (cannot override Canon)
```

---

## 17. CROSS-CUTTING AUTHORITY RELATIONSHIPS

### 17.1 Authority Precedence (Conflict Resolution)

**From NORMATIVE_INDEX Section 1 (T0-T7 Hierarchy)**:

```
T0 Constitution
  ↓ supersedes
T1 Architecture/Policy
  ↓ supersedes
T2 Genre Constitution
  ↓ supersedes
T3 Canon (what happened)
  ↓ supersedes
T4 Plan/Contract (what should happen)
  ↓ supersedes
T5 External Evidence (Reference/Market)
  ↓ supersedes
T6 Draft/Candidate
  ↓ supersedes
T7 AI Analysis/Judge
```

**Conflict Resolution Rules**:
- Lower tier CANNOT override higher tier
- Plan vs Canon conflict → Canon wins, Plan re-plans
- Reference vs Canon conflict → Canon wins
- Judge vs deterministic invariant → Invariant wins
- Market vs Genre Constitution → Cannot silently change Genre
- Draft vs Canon → Draft never becomes Canon without CanonCommit

### 17.2 SourcePrecedence (Context Compilation)

**From context-policy.yaml**:

```yaml
authority_priority:  # (renamed to SourcePrecedence in TERMINOLOGY_BASELINE)
  - constitution
  - genre
  - canon
  - contract
  - plan
  - derived
  - reference
  - market
  - diagnostic
```

**Effect**: When Context Compiler encounters conflicting information, higher-priority sources override lower.

### 17.3 Multi-Authority Operations

Some operations require **multiple authorities** to succeed:

#### CanonCommit (Operation 6)

```yaml
required_authorities:
  - genre: PASS (Q2 hard gate)
  - canon: PASS (Q1 hard gate, parent validation)
  - contract: PASS (Q3 hard gate, bound to commit)
  - system: PASS (Q0 hard gate, integrity)
  - commit_permit: ISSUED
  - canon_commit_service: EXECUTE (only entity that can write)
```

#### Publish (Operation 11)

```yaml
required_authorities:
  - canon: COMMITTED (only committed Canon can publish)
  - production_state: PUBLISH_READY
  - human_approval: GRANTED (REQUIRED)
  - publishing_service: EXECUTE
```

#### R3 Retcon (Operation 8)

```yaml
required_authorities:
  - human_approval: GRANTED (REQUIRED)
  - canon_service: EXECUTE
  - impact_analysis: COMPLETE
  - invalidation_cascade: PREPARED
```

---

## 18. OPERATION SUMMARY TABLE

| Operation | Primary Authority | Can Trigger | Can Block | Human Required | Output Tier |
|-----------|------------------|-------------|-----------|----------------|-------------|
| **Produce Candidate** | Worker | Writer, Workflow | Missing Contract, Stale Canon | No | T6 (draft) |
| **Write Draft** | Worker | Writer, Workflow | Missing Contract, Stale Canon | No | T6 (draft) |
| **Write Plan** | Worker | Planner, Workflow | Genre, Canon contradiction | No | T4 (plan) |
| **Write Contract** | Worker | Planner, Workflow | Genre, Impossible state | No | T4 (contract) |
| **Sign Permit** | System | CanonCommit Service | Q0-Q3 failures, Policy violations | No | Gate artifact |
| **Modify Canon** | System | CanonCommit Service ONLY | Missing Permit, Parent mismatch | No (auto) | T3 (canon) |
| **Push Canon Head** | System | CanonCommit Service | N/A (automatic) | No | T3 (canon) |
| **Retcon R1** | System | Annotator | N/A | No | T3 (canon) |
| **Retcon R2** | System | Canon Service + Review | Impact analysis | No | T3 (canon) |
| **Retcon R3** | Human | Human ONLY | Missing approval | **YES** | T3 (canon) |
| **Modify Genre Hard Rule** | Human | Human, Genre Designer | Active production (warning) | **YES** | T2 (genre) |
| **Modify Policy** | Human | Human, Promotion Gate | Failed gate, Missing approval | **YES** (prod) | T1 (policy) |
| **Publish** | Human | Human, Publishing Service | Not PUBLISH_READY, Uncommitted | **YES** | External |
| **Promote Prompt/Model** | System/Human | Learning System, Promotion Gate | Failed gate, Missing approval | **YES** (prod) | T1 (policy) |

---

## 19. INVARIANT ENFORCEMENT MATRIX

### 19.1 Core Invariants (from CONSTITUTION Section 11)

| Invariant | Enforced By | Enforcement Point | Violation Consequence |
|-----------|-------------|-------------------|----------------------|
| **INV-001**: Production MUST bind GenrePack | Context Compiler, Validation | Context compilation, Q0 gate | BLOCK |
| **INV-002**: Genre Hard Violation MUST block Canon Commit | Q2 Gate | Permit signing | BLOCK commit |
| **INV-003**: Canon Commit MUST reference valid parent | Q0 Gate | Permit signing | BLOCK commit |
| **INV-004**: Canon writes ONLY through CanonCommit boundary | Architecture | Code structure, fitness tests | P0 violation |
| **INV-005**: Evaluated text hash = accepted text hash | Q0 Gate | Permit signing | BLOCK commit |
| **INV-006**: Retry/Resume MUST NOT duplicate side effects | Workflow | Idempotency check | BLOCK retry |
| **INV-007**: Reference MUST NOT write Canon directly | Reference Firewall | Architecture boundary | P0 violation |
| **INV-008**: Model MUST NOT be proposal+approver+authority | Architecture | Separation of concerns | P0 violation |
| **INV-009**: Canon rebuildable from Event Log | Canon Service | Snapshot verification | Warning (SHOULD) |
| **INV-010**: Production Run MUST have RunFingerprint | Workflow | Run initialization | BLOCK run |
| **INV-011**: Market Snapshot MUST have provenance | Market Service | Snapshot creation | BLOCK creation |
| **INV-012**: AI Eval MUST label Evidence Level | Quality Service | Report generation | Warning |
| **INV-013**: Persisted Artifact MUST have lifecycle | Artifact Service | Artifact creation | BLOCK creation |
| **INV-014**: GenrePack MUST have pollution tests | Genre Certification | M3 gate | BLOCK certification |
| **INV-015**: Unsafe bypass output MUST mark non-production | Workflow | Output tagging | BLOCK publish |

### 19.2 Policy Enforcement (canon-commit-policy.yaml)

| Policy | Default | Enforced By | Enforcement Point |
|--------|---------|-------------|-------------------|
| **missing_contract** | BLOCK | Q0 Gate | Permit signing |
| **missing_permit** | BLOCK | CanonCommit Service | Commit attempt |
| **parent_mismatch** | BLOCK | Q0 Gate | Permit signing |
| **text_hash_mismatch** | BLOCK | Q0 Gate | Permit signing |
| **hard_genre_violation** | BLOCK | Q2 Gate | Permit signing |
| **immutable_fact_mutation** | BLOCK | Q1 Gate | Permit signing |
| **unregistered_extension** | BLOCK | Q0 Gate | Permit signing |
| **continuity_hard_error** | BLOCK | Q1 Gate | Permit signing |

### 19.3 Context Policy Enforcement (context-policy.yaml)

| Policy | Severity | Enforced By | Enforcement Point |
|--------|----------|-------------|-------------------|
| **CTX-POL-001**: Mandatory items never trimmed | HARD | Context Compiler | Context assembly |
| **CTX-POL-002**: Writer raw reference forbidden | HARD | Context Compiler | Context assembly |
| **CTX-POL-003**: Project/branch isolation | HARD | Context Compiler | Context assembly |
| **CTX-POL-004**: Stale canon/contract blocks | HARD | Context Compiler | Context assembly |
| **CTX-POL-005**: Failed draft not used as canon context | HARD | Context Compiler | Context assembly |
| **CTX-POL-006**: Same-authority conflict must resolve | HARD | Context Compiler | Context assembly |

---

## 20. AUTHORITY VERIFICATION CHECKLIST

### 20.1 Architecture Fitness Tests (MUST verify)

```yaml
fitness_tests:
  - canon_write_only_through_commit_boundary: true
  - writer_cannot_import_canon_write_api: true
  - reference_cannot_import_canon_commit: true
  - single_canon_store_only: true
  - genre_can_block_commits: true
  - draft_never_auto_becomes_canon: true
  - ai_judge_no_commit_authority: true
  - contract_binds_genre_and_parent: true
  - permit_requires_all_hard_gates: true
  - human_authority_enforced_for_r3: true
```

### 20.2 Runtime Assertions (SHOULD verify)

```yaml
runtime_assertions:
  - commit_has_valid_permit: true
  - permit_binds_exact_draft_hash: true
  - parent_hash_matches_canon_head: true
  - idempotency_key_unique: true
  - genre_pack_version_bound: true
  - contract_version_bound: true
  - policy_version_bound: true
  - provenance_complete: true
```

### 20.3 Manual Review Gates (Human verification)

```yaml
manual_review_required:
  - r3_retcon_requests: human_approval
  - external_publishing: human_approval
  - major_genre_changes: human_approval
  - production_policy_deployment: human_approval
  - world_rule_changes: human_approval
  - identity_corrections: human_approval
```

---

## 21. IMPLEMENTATION PHASES

### Phase Mapping to Implementation Plan

| Authority Matrix Section | Implementation Phase | Tasks |
|--------------------------|---------------------|-------|
| **Produce Candidate** | P5 (Context), P8 (Workflow) | V2-013 to V2-015, V2-017 to V2-019 |
| **Write Plan/Contract** | P4 (Planning) | V2-011, V2-012 |
| **Sign Permit** | P3 (Canon), P6 (Quality) | V2-009, V2-020 to V2-026 |
| **Modify Canon** | P3 (Canon Transaction) | V2-009, V2-010 |
| **Retcon** | P3 (Canon) | V2-010 |
| **Genre Hard Rules** | P1 (Genre Foundation) | V2-007, V2-008 |
| **Reference Authority** | P10 (Genesis, deferred) | V2-042 to V2-044 |
| **Market Signal** | P13 (Learning, deferred) | V2-055 to V2-060 |
| **AI Judge Authority** | P6 (Quality) | V2-020 to V2-026 |
| **Human Approval** | P0 (Platform Security) | V2-003 |

---

## 22. CONCLUSION

This Authority Matrix establishes:

1. **Who can perform** each critical operation (trigger authority)
2. **Who can prevent** each operation (block authority)
3. **What must be true** for operations to proceed (gate conditions)
4. **What must be preserved** across operations (invariants)
5. **Clear boundaries** between evidence (T5-T7) and truth (T0-T3)
6. **Human authority requirements** for high-stakes operations
7. **No bypass paths** to Canon except through CanonCommit

**Key Takeaways**:

- **Canon has ONE write path** (INV-004): CanonCommit Service
- **Draft ≠ Canon** (P-003): All generation is T6 until committed
- **Genre can block** (T2 authority): Hard Rules gate commits
- **Judge cannot decide alone** (P-010): T7 is evidence, not truth
- **Reference cannot write Canon** (P-011, INV-007): T5 informs, doesn't command
- **Human approval required** for: R3, Publishing, Major Changes, Policy Deploy
- **Truth Hierarchy enforced**: Lower tiers cannot override higher tiers

**Verification**: All authority claims traceable to:
- PROJECT_CONSTITUTION.md (principles, invariants, prohibitions)
- canon-commit-policy.yaml (commit gates)
- context-policy.yaml (context rules)
- Domain specifications (operational semantics)

---

**Document Status**: NORMATIVE  
**Enforcement**: All V2 code, workflows, and operations  
**Next Update**: After architecture conflicts resolved (Task #8)  
**Verification**: Architecture fitness tests + runtime assertions + manual review gates

---

**END OF AUTHORITY MATRIX**
