# ANovel V2 Data Ownership Matrix

**Document ID**: CONV-0010  
**Version**: 1.0  
**Status**: NORMATIVE  
**Created**: 2026-09-19  
**Authority**: CONVERGENCE-BASELINE  
**Purpose**: Define ownership, lifecycle, and governance for every persistent artifact in ANovel V2

---

## 0. Matrix Governance Principles

**Core Rules**:
1. Every persistent object MUST have a defined owner
2. Every artifact MUST have at least one consumer (NO_CONSUMER = excluded from V2)
3. Authority tier (T0-T7) determines conflict resolution precedence
4. Immutability vs mutability MUST be explicit
5. Versioning strategy MUST be defined
6. Staleness and invalidation triggers MUST be specified
7. Reconstruction mechanism MUST be defined
8. Retention and deletion policies MUST comply with Constitution

**Reference Framework**:
- Truth Hierarchy: T0 (Constitution) → T7 (AI Analysis)
- Authority Boundary: Per NORMATIVE_INDEX.md Section 12
- Terminology: Per TERMINOLOGY_BASELINE.md
- Lifecycle States: CREATED → VALID → STALE → INVALID → DELETED

---

## 1. CANON ARTIFACTS (T3 - Canonical Truth)

### 1.1 Canon Event

| Dimension | Definition |
|-----------|------------|
| **Producer** | CanonCommit Service (only path to Canon) |
| **Owner** | Project Canon (T3 authority) |
| **Consumers** | Canon Snapshot builder, Context Compiler, Planner, Retcon analyzer, Quality validator (Q1) |
| **Authority** | T3 - Canonical Narrative State |
| **Mutability** | IMMUTABLE once committed (append-only log) |
| **Versioned** | YES - Canon sequence number + commit hash |
| **Staleness** | Never stale (historical fact) |
| **Invalidation** | Only via explicit Retcon (R1/R2/R3) with invalidation cascade |
| **Reconstruction** | From Canon Event Log (append-only sequence) |
| **Retention** | PERMANENT (project lifetime) |
| **Deletion** | Only on project deletion (after human approval) |
| **Provenance** | REQUIRED - parent commit hash, source artifact hash, permit ID, ChangeSet hash |

**Critical Invariant**: INV-004 - Canon writes ONLY through CanonCommit boundary

---

### 1.2 Canon Snapshot

| Dimension | Definition |
|-----------|------------|
| **Producer** | Canon Snapshot Builder (projection service) |
| **Owner** | Project Canon (T3 authority) |
| **Consumers** | Context Compiler, Planner, Contract validator, Quality gates (Q1), Retcon impact analyzer |
| **Authority** | T3 - Derived projection of Canon HEAD |
| **Mutability** | IMMUTABLE per snapshot (rebuilt on Canon HEAD change) |
| **Versioned** | YES - tied to Canon HEAD commit hash |
| **Staleness** | Becomes stale when Canon HEAD advances |
| **Invalidation** | On Canon HEAD change or Retcon |
| **Reconstruction** | Replay Canon Event Log to target commit |
| **Retention** | SHORT-TERM cache + historical snapshots at milestones (every 10 chapters, major arcs) |
| **Deletion** | Cache eviction policy (keep milestone snapshots) |
| **Provenance** | REQUIRED - Canon HEAD hash, snapshot timestamp, builder version |

---

### 1.3 CanonCommit

| Dimension | Definition |
|-----------|------------|
| **Producer** | CanonCommit Service with validated CommitPermit |
| **Owner** | Project Canon (T3 authority) |
| **Consumers** | Canon Event Log, Canon Snapshot builder, Audit system, Provenance tracker, Workflow completion |
| **Authority** | T3 - Commit transaction record |
| **Mutability** | IMMUTABLE (atomic transaction) |
| **Versioned** | YES - commit sequence + parent hash chain |
| **Staleness** | Never stale (historical transaction) |
| **Invalidation** | Only via R3 Hard Retcon (requires human authority) |
| **Reconstruction** | From CanonCommit log (append-only) |
| **Retention** | PERMANENT (project lifetime) |
| **Deletion** | Only on project deletion |
| **Provenance** | REQUIRED - parent commit, source text hash, ChangeSet hash, permit ID, actor, timestamp |

**Validation Requirements**: Q0-Q3 hard gates MUST pass before permit issued

---

### 1.4 CommitPermit

| Dimension | Definition |
|-----------|------------|
| **Producer** | Workflow validation orchestrator (Q0-Q3 gate results) |
| **Owner** | Workflow execution (T1 infrastructure) |
| **Consumers** | CanonCommit Service (gate enforcement) |
| **Authority** | T3 gate artifact - proof of validation |
| **Mutability** | IMMUTABLE once issued |
| **Versioned** | YES - tied to candidate hash + validation run |
| **Staleness** | Becomes stale if Canon HEAD advances (parent mismatch) |
| **Invalidation** | On Canon HEAD change, Contract invalidation, or timeout (e.g., 24 hours) |
| **Reconstruction** | Cannot reconstruct (must revalidate) |
| **Retention** | SHORT-TERM (until commit or timeout) |
| **Deletion** | After commit or expiration |
| **Provenance** | REQUIRED - all Q0-Q3 validation results, candidate hash, Canon parent hash, timestamp |

---

### 1.5 RetconRequest / RetconCommit

| Dimension | Definition |
|-----------|------------|
| **Producer** | Human authority (R3) or System (R1/R2 with constraints) |
| **Owner** | Project Canon (T3 authority) |
| **Consumers** | Canon invalidation cascade, Snapshot rebuilder, Planning re-validator, Audit log |
| **Authority** | T3 - Retroactive Canon mutation |
| **Mutability** | IMMUTABLE once committed |
| **Versioned** | YES - Retcon sequence + scope (R1/R2/R3) |
| **Staleness** | Never stale (historical Retcon fact) |
| **Invalidation** | Never (Retcon itself is truth record) |
| **Reconstruction** | From Retcon log |
| **Retention** | PERMANENT (audit trail) |
| **Deletion** | Only on project deletion |
| **Provenance** | REQUIRED - Retcon level, affected commits, justification, human approver (R3), invalidation cascade manifest |

**Critical Rule**: PROHIBIT-010 - Silent Retcon is forbidden

---

## 2. DOMAIN ENTITIES (T2/T3 - Genre + Canon)

### 2.1 Character

| Dimension | Definition |
|-----------|------------|
| **Producer** | NarrativeDelta Extractor → CanonCommit |
| **Owner** | Project Canon (T3 for instances), GenrePack (T2 for schema extensions) |
| **Consumers** | Context Compiler, Contract validator, Knowledge Boundary enforcer, Relationship manager, Quality evaluator (Q5) |
| **Authority** | T3 (instance data), T2 (schema extensions) |
| **Mutability** | MIXED - Identity immutable, State mutable, History append-only |
| **Versioned** | YES - via Canon commit sequence |
| **Staleness** | When Canon HEAD advances (use latest snapshot) |
| **Invalidation** | Via Retcon or lifecycle state change (DEAD, ABSENT) |
| **Reconstruction** | From Canon Event Log filtered by character_id |
| **Retention** | PERMANENT (project lifetime) |
| **Deletion** | Only on project deletion (entities never truly deleted, lifecycle=ENDED) |
| **Provenance** | REQUIRED - creation commit, last update commit, Genre schema version |

**Fact Mutability** (per NARRATIVE_DOMAIN_SPEC):
- IMMUTABLE: identity, canonical_name, entity_type, parent facts
- MUTABLE: location, occupation, beliefs, emotions, goals
- APPEND-ONLY: events, knowledge_acquired, relationships

---

### 2.2 Relationship

| Dimension | Definition |
|-----------|------------|
| **Producer** | NarrativeDelta Extractor → CanonCommit |
| **Owner** | Project Canon (T3) |
| **Consumers** | Context Compiler (character context), Contract validator, Social graph analyzer, Quality evaluator |
| **Authority** | T3 |
| **Mutability** | MIXED - Identity immutable, State mutable (relationship strength/status) |
| **Versioned** | YES - via Canon commit |
| **Staleness** | On Canon HEAD change |
| **Invalidation** | Via Retcon or entity lifecycle change |
| **Reconstruction** | From Canon Event Log relationship events |
| **Retention** | PERMANENT |
| **Deletion** | Lifecycle-based (relationship_ended=true) |
| **Provenance** | REQUIRED - establishment commit, modification commits |

---

### 2.3 Event

| Dimension | Definition |
|-----------|------------|
| **Producer** | NarrativeDelta Extractor → CanonCommit |
| **Owner** | Project Canon (T3) |
| **Consumers** | Timeline builder, Canon Snapshot, Knowledge inference, Promise/Mystery tracker, Quality validator (Q1) |
| **Authority** | T3 - Historical claim |
| **Mutability** | IMMUTABLE once committed (what happened cannot un-happen) |
| **Versioned** | YES - via Canon commit |
| **Staleness** | Never stale (historical fact) |
| **Invalidation** | Only via Retcon |
| **Reconstruction** | From Canon Event Log |
| **Retention** | PERMANENT |
| **Deletion** | Only via project deletion |
| **Provenance** | REQUIRED - commit, timestamp, participants, location, consequences |

**Critical Distinction**: Event identity vs event occurrence (AR-06 defect)

---

### 2.4 Knowledge

| Dimension | Definition |
|-----------|------------|
| **Producer** | NarrativeDelta Extractor → CanonCommit |
| **Owner** | Project Canon (T3) |
| **Consumers** | Knowledge Boundary enforcer (Context), Character context builder, Mystery revelation tracker |
| **Authority** | T3 |
| **Mutability** | APPEND-ONLY (knowledge gained, beliefs updated) |
| **Versioned** | YES - knowledge acquisition is Canon event |
| **Staleness** | On Canon HEAD change |
| **Invalidation** | Via Retcon or belief contradiction resolution |
| **Reconstruction** | From Canon Event Log knowledge events |
| **Retention** | PERMANENT |
| **Deletion** | Superseded by contradictory knowledge (both retained with timestamps) |
| **Provenance** | REQUIRED - acquisition event, source, confidence, knower scope |

**Key Principle**: P-015 - Absence of evidence ≠ evidence of absence

---

### 2.5 Promise

| Dimension | Definition |
|-----------|------------|
| **Producer** | NarrativeDelta Extractor → CanonCommit |
| **Owner** | Project Canon (T3) |
| **Consumers** | Planning Contract validator (payoff tracker), Context Compiler, Quality evaluator (Q4), Reader Promise monitor |
| **Authority** | T3 (what promises exist) + T4 (what promises should be paid off when) |
| **Mutability** | MIXED - Setup immutable, State mutable (status: OPEN/PAID/BROKEN) |
| **Versioned** | YES - setup commit + payoff commit |
| **Staleness** | On Canon HEAD change |
| **Invalidation** | Via payoff or explicit breaking (with consequences) |
| **Reconstruction** | From Canon Event Log promise lifecycle events |
| **Retention** | PERMANENT (even after payoff, for narrative analysis) |
| **Deletion** | Never (lifecycle-based state only) |
| **Provenance** | REQUIRED - setup commit, payoff commit (if paid), genre promise type |

**Critical Link**: T2 GenrePack defines canonical promise types per genre

---

### 2.6 Mystery

| Dimension | Definition |
|-----------|------------|
| **Producer** | NarrativeDelta Extractor → CanonCommit |
| **Owner** | Project Canon (T3) |
| **Consumers** | Planning Contract, Context Compiler, Knowledge Boundary (reveal control), Quality evaluator |
| **Authority** | T3 |
| **Mutability** | MIXED - Question immutable, State mutable (status: OPEN/REVEALED/ABANDONED) |
| **Versioned** | YES - question commit + revelation commit |
| **Staleness** | On Canon HEAD change |
| **Invalidation** | Via revelation or explicit abandonment |
| **Reconstruction** | From Canon Event Log mystery lifecycle events |
| **Retention** | PERMANENT |
| **Deletion** | Never |
| **Provenance** | REQUIRED - question commit, revelation commit (if revealed), foreshadowing trail |

---

## 3. GENRE ARTIFACTS (T2 - Genre Constitution)

### 3.1 GenrePack

| Dimension | Definition |
|-----------|------------|
| **Producer** | Genre Designer + Genre Certification System |
| **Owner** | Platform (T2 authority) |
| **Consumers** | Project binding (Genesis), Canon validator (Q2), Context Compiler, Planning constraints, Reality Model enforcer |
| **Authority** | T2 - Genre Constitution |
| **Mutability** | IMMUTABLE per version (versioned releases) |
| **Versioned** | YES - semantic versioning (MAJOR.MINOR.PATCH) |
| **Staleness** | When newer certified version available (project can stay on pinned version) |
| **Invalidation** | Via decertification (critical defect found) |
| **Reconstruction** | From Genre Pack registry + certification record |
| **Retention** | LONG-TERM (all certified versions, deprecated versions for 2 major releases) |
| **Deletion** | After deprecation grace period + no active projects using it |
| **Provenance** | REQUIRED - certification milestone (M3), certification test results, author, release date |

**Critical Rule**: GenrePack can BLOCK CanonCommit if Hard Rule violated

---

### 3.2 Genre Hard Rule

| Dimension | Definition |
|-----------|------------|
| **Producer** | Genre Designer (embedded in GenrePack) |
| **Owner** | GenrePack (T2 authority) |
| **Consumers** | Canon validator (Q2 gate), NarrativeDelta validator, Reality Model enforcer |
| **Authority** | T2 - Can block Canon writes |
| **Mutability** | IMMUTABLE per GenrePack version (new version = new rules) |
| **Versioned** | YES - via GenrePack version |
| **Staleness** | When GenrePack updated (project binds to specific version) |
| **Invalidation** | Via GenrePack version supersession |
| **Reconstruction** | From GenrePack artifact |
| **Retention** | LONG-TERM (lifetime of GenrePack version) |
| **Deletion** | With GenrePack deletion |
| **Provenance** | REQUIRED - GenrePack version, rule rationale, certification validation |

---

### 3.3 Canon Extension Schema (Genre-specific)

| Dimension | Definition |
|-----------|------------|
| **Producer** | Genre Designer (embedded in GenrePack) |
| **Owner** | GenrePack (T2 schema) + Project Canon (T3 instance data) |
| **Consumers** | Canon entity builder, Domain type system, Context Compiler, Quality validator |
| **Authority** | T2 (schema definition), T3 (instance values) |
| **Mutability** | Schema immutable per GenrePack version, instance data per entity mutability |
| **Versioned** | YES - via GenrePack version |
| **Staleness** | Schema never stale (bound at project creation), instance data on Canon change |
| **Invalidation** | Schema on GenrePack decertification, instance data via Retcon |
| **Reconstruction** | Schema from GenrePack, instance data from Canon Event Log |
| **Retention** | Schema: GenrePack lifetime, Instance: PERMANENT |
| **Deletion** | Schema with GenrePack, instance with project |
| **Provenance** | REQUIRED - GenrePack version, namespace (AR-08 collision risk mitigation) |

**Known Risk**: AR-08 - Canon extension namespace collision between GenrePacks

---

### 3.4 MarketTrendSnapshot

| Dimension | Definition |
|-----------|------------|
| **Producer** | Market Intelligence Collector |
| **Owner** | Platform (T5 evidence provider) |
| **Consumers** | Genesis candidate ranker, Planner (optional market signal), Learning system (calibration) |
| **Authority** | T5 - Market Evidence (NEVER writes Canon or Genre directly) |
| **Mutability** | IMMUTABLE per snapshot (time-bound observation) |
| **Versioned** | YES - timestamp + data source version |
| **Staleness** | Time-based (e.g., 30 days for platform trends) |
| **Invalidation** | On expiration or data source retraction |
| **Reconstruction** | Cannot reconstruct (historical market data) |
| **Retention** | MEDIUM-TERM (e.g., 2 years for trend analysis) |
| **Deletion** | After retention period |
| **Provenance** | REQUIRED - collection timestamp, platform source, sampling methodology, confidence bounds |

**Critical Rule**: P-009 - Market trend CANNOT silently modify Genre Constitution

---

## 4. PLANNING ARTIFACTS (T4 - Future Intentions)

### 4.1 SeriesVision

| Dimension | Definition |
|-----------|------------|
| **Producer** | Genesis process or Human planner |
| **Owner** | Project (T4 authority) |
| **Consumers** | ArcPlan generator, Planner (long-term direction), Context Compiler (optional), Fatigue analyzer |
| **Authority** | T4 - Series-level intention |
| **Mutability** | MUTABLE (replaceable as vision evolves) |
| **Versioned** | YES - vision version + effective from chapter N |
| **Staleness** | When major Canon divergence detected or explicit revision |
| **Invalidation** | Via explicit revision or Canon conflict (Canon wins, vision re-plans) |
| **Reconstruction** | From vision history log |
| **Retention** | LONG-TERM (all versions for project lifetime) |
| **Deletion** | Only on project deletion |
| **Provenance** | REQUIRED - Genesis source or revision trigger, Canon state at creation, author (human/AI) |

**Conflict Rule**: Plan vs Canon → Canon wins, Plan re-plans (P-017)

---

### 4.2 ArcPlan

| Dimension | Definition |
|-----------|------------|
| **Producer** | Planner Worker (from SeriesVision + Canon state) |
| **Owner** | Project (T4 authority) |
| **Consumers** | ChapterContract generator, Context Compiler, Fatigue monitor, Progress tracker |
| **Authority** | T4 - Arc-level intention |
| **Mutability** | MUTABLE (rolling replan) |
| **Versioned** | YES - plan version + effective range (chapters N-M) |
| **Staleness** | When Canon diverges from plan or rolling horizon advances |
| **Invalidation** | Via rolling replan or Canon conflict |
| **Reconstruction** | From plan history |
| **Retention** | MEDIUM-TERM (completed arcs retained for 1 year after completion) |
| **Deletion** | After retention period |
| **Provenance** | REQUIRED - SeriesVision version, Canon HEAD at planning, planner policy version |

---

### 4.3 ChapterContract

| Dimension | Definition |
|-----------|------------|
| **Producer** | Contract Compiler (from ArcPlan + Canon state + GenrePack) |
| **Owner** | Workflow execution (T4 binding) |
| **Consumers** | Workflow stage gate, Context Compiler (Writer/Reviewer), Contract validator (Q3), CommitPermit generator |
| **Authority** | T4 - Chapter semantic requirements |
| **Mutability** | IMMUTABLE once frozen for production run (versioned if revised) |
| **Versioned** | YES - contract version + Canon parent hash |
| **Staleness** | When Canon parent becomes obsolete (HEAD advanced by other commit) |
| **Invalidation** | On Canon parent mismatch or explicit contract revision |
| **Reconstruction** | Cannot reconstruct (must recompile from plan + Canon) |
| **Retention** | MEDIUM-TERM (active contracts + completed contracts for 6 months) |
| **Deletion** | After retention period |
| **Provenance** | REQUIRED - ArcPlan version, Canon parent hash, GenrePack version, required/forbidden transitions |

**Critical Rule**: Contract missing = production BLOCKED

---

### 4.4 SceneContract

| Dimension | Definition |
|-----------|------------|
| **Producer** | Contract Compiler (from ChapterPlan) |
| **Owner** | Workflow execution (T4 binding) |
| **Consumers** | Scene Writer context, Contract validator, CommitPermit generator |
| **Authority** | T4 - Scene-level semantic commitments |
| **Mutability** | IMMUTABLE once frozen for scene production |
| **Versioned** | YES - tied to ChapterContract version |
| **Staleness** | When parent ChapterContract invalidated |
| **Invalidation** | On ChapterContract invalidation or Canon parent mismatch |
| **Reconstruction** | From ChapterContract decomposition |
| **Retention** | SHORT-TERM (until chapter committed + 30 days) |
| **Deletion** | After retention period |
| **Provenance** | REQUIRED - ChapterContract hash, scene order, required transitions |

---

## 5. CONTEXT ARTIFACTS (T5 - Compiled Context)

### 5.1 ContextArtifact

| Dimension | Definition |
|-----------|------------|
| **Producer** | Context Compiler |
| **Owner** | Workflow execution (T5 artifact) |
| **Consumers** | Worker (Writer/Planner/Reviewer/Repairer), Provenance tracker, Reproducibility audit |
| **Authority** | T5 - Compiled context package (NOT Canon) |
| **Mutability** | IMMUTABLE once issued (content-addressed) |
| **Versioned** | YES - context hash (content-addressed) |
| **Staleness** | When bound Canon HEAD or Contract invalidated |
| **Invalidation** | On Canon HEAD change or Contract invalidation |
| **Reconstruction** | Can reconstruct if all source artifacts still valid (Canon HEAD, Contract, GenrePack versions match) |
| **Retention** | SHORT-TERM (until Worker completes + provenance retention period, e.g., 90 days) |
| **Deletion** | After retention period (keep provenance metadata) |
| **Provenance** | REQUIRED - Canon HEAD hash, Contract hash, GenrePack version, selection policy version, task role |

**Critical Rule**: ContextArtifact DOES NOT become Canon

---

### 5.2 ModelPolicy

| Dimension | Definition |
|-----------|------------|
| **Producer** | Platform configuration or Learning promotion |
| **Owner** | Platform (T1 configuration) |
| **Consumers** | Model Gateway, Context Compiler, Cost estimator, Workflow retry logic |
| **Authority** | T1 - Infrastructure configuration |
| **Mutability** | IMMUTABLE per version (versioned policy) |
| **Versioned** | YES - policy version + effective date |
| **Staleness** | When superseded by promoted policy |
| **Invalidation** | Via policy promotion or deprecation |
| **Reconstruction** | From policy registry |
| **Retention** | LONG-TERM (all versions for audit, deprecated policies for 1 year) |
| **Deletion** | After deprecation grace period |
| **Provenance** | REQUIRED - promotion experiment ID (if from Learning), approval authority, rollback criteria |

---

## 6. WORKFLOW ARTIFACTS (T1 - Production Execution)

### 6.1 WorkflowRun

| Dimension | Definition |
|-----------|------------|
| **Producer** | Workflow Orchestrator |
| **Owner** | Workflow execution (T1 infrastructure) |
| **Consumers** | Stage executor, Checkpoint system, Cost tracker, Observability, Audit log |
| **Authority** | T1 - Execution state (NOT Canon state) |
| **Mutability** | MUTABLE (status updates during execution) |
| **Versioned** | YES - run_id + workflow version |
| **Staleness** | Never stale (historical execution record) |
| **Invalidation** | Never (execution history is fact) |
| **Reconstruction** | From execution log + checkpoints |
| **Retention** | LONG-TERM (all runs for project lifetime, detailed logs for 1 year) |
| **Deletion** | Summarize after 1 year (keep metadata, delete detailed stage logs) |
| **Provenance** | REQUIRED - RunFingerprint (constitution version, code commit, Canon parent, Contract hash, policy versions) |

**Critical Rule**: WF-POL-002 - Workflow state ≠ Canon state

---

### 6.2 Checkpoint

| Dimension | Definition |
|-----------|------------|
| **Producer** | Workflow stage completion |
| **Owner** | WorkflowRun (T1 infrastructure) |
| **Consumers** | Workflow resume logic, Idempotency checker, Cost deduplication |
| **Authority** | T1 - Resumption point |
| **Mutability** | IMMUTABLE per checkpoint |
| **Versioned** | YES - checkpoint sequence in run |
| **Staleness** | When WorkflowRun completes or fails terminally |
| **Invalidation** | On WorkflowRun cancellation or bound artifacts invalidated (Canon HEAD changed) |
| **Reconstruction** | Cannot reconstruct (must replay from prior checkpoint) |
| **Retention** | SHORT-TERM (until run completes + 7 days) |
| **Deletion** | After run completion + retention period |
| **Provenance** | REQUIRED - stage name, artifact hashes produced, timestamp, idempotency key |

---

### 6.3 RunFingerprint

| Dimension | Definition |
|-----------|------------|
| **Producer** | Workflow initialization |
| **Owner** | WorkflowRun (T1 provenance) |
| **Consumers** | Reproducibility audit, Regression analysis, Experiment comparison, Incident investigation |
| **Authority** | T1 - Production conditions snapshot |
| **Mutability** | IMMUTABLE |
| **Versioned** | YES - tied to WorkflowRun |
| **Staleness** | Never stale (historical fingerprint) |
| **Invalidation** | Never |
| **Reconstruction** | Cannot reconstruct (must be captured at run start) |
| **Retention** | LONG-TERM (project lifetime for audit) |
| **Deletion** | Only on project deletion |
| **Provenance** | REQUIRED - all versioned inputs (constitution, code, schemas, policies, Canon parent, GenrePack) |

---

## 7. QUALITY ARTIFACTS (T7 - AI Analysis / E1-E4 Evidence)

### 7.1 QualityReport

| Dimension | Definition |
|-----------|------------|
| **Producer** | Quality Evaluator (Reviewer Worker) |
| **Owner** | Workflow execution (T7 evidence) |
| **Consumers** | CommitPermit generator (Q0-Q3 gates), RepairPlan generator, Human reviewer, Learning calibration |
| **Authority** | T7 - Evaluation evidence (NOT truth, NOT Canon authority) |
| **Mutability** | IMMUTABLE per evaluation run |
| **Versioned** | YES - tied to candidate hash + reviewer policy version |
| **Staleness** | When candidate revised or quality policy updated |
| **Invalidation** | On candidate invalidation |
| **Reconstruction** | Can rerun evaluation (but may differ if non-deterministic) |
| **Retention** | MEDIUM-TERM (committed chapters: 1 year, rejected candidates: 90 days) |
| **Deletion** | After retention period |
| **Provenance** | REQUIRED - candidate hash, context hash, quality policy version, confidence level (E1-E4) |

**Critical Rule**: P-010 - AI Judge is not ground truth

---

### 7.2 RepairPlan

| Dimension | Definition |
|-----------|------------|
| **Producer** | Repair Worker (from QualityReport) |
| **Owner** | Workflow execution (T7 proposal) |
| **Consumers** | Repair executor (Patch/Rewrite generator), Human reviewer (optional approval) |
| **Authority** | T7 - Repair proposal (NOT executed repair) |
| **Mutability** | IMMUTABLE per repair plan |
| **Versioned** | YES - tied to QualityReport hash |
| **Staleness** | When QualityReport invalidated or candidate revised |
| **Invalidation** | On source QualityReport invalidation |
| **Reconstruction** | Can regenerate (may differ) |
| **Retention** | SHORT-TERM (until repair executed + 30 days) |
| **Deletion** | After retention period |
| **Provenance** | REQUIRED - QualityReport hash, repair strategy (patch/rewrite), protected facts list |

---

### 7.3 Golden Set Item

| Dimension | Definition |
|-----------|------------|
| **Producer** | Human curator or Learning system (with human validation) |
| **Owner** | Platform (T5 calibration asset) |
| **Consumers** | Quality calibration, Experiment baseline, Regression test suite |
| **Authority** | T5 - Human truth reference (E4 evidence level) |
| **Mutability** | IMMUTABLE once curated (versioned if revised) |
| **Versioned** | YES - golden set version |
| **Staleness** | When evaluation criteria evolve (periodic review, e.g., yearly) |
| **Invalidation** | Via explicit deprecation (defect found in gold label) |
| **Reconstruction** | Cannot reconstruct (human curation required) |
| **Retention** | PERMANENT (first-class product asset) |
| **Deletion** | Never (deprecate but retain for historical analysis) |
| **Provenance** | REQUIRED - curator identity, curation date, evaluation rubric version, blind review protocol |

---

## 8. GENESIS ARTIFACTS (T4/T5/T6 - Story Birth)

### 8.1 GenesisSpec

| Dimension | Definition |
|-----------|------------|
| **Producer** | Genesis Compiler (from Genesis Tournament winner) |
| **Owner** | Project (T4 foundation) |
| **Consumers** | SeriesVision builder, Initial Canon (via GenesisCommit), GenrePack binding, Planning seed |
| **Authority** | T4 - Project foundation specification |
| **Mutability** | IMMUTABLE once accepted (project locked to Genesis) |
| **Versioned** | YES - GenesisSpec version (only one per project) |
| **Staleness** | Never stale (historical project origin) |
| **Invalidation** | Never (project origin is fixed) |
| **Reconstruction** | Cannot reconstruct (Genesis Tournament required) |
| **Retention** | PERMANENT (project lifetime) |
| **Deletion** | Only on project deletion |
| **Provenance** | REQUIRED - Genesis mode (IDEA/REFERENCE/HYBRID/CORPUS), tournament results, originality report hash, GenrePack binding |

**Critical Output**: Single accepted GenesisSpec per project (no forking after acceptance)

---

### 8.2 ReferencePack (formerly ReferenceEvidencePack)

| Dimension | Definition |
|-----------|------------|
| **Producer** | Reference Intelligence Extractor |
| **Owner** | Platform or Project (T5 evidence) |
| **Consumers** | Genesis candidate generator (mechanism learning), Planner (optional), Learning system |
| **Authority** | T5 - Reference Evidence (NEVER writes Canon directly) |
| **Mutability** | IMMUTABLE per pack version |
| **Versioned** | YES - pack version + source work hash |
| **Staleness** | Never stale (reference material is historical) |
| **Invalidation** | On copyright/rights issue or extraction defect |
| **Reconstruction** | Can re-extract from source work (may differ with updated extraction policy) |
| **Retention** | LONG-TERM (while project active + 1 year, or corpus lifetime) |
| **Deletion** | On rights expiration or explicit removal |
| **Provenance** | REQUIRED - source work identity, extraction policy version, rights metadata, negative/positive/dimension classification |

**Critical Rule**: P-011 + INV-007 - Reference cannot write Canon directly, PROHIBIT-008 - Reference text excluded from Writer context by default

---

### 8.3 OriginalityReport

| Dimension | Definition |
|-----------|------------|
| **Producer** | Originality Guard (pre-Genesis acceptance) |
| **Owner** | Project (T5 evidence) |
| **Consumers** | Genesis acceptance gate, Human reviewer, Copyright compliance audit |
| **Authority** | T5 - Originality evidence |
| **Mutability** | IMMUTABLE per Genesis candidate |
| **Versioned** | YES - tied to Genesis candidate hash |
| **Staleness** | Only for rejected candidates |
| **Invalidation** | Never (originality check is historical record) |
| **Reconstruction** | Can rerun (but should match original) |
| **Retention** | PERMANENT (copyright defense) |
| **Deletion** | Never (legal/audit requirement) |
| **Provenance** | REQUIRED - candidate hash, reference sources checked, similarity scores, manual review notes |

---

## 9. LEARNING ARTIFACTS (T5/T7 - System Improvement)

### 9.1 Experiment

| Dimension | Definition |
|-----------|------------|
| **Producer** | Learning system or human experimenter |
| **Owner** | Platform (T1 learning infrastructure) |
| **Consumers** | Experiment runner, Baseline comparator, Promotion gate, Learning dashboard |
| **Authority** | T1 - Experiment definition (NOT policy authority until promoted) |
| **Mutability** | IMMUTABLE once started (cannot modify running experiment) |
| **Versioned** | YES - experiment ID + version |
| **Staleness** | Never stale (historical experiment) |
| **Invalidation** | Never (even failed experiments retained for negative evidence) |
| **Reconstruction** | Cannot reconstruct (must rerun experiment, may differ due to non-determinism) |
| **Retention** | PERMANENT (first-class learning asset, including failures) |
| **Deletion** | Never (P-018 - preserve negative evidence) |
| **Provenance** | REQUIRED - hypothesis, baseline policy, variant policy, sample set, promotion criteria, results |

**Critical Rule**: Baseline and variant MUST be compared on same eligible sample set

---

### 9.2 Baseline

| Dimension | Definition |
|-----------|------------|
| **Producer** | Learning system (from current production policy) |
| **Owner** | Platform (T1 learning infrastructure) |
| **Consumers** | Experiment comparator, Regression detector, Promotion gate |
| **Authority** | T1 - Reference policy/model performance |
| **Mutability** | IMMUTABLE per baseline snapshot |
| **Versioned** | YES - baseline version + effective date |
| **Staleness** | When production policy promoted (new baseline) |
| **Invalidation** | Never (historical baseline retained) |
| **Reconstruction** | Cannot reconstruct (must capture at time) |
| **Retention** | PERMANENT (all baselines for trend analysis) |
| **Deletion** | Never |
| **Provenance** | REQUIRED - policy snapshot, benchmark results, captured date |

---

### 9.3 CorpusRegistry Entry

| Dimension | Definition |
|-----------|------------|
| **Producer** | Corpus ingestion system + human curator |
| **Owner** | Platform (T5 corpus governance) |
| **Consumers** | Learning experiments, Genesis research, Genre inference, Market analysis |
| **Authority** | T5 - Corpus governance |
| **Mutability** | Metadata mutable (e.g., tags, classification), content immutable |
| **Versioned** | YES - corpus item version + ingestion date |
| **Staleness** | Never stale (corpus is historical data) |
| **Invalidation** | On rights revocation or quality defect (contamination detected) |
| **Reconstruction** | Cannot reconstruct (original source required) |
| **Retention** | LONG-TERM (varies by corpus purpose: research corpus permanent, market sample corpus 2 years) |
| **Deletion** | On rights expiration, privacy request, or governance violation |
| **Provenance** | REQUIRED - source platform, author (if known), ingestion date, rights metadata, privacy classification, train/test/holdout designation |

**Critical Rule**: Corpus contamination, data leakage, benchmark leakage are hard governance failures

---

## 10. PLATFORM ARTIFACTS (T1 - Infrastructure)

### 10.1 Audit Log Entry

| Dimension | Definition |
|-----------|------------|
| **Producer** | Platform audit service (automated) |
| **Owner** | Platform (security/compliance) |
| **Consumers** | Security audit, Incident investigation, Compliance reporting, Forensic analysis |
| **Authority** | T1 - Operational truth (what system actions occurred) |
| **Mutability** | IMMUTABLE (append-only, tamper-evident) |
| **Versioned** | YES - log sequence number + timestamp |
| **Staleness** | Never stale (historical operational fact) |
| **Invalidation** | Never |
| **Reconstruction** | Cannot reconstruct (must capture in real-time) |
| **Retention** | PERMANENT for privileged actions (CANON_COMMIT, RETCON, PUBLISH), 1 year for routine actions |
| **Deletion** | After retention period (routine logs only, privileged logs never deleted) |
| **Provenance** | REQUIRED - actor, action, resource, timestamp, outcome, IP/context |

**Critical Actions Logged**: CANON_COMMIT, RETCON_APPROVE, GENRE_HARD_RULE_CHANGE, POLICY_PROMOTION, PUBLISH_EXTERNAL, SECRET_ROTATION, CORPUS_EXPORT, DATA_DELETE

---

### 10.2 Secrets

| Dimension | Definition |
|-----------|------------|
| **Producer** | Secret management system or human admin |
| **Owner** | Platform security (highest privilege) |
| **Consumers** | Model Gateway (API keys), External connectors, Backup system |
| **Authority** | T1 - Security infrastructure |
| **Mutability** | MUTABLE (rotation required) |
| **Versioned** | YES - secret version (rotation history) |
| **Staleness** | Time-based rotation policy (e.g., 90 days) or on compromise |
| **Invalidation** | On rotation or compromise |
| **Reconstruction** | Cannot reconstruct (must generate new) |
| **Retention** | ZERO (secrets never logged, rotated secrets immediately destroyed) |
| **Deletion** | Immediate (after rotation, old secret destroyed) |
| **Provenance** | REQUIRED - rotation history metadata only (NOT secret values), rotation trigger |

**Critical Rule**: Secrets NEVER enter source, artifacts, prompts, logs, or corpus (Constitution Section 21)

---

## 11. DRAFT ARTIFACTS (T6 - Proposals, NOT Truth)

### 11.1 Draft Text

| Dimension | Definition |
|-----------|------------|
| **Producer** | Writer Worker |
| **Owner** | Workflow execution (T6 proposal) |
| **Consumers** | NarrativeDelta Extractor, Quality Evaluator, Repair Worker, Human reviewer |
| **Authority** | T6 - Generated proposal (NOT Canon until committed) |
| **Mutability** | IMMUTABLE per draft hash (new repair = new draft) |
| **Versioned** | YES - draft hash (content-addressed) |
| **Staleness** | On quality failure or repair generation |
| **Invalidation** | On rejection or supersession by repair |
| **Reconstruction** | Can regenerate (will differ, not reproducible) |
| **Retention** | SHORT-TERM (committed drafts: 1 year, rejected drafts: 30 days) |
| **Deletion** | After retention period |
| **Provenance** | REQUIRED - context hash, contract hash, writer policy version, generation timestamp |

**Critical Rule**: P-003 + PROHIBIT-003 - Draft is NOT Canon, never auto-becomes Canon

---

### 11.2 NarrativeDelta

| Dimension | Definition |
|-----------|------------|
| **Producer** | Extractor Worker (from Draft text) |
| **Owner** | Workflow execution (T6 proposal) |
| **Consumers** | ChangeSet builder, Contract validator (Q3), Canon validator (Q1), Quality evaluator |
| **Authority** | T6 - Extracted proposal (NOT truth) |
| **Mutability** | IMMUTABLE per draft hash |
| **Versioned** | YES - tied to draft hash |
| **Staleness** | On draft invalidation |
| **Invalidation** | On draft rejection or repair |
| **Reconstruction** | Can re-extract (may differ with updated extraction policy) |
| **Retention** | SHORT-TERM (same as draft) |
| **Deletion** | After retention period |
| **Provenance** | REQUIRED - draft hash, extractor policy version, extraction confidence |

**Critical Rule**: NarrativeDelta is proposal, not truth (Constitution Section 0)

---

### 11.3 ChangeSet

| Dimension | Definition |
|-----------|------------|
| **Producer** | ChangeSet Builder (from validated NarrativeDelta) |
| **Owner** | Workflow execution (T6→T3 transition artifact) |
| **Consumers** | CommitPermit generator (validation input), CanonCommit service (commit payload) |
| **Authority** | T6 - Validated proposal ready for commit |
| **Mutability** | IMMUTABLE per ChangeSet hash |
| **Versioned** | YES - ChangeSet hash (content-addressed) |
| **Staleness** | On Canon parent change or validation expiration |
| **Invalidation** | On Canon HEAD advance (parent mismatch) or permit timeout |
| **Reconstruction** | Cannot reconstruct (must revalidate) |
| **Retention** | SHORT-TERM (until commit + 7 days) |
| **Deletion** | After retention period |
| **Provenance** | REQUIRED - NarrativeDelta hash, Canon parent hash, validation results (Q0-Q3), timestamp |

---

## 12. NO_CONSUMER ARTIFACTS (EXCLUDED FROM V2)

**Principle**: Per V1 Lesson LESSON-V1-XXX - "No consumer = stub, exclude from V2"

### Artifacts with NO_CONSUMER = Design Smell

After analyzing all specifications, the following artifact patterns appear to have insufficient consumers or unclear usage:

1. **StoryBible** (V1 concept) - EXCLUDED
   - Superseded by Canon Snapshot + Context Compiler
   - Consumers: None (ambiguous format, unclear authority)

2. **ProductionState** (if separate from Canon) - EXCLUDED  
   - WF-POL-002: Workflow state ≠ Canon state
   - If ProductionState duplicates Canon: EXCLUDED
   - If ProductionState = Workflow status: RETAINED as WorkflowRun status

3. **Generic "Context" without Artifact** - EXCLUDED
   - All context MUST be ContextArtifact (versioned, hashed)
   - Ad-hoc context assembly: PROHIBITED

4. **Unnamed "Memory" or "Agent State"** - EXCLUDED
   - P-007: Agents are Workers, not architecture
   - Any persistent "agent memory" must be Canon or Context, not separate truth

### Validation

All artifacts in Sections 1-11 have defined consumers. Any artifact without consumers in implementation phase MUST be reviewed for exclusion.

---

## 13. CROSS-CUTTING LIFECYCLE RULES

### 13.1 Provenance Requirements (All Persistent Artifacts)

Per Constitution P-012 + PLATFORM spec Section 4:

**REQUIRED provenance metadata**:
- Producer identity + version
- Creation timestamp
- Parent artifact hashes (for derived artifacts)
- Authority level (T0-T7)
- Content hash (for immutable artifacts)

**Audit trail for high-privilege artifacts**:
- Canon artifacts (T3)
- GenrePack (T2)
- Privileged actions (CanonCommit, Retcon, Policy Promotion)

---

### 13.2 Retention Policy Classes

| Class | Duration | Examples |
|-------|----------|----------|
| **PERMANENT** | Project lifetime + archive | Canon artifacts, GenesisSpec, GenrePack, Experiment results, Audit logs (privileged) |
| **LONG-TERM** | 1-2 years | WorkflowRun metadata, QualityReport (committed), Corpus items, RunFingerprint |
| **MEDIUM-TERM** | 3-12 months | ArcPlan (completed), ChapterContract (committed), ReferencePack (project active) |
| **SHORT-TERM** | 7-90 days | ContextArtifact, Checkpoint, Draft (rejected), RepairPlan |
| **EPHEMERAL** | Session/Run only | In-memory Worker state, temporary computation |
| **ZERO** | Never retained | Secrets (values), PII (where minimized) |

---

### 13.3 Deletion Policy

**NEVER delete**:
- Canon artifacts (only via project deletion)
- GenrePack (certified versions)
- Experiment results (including failures)
- Audit logs (privileged actions)
- Golden Set
- OriginalityReport

**Time-based deletion** (after retention):
- Workflow logs (detailed)
- Context artifacts
- Draft artifacts (rejected)
- Checkpoints

**Event-based deletion**:
- Secrets (on rotation)
- Stale permits (on expiration)
- Invalidated contracts (on Canon mismatch)

**Governance-triggered deletion**:
- Corpus items (rights expiration, privacy request)
- GenrePack (decertification + no dependencies)

---

### 13.4 Staleness Detection

| Artifact | Staleness Trigger | Detection Method |
|----------|------------------|------------------|
| Canon Snapshot | Canon HEAD advances | Compare snapshot Canon hash vs current HEAD |
| Contract | Canon parent changes | Compare contract parent hash vs current HEAD |
| ContextArtifact | Canon or Contract invalidated | Check bound artifact hashes |
| CommitPermit | Canon HEAD advances or timeout | Check parent hash + timestamp |
| Plan | Canon divergence | Contract validation failure rate |
| MarketTrendSnapshot | Time-based | Timestamp expiration (e.g., 30 days) |
| ModelPolicy | Supersession | Policy version comparison |

---

### 13.5 Reconstruction Capability

| Capability | Artifacts | Method |
|------------|-----------|--------|
| **Full reconstruction** | Canon Snapshot, Character state, Event history | Replay Canon Event Log |
| **Conditional reconstruction** | ContextArtifact, NarrativeDelta | Rebuild if source artifacts unchanged |
| **Cannot reconstruct** | Checkpoint, CommitPermit, Human curation, Secrets | Must regenerate or re-execute |
| **Reproducibility** | Experiment, WorkflowRun | RunFingerprint enables audit, not exact replay (non-deterministic LLMs) |

---

## 14. AUTHORITY CONFLICT RESOLUTION

When artifacts conflict, resolve by Truth Hierarchy (T0-T7):

```
T0 Constitution       > ALL
T1 Normative Specs    > T2-T7
T2 GenrePack          > T3-T7 (for Genre rules)
T3 Canon              > T4-T7 (for story facts)
T4 Contract/Plan      > T5-T7 (for intentions)
T5 Evidence           > T6-T7 (for reference/market)
T6 Draft/Proposal     > T7 only
T7 AI Analysis        > NONE (evidence only)
```

**Key Conflicts**:
- **Plan (T4) vs Canon (T3)**: Canon wins, Plan re-plans
- **Reference (T5) vs Canon (T3)**: Canon wins, Reference is input only
- **Judge (T7) vs Genre Rule (T2)**: Genre Rule wins (hard gate)
- **Market (T5) vs Genre Constitution (T2)**: Cannot silently change Genre
- **Draft (T6) vs Canon (T3)**: Draft never auto-becomes Canon

---

## 15. ARCHITECTURE FITNESS VALIDATION

### 15.1 Invariant Checks

**INV-004 verification**: No code bypasses CanonCommit boundary
- Check: All Canon writes go through CanonCommitService
- Check: Writer imports exclude Canon write API

**P-003 verification**: Draft ≠ Canon
- Check: No auto-promotion from Draft to Canon
- Check: CommitPermit always required

**P-010 verification**: AI Judge not ground truth
- Check: QualityReport cannot trigger CanonCommit alone
- Check: Q0-Q3 gates + Permit required

---

### 15.2 Consumer Validation

For each artifact in Sections 1-11:
- MUST have at least one defined consumer
- Consumer MUST be implemented (not stub)
- Consumer usage MUST be tested

**Exclusion trigger**: If consumer count = 0 after implementation → flag for removal

---

## 16. SUMMARY: CRITICAL OWNERSHIP DECISIONS

### Artifacts with PERMANENT retention (19 artifact types):
1. Canon Event, CanonCommit, Retcon records
2. Character, Relationship, Event, Knowledge, Promise, Mystery (entity lifecycle, not deletion)
3. GenrePack (certified versions)
4. GenesisSpec, OriginalityReport
5. Experiment results, Baseline snapshots
6. Golden Set
7. Audit logs (privileged actions)
8. RunFingerprint
9. SeriesVision, ArcPlan (all versions)

### Artifacts that NEVER become Canon (T6/T7):
1. Draft Text
2. NarrativeDelta (proposal)
3. QualityReport
4. RepairPlan
5. ContextArtifact
6. ReferencePack (evidence only)
7. MarketTrendSnapshot (evidence only)

### Single-path-to-Canon artifacts:
1. CanonCommit (via CommitPermit gate)
2. All Canon writes MUST go through CanonCommitService (INV-004)

### Human-authority-required artifacts:
1. R3 Hard Retcon
2. GenrePack certification approval
3. Golden Set curation
4. Policy promotion (major changes)
5. Project deletion

---

## 17. IMPLEMENTATION GATES

**P0 (V2-001, V2-002)**: Constitution + Terminology + Normative Index + **THIS MATRIX**  
**P2 (V2-005, V2-006)**: Domain entity schemas MUST match this matrix  
**P3 (V2-009, V2-010)**: Canon transaction MUST enforce ownership rules  
**P4 (V2-011, V2-012)**: Planning artifacts MUST respect authority boundaries  
**P5 (V2-013, V2-014, V2-015)**: Context artifacts MUST be versioned and hashed  
**P6 (V2-020-V2-026)**: Quality artifacts MUST NOT have Canon write authority  
**P8 (V2-017, V2-018, V2-019)**: Workflow artifacts MUST separate from Canon state  
**All Phases**: Architecture fitness tests MUST validate ownership boundaries

---

**Document Status**: NORMATIVE  
**Next Update**: After implementation defects found or new artifact types added  
**Maintenance**: Update when specifications evolve or retention policies change

---

**END OF DATA OWNERSHIP MATRIX**
