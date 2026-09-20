# ANovel V2 Terminology Baseline

**Document ID**: CONV-0003  
**Version**: 1.0  
**Status**: NORMATIVE  
**Created**: 2026-09-19  
**Authority**: CONVERGENCE-BASELINE  
**Purpose**: Establish unified terminology for ANovel V2, resolving conflicts across all specifications

---

## 0. Terminology Governance

**Rule**: No term may have multiple incompatible meanings within V2 specifications.

**When conflicts exist**:
1. Identify all uses across specifications
2. Choose primary meaning (based on frequency, architectural centrality, Constitution usage)
3. Rename secondary uses to distinct terms
4. Update all specifications to use unified terminology

**Authority**: This baseline supersedes conflicting terminology in any T1-T7 document.

---

## 1. CRITICAL CONFLICTS RESOLVED

### 1.1 "Evidence" — Multi-Meaning Conflict [CRITICAL]

**Problem**: Same root term with three completely different meanings across specs (identified in gptdoc cross-reference analysis as AR-02).

**Conflict Details**:

| Spec | Original Term | Meaning | Domain |
|------|---------------|---------|--------|
| QUALITY_EVALUATION_REPAIR | Evidence Level (E1-E4) | Confidence in quality evaluation | Quality certainty scale |
| MULTI_SOURCE_GENESIS | Evidence Pack | Reference material from source novels | Input provenance |
| CORPUS_EVALUATION_LEARNING | Evidence | Experimental results proving improvements | Scientific validation |

**RESOLUTION**:

| Context | **UNIFIED TERM** | Definition | Specs Affected |
|---------|------------------|------------|----------------|
| Quality evaluation confidence | **`ConfidenceLevel`** or **`QualityEvidence`** | E1=deterministic, E2=semantic, E3=simulated, E4=real reader | QUALITY_EVALUATION_REPAIR |
| Reference material from sources | **`ReferencePack`** or **`SourceEvidence`** | Extracted knowledge from reference novels | MULTI_SOURCE_GENESIS |
| Experimental validation proof | **`ExperimentalProof`** or **`ValidationEvidence`** | Proof that policy/model improved | CORPUS_EVALUATION_LEARNING |

**Implementation**:
- QUALITY spec: Rename to `QualityConfidenceLevel` enum (E1-E4) or keep "Evidence Level" as compound term
- GENESIS spec: Rename to `ReferenceEvidencePack` → `ReferencePack` (already partially done)
- LEARNING spec: Use `ExperimentalEvidence` or `ValidationProof` for scientific results
- **Gate**: P0 (V2-002), enforcement P7 (V2-022, V2-026)

**Decision**: Keep "Evidence Level" in Quality (established compound term), rename others.

---

### 1.2 "Authority" — Dual Meaning [HIGH]

**Problem**: Overloaded term with different meanings in different contexts.

**Conflict Details**:

| Context | Meaning |
|---------|---------|
| Context Compiler | **Source Priority** - ordering of information sources (constitution > genre > canon > contract > plan) |
| Document Metadata | **Authority Type** - document classification (ARCHITECTURE-SPEC, RESEARCH-EVIDENCE, etc.) |

**RESOLUTION**:

| Context | **UNIFIED TERM** | Definition |
|---------|------------------|------------|
| Information source ordering | **`SourcePrecedence`** or **`InformationPriority`** | T0-T7 hierarchy for conflict resolution |
| Document classification | **`DocumentAuthority`** or **`AuthorityType`** | Metadata field indicating document type |

**Implementation**:
- CONTEXT_INTELLIGENCE spec: Rename "authority priority" → `source_precedence` in code/schemas
- All spec headers: Keep `Authority:` field (established convention), or fully qualify as `DocumentAuthority:`
- **Gate**: P5 (V2-013, V2-014)

**Decision**: Context uses `SourcePrecedence`, document metadata keeps `Authority` field (compound context clarifies).

---

### 1.3 "Contract" — Multi-Layer Usage [MEDIUM]

**Problem**: Same term at different abstraction levels, potentially confusing.

**Conflict Details**:

| Spec | Term | Meaning | Layer |
|------|------|---------|-------|
| PLANNING_CONTRACT | ChapterContract | Semantic requirements (what chapter must accomplish) | Narrative/Domain |
| PLANNING_CONTRACT | SceneContract | Scene-level semantic commitments | Narrative/Domain |
| PRODUCTION_WORKFLOW | StageContract | Technical execution contract (inputs, outputs, idempotency) | Infrastructure/Technical |

**RESOLUTION**:

| Layer | **UNIFIED TERM** | Definition | Usage |
|-------|------------------|------------|-------|
| Narrative/Domain | **`SemanticContract`** or keep `ChapterContract` / `SceneContract` | Story-level commitments | PLANNING_CONTRACT |
| Technical/Infrastructure | **`ExecutionContract`** or **`StageContract`** | Technical execution requirements | PRODUCTION_WORKFLOW |

**Implementation**:
- No rename needed if context always distinguishes (ChapterContract vs StageContract)
- If generic "Contract" used: qualify as Semantic vs Execution
- **Gate**: P4 (V2-011), P8 (V2-017)

**Decision**: No conflict if terms remain qualified (ChapterContract, SceneContract, StageContract). Generic "Contract" must specify type.

---

## 2. CORE DOMAIN TERMS

### 2.1 Canon & State

| Term | **UNIFIED DEFINITION** | Aliases Prohibited | Authority Tier |
|------|------------------------|-------------------|----------------|
| **Canon** | The committed, authoritative narrative truth; what has definitively happened in the story | Story Truth, Narrative Truth (avoid) | T3 |
| **Canon HEAD** | The current tip of the canonical event log; the latest committed state | - | T3 |
| **Canon Event Log** | Append-only sequence of all CanonCommit events | Event Stream | T3 |
| **Canon Snapshot** | Projection of narrative state at a specific Canon commit | State Snapshot, Canon State | T3 |
| **Canon Commit** | The only operation that writes to Canon; requires Permit and passes all gates | Commit (ambiguous alone) | T3 process |
| **CanonCommit Service** | The single architectural boundary that executes Canon writes | Canon Writer (avoid) | T1 architecture |
| **Draft** | Generated text that is NOT Canon until committed | Candidate Text | T6 |
| **NarrativeDelta** | Structured proposal of story changes extracted from Draft | Story Change Proposal | T6 |
| **ChangeSet** | Validated, ready-to-commit collection of narrative deltas | - | T6→T3 transition |
| **CommitPermit** | Proof that ChangeSet has passed all required validations and authorizations | Approval, Clearance (avoid) | T3 gate artifact |

**Key Principle**: Draft is NOT Canon (P-003), NarrativeDelta is proposal not truth (CANON spec section 0).

---

### 2.2 Genre & Domain

| Term | **UNIFIED DEFINITION** | Context | Authority Tier |
|------|------------------------|---------|----------------|
| **Genre** | A narrative domain defined by reality model, world rules, progression mechanics, and reader promises | Not a label/tag | Concept |
| **GenrePack** | Version-controlled, machine-executable package containing Genre rules, extensions, constraints, and validation logic | Genre Instance | T2 |
| **Genre Constitution** | The highest-priority rules within a GenrePack (allowed/forbidden elements, world laws) | Genre Hard Rules | T2 |
| **Genre Hard Rule** | Constraint that can BLOCK CanonCommit if violated | Genre Constraint | T2 validation |
| **Genre Soft Rule** | Guidance/preference that doesn't block commit | Genre Preference | T2 guidance |
| **Canon Extension** | Genre-specific narrative state fields (e.g., cultivation realm, business metrics) | Genre State | T2 schema |
| **Reality Model** | Genre's rules about what can/cannot happen in its world (e.g., urban: no magic) | World Model | T2 |
| **Progression Model** | Abstraction for character growth (e.g., PowerProgression, WealthProgression, TechProgression) | Growth Model | T2 |

**Key Principle**: Genre is foundational domain (P-002), not afterthought.

---

### 2.3 Planning & Contracts

| Term | **UNIFIED DEFINITION** | Scope | Authority Tier |
|------|------------------------|-------|----------------|
| **Plan** | Intention for future narrative; what SHOULD happen | Future | T4 |
| **SeriesVision** | Overarching multi-volume narrative direction and reader promise | Series level | T4 |
| **ArcPlan** | Multi-chapter narrative arc structure | Arc level | T4 |
| **ChapterContract** | Semantic requirements a chapter must satisfy (transitions, payoffs, promises) | Chapter level | T4 |
| **SceneContract** | Granular scene-level narrative commitments | Scene level | T4 |
| **RequiredTransition** | State change that MUST occur for contract satisfaction | Mandatory change | T4 constraint |
| **ForbiddenTransition** | State change that MUST NOT occur (Genre or plan violation) | Prohibited change | T4 constraint |
| **OptionalTransition** | State change that MAY occur | Allowed change | T4 option |

**Key Principle**: Plan vs Canon conflict → Canon wins, Plan re-plans (CONSTITUTION section 8, P-017).

---

### 2.4 Context & Compilation

| Term | **UNIFIED DEFINITION** | Notes | Authority Tier |
|------|------------------------|-------|----------------|
| **Context** | Compiled information provided to a Worker (Writer/Judge/Planner) | Not raw database dump | T5 compilation |
| **ContextArtifact** | Version-controlled, content-addressed context package for one execution | Reproducible input | T5 artifact |
| **Context Compiler** | Service that assembles Context from Genre, Canon, Contract, Knowledge, Evidence according to Authority Priority | - | T1 service |
| **Mandatory Item** | Context element that MUST be included (e.g., character identity, current genre rules) | Required | T5 constraint |
| **Optional Item** | Context element that MAY be included if space permits | Discretionary | T5 option |
| **Token Budget** | Maximum context size for a single Worker invocation | Context limit | T5 constraint |
| **Authority Priority** → **SourcePrecedence** | Ordering: constitution > genre > canon > contract > plan > derived > reference > market > diagnostic | Conflict resolution | T0 hierarchy |

**Key Principle**: Context must be compiled, not ad-hoc (P-016).

---

### 2.5 Production & Workflow

| Term | **UNIFIED DEFINITION** | Notes | Authority Tier |
|------|------------------------|-------|----------------|
| **Workflow** | Orchestrated sequence of stages to produce and commit a narrative unit | End-to-end process | T1 |
| **WorkflowRun** | Single execution instance of a Workflow | One run | T1 instance |
| **Stage** | Individual step within a Workflow (e.g., Generate, Validate, Repair, Commit) | Atomic step | T1 component |
| **StageContract** → **ExecutionContract** | Technical contract for a Stage (inputs, outputs, idempotency, retry semantics) | Technical layer | T1 specification |
| **Checkpoint** | Workflow resumption point; state saved for recovery | Recovery point | T1 artifact |
| **Idempotency Key** | Identifier ensuring duplicate execution returns original result | Deduplication | T1 mechanism |
| **Resume** | Restart Workflow from last successful Checkpoint | Recovery operation | T1 operation |
| **Retry** | Re-attempt a failed Stage | Error recovery | T1 operation |
| **ProductionState** | Single authoritative state of a narrative unit in the production lifecycle | NOT Canon state | T1 state |

**Key Principle**: Workflow state ≠ Canon state (WF-POL-002). Workflow can be FAILED while Canon remains valid.

---

### 2.6 Quality & Evaluation

| Term | **UNIFIED DEFINITION** | Notes | Authority Tier |
|------|------------------------|-------|----------------|
| **Quality Layer** | One dimension of quality evaluation (Q0-Q8: schema, canon, contract, semantics, craft, reader sim, human gold, market) | Evaluation dimension | T1 |
| **QualityConfidenceLevel** (fka Evidence Level) | Confidence in evaluation result: E1=deterministic, E2=semantic AI, E3=simulated reader, E4=real reader | Confidence scale | T1 |
| **QualityReport** | Structured output of quality evaluation | Diagnostic output | T7 |
| **Hard Gate** | Quality check that can BLOCK progression (Q0-Q3) | Mandatory pass | T1 enforcement |
| **Soft Gate** | Quality feedback that informs but doesn't block (Q4-Q6) | Advisory | T1 guidance |
| **RepairPlan** | Proposed fixes for quality failures | Fix proposal | T7 |
| **Patch** | Targeted fix for specific quality issue | Surgical edit | T6 artifact |
| **Rewrite** | Full regeneration (used sparingly per patch-first policy) | Full regen | T6 artifact |
| **Golden Set** | Human-curated exemplars for calibration | Truth corpus | T5 |
| **Blind Review** | Human evaluation without AI scores visible | Human truth | T5 |

**Key Principle**: AI Judge is not ground truth (P-010). E1-E4 must calibrate against human/market eventually (P-020).

---

### 2.7 Genesis & Reference

| Term | **UNIFIED DEFINITION** | Notes | Authority Tier |
|------|------------------------|-------|----------------|
| **Genesis** | Process of creating initial story foundation from intent/reference/corpus | Story birth | T1 process |
| **GenesisSpec** | Unified output of Genesis process (converges Idea/Reference/Hybrid/Corpus inputs) | Startup spec | T4 |
| **ReferencePack** (fka Evidence Pack) | Knowledge extracted from source novels for mechanism learning | Input knowledge | T5 |
| **Reference Intelligence** | System for analyzing reference works and extracting patterns | Learning system | T1 system |
| **Originality Guard** | System preventing direct copying from reference materials | Anti-plagiarism | T1 system |
| **Mechanism Transfer** | Learning narrative functions/patterns, not content | Abstraction | Principle |
| **Genesis Tournament** | Multi-candidate Genesis evaluation and selection | Genesis selection | T1 process |

**Key Principle**: Reference material cannot write Canon directly (P-011, INV-007).

---

### 2.8 Workers & Services

| Term | **UNIFIED DEFINITION** | Notes | Authority Tier |
|------|------------------------|-------|----------------|
| **Worker** | Replaceable execution agent (Writer, Planner, Reviewer, Extractor, Repairer, Judge) | Computation, not truth | T1 concept |
| **Writer** | Worker that generates Draft text from Context | Text generator | T1 role |
| **Planner** | Worker that generates Plans/Contracts | Planning agent | T1 role |
| **Extractor** | Worker that converts Draft to NarrativeDelta | Story analyzer | T1 role |
| **Reviewer** / **Judge** | Worker that evaluates quality | Evaluator | T1 role |
| **Repairer** | Worker that generates RepairPlan and Patches | Fix generator | T1 role |
| **Model** | Underlying LLM (Claude, GPT, DeepSeek, etc.) | Provider | Infrastructure |
| **Provider** | API service hosting Models | API backend | Infrastructure |
| **Model Gateway** | Abstraction layer isolating system from specific Providers | Provider abstraction | T1 architecture |

**Key Principle**: Workers are replaceable, don't own long-term truth (P-006). Agents are Workers, not architecture (P-007).

---

### 2.9 Narrative Domain Entities

| Term | **UNIFIED DEFINITION** | Schema | Authority Tier |
|------|------------------------|--------|----------------|
| **Character** | Individual with identity, traits, knowledge, goals, relationships | character.schema.json | T2/T3 entity |
| **Relationship** | Typed connection between entities (social, power, knowledge, resource) | relationship.schema.json | T2/T3 entity |
| **Event** | Something that happened at a specific time, causing state change | event.schema.json | T3 entity |
| **Knowledge** | Information entities know/believe (may be true or false) | knowledge.schema.json | T3 entity |
| **Promise** | Narrative commitment to reader (setup → payoff) | promise.schema.json | T3 entity |
| **Mystery** | Question posed to reader (setup → revelation) | mystery.schema.json | T3 entity |
| **Timeline** | Temporal structure of events | timeline.schema.json | T3 structure |
| **Location** | Place in story world | location.schema.json | T2/T3 entity |
| **Faction** | Group/organization entity | faction.schema.json | T2/T3 entity |
| **Object** | Significant item in story | object.schema.json | T2/T3 entity |

**Fact Mutability**: Defined in NARRATIVE_DOMAIN_SPEC (Immutable: identity, parent facts; Mutable: beliefs, locations; Append-only: events, knowledge)

---

### 2.10 Lifecycle & Retcon

| Term | **UNIFIED DEFINITION** | Notes | Authority Tier |
|------|------------------------|-------|----------------|
| **Retcon** | Explicit retroactive Canon change with invalidation cascade | Retroactive continuity | T3 operation |
| **R1 Retcon** | Soft retcon (annotation, alternative interpretation) | Mild change | T3 level |
| **R2 Retcon** | Medium retcon (state correction, minor fact change) | Moderate change | T3 level |
| **R3 Retcon** | Hard retcon (major past rewrite, requires human authority) | Major change | T3 level |
| **Invalidation Cascade** | Automatic marking of dependent artifacts as stale after Retcon | Dependency tracking | T3 mechanism |
| **Branch** | Alternate Canon timeline (experimental in v1.0) | Alternate history | T3 structure |
| **Stale** | Artifact based on superseded Canon state | Out of date | Lifecycle state |
| **Invalid** | Artifact failed validation | Rejected | Lifecycle state |

**Key Principle**: Silent retcon is prohibited (PROHIBIT-010).

---

### 2.11 Provenance & Observability

| Term | **UNIFIED DEFINITION** | Notes | Authority Tier |
|------|------------------------|-------|----------------|
| **Provenance** | Traceable lineage of an artifact (inputs, producer, version, policy) | Audit trail | T1 requirement |
| **RunFingerprint** | Content-addressed identifier of production conditions | Reproducibility | T1 artifact |
| **Artifact** | Persistent output with provenance (ContextArtifact, QualityReport, etc.) | Tracked output | T1 concept |
| **Manifest** | Metadata about artifact contents and dependencies | Inventory | T1 metadata |
| **Content Hash** | Cryptographic hash of artifact content | Integrity check | T1 verification |
| **Parent Hash** | Reference to prior Canon state for chain validation | Chain link | T3 verification |

**Key Principle**: Persistent artifacts require provenance (P-012).

---

### 2.12 Security & Authority

| Term | **UNIFIED DEFINITION** | Notes | Authority Tier |
|------|------------------------|-------|----------------|
| **Human Authority** | Explicit human decision for high-stakes actions | Human override | Override |
| **Authorization** | Permission to perform sensitive operation | Access control | Platform |
| **Secret** | Sensitive credential (API key, token, password) | Must not leak | Platform |
| **Audit Log** | Tamper-evident log of sensitive operations | Security trail | Platform |
| **PII** | Personally Identifiable Information | Must protect | Platform |

**Key Principle**: Day 1 secret scanning, no keys in Git (CONSTITUTION section 21).

---

### 2.13 Market & Learning

| Term | **UNIFIED DEFINITION** | Notes | Authority Tier |
|------|------------------------|-------|----------------|
| **Market Signal** | Real reader behavior data (clicks, retention, payments) | Real feedback | T5 |
| **Reader Promise** | Implicit contract with reader about what story will deliver | Genre contract | T2/T4 |
| **Corpus** | Collection of novels for analysis/learning | Training data | T5 |
| **Experiment** | Controlled test of policy/model change | A/B test | T1 process |
| **Baseline** | Reference policy/model for comparison | Control | T1 artifact |
| **Holdout Set** | Data reserved for validation, not training | Test set | T1 artifact |
| **Promotion Gate** | Criteria for deploying experimental policy to production | Deploy gate | T1 gate |
| **MarketTrendSnapshot** | Time-bound observation of market patterns | Temporal evidence | T5 |

**Key Principle**: Market trend ≠ Genre truth (P-009).

---

## 3. PROHIBITED ALIASES

**Do not use these terms** (ambiguous or superseded):

| Prohibited Term | Why | Use Instead |
|-----------------|-----|-------------|
| "Story Truth" | Ambiguous | Canon |
| "Writer Memory" | Misleading (implies AI owns truth) | Canon, Context |
| "Approved Text" | Vague | Committed Canon |
| "AI Judge Score = Truth" | Violates P-010 | QualityReport (T7 evidence) |
| "Reference Text = Canon" | Violates P-011 | ReferencePack (T5 input) |
| "Draft = Canon" | Violates P-003 | Draft (T6) vs Canon (T3) |
| "Genre Label" / "Genre Tag" | Shallow view | GenrePack (domain) |
| "Keyword = Genre" | V1 mistake | Genre Hard Rule (validated) |
| "Score Gates Deploy" | Uncalibrated | Q0-Q3 Hard Gates + Calibration |
| "Automatic Retcon" | Dangerous | R3 requires human authority |
| "Second Canon" | Prohibited | Single Canon (INV-004) |

---

## 4. COMPOUND TERMS (Established Conventions)

These multi-word terms are canonical and should not be abbreviated:

| Compound Term | Abbreviation | Status |
|---------------|--------------|--------|
| Canon Commit | CanonCommit (class name OK) | Canonical |
| Chapter Contract | ChapterContract | Canonical |
| Scene Contract | SceneContract | Canonical |
| Story Bible | - | Canonical |
| Genre Pack | GenrePack | Canonical |
| Commit Permit | CommitPermit | Canonical |
| Context Artifact | ContextArtifact | Canonical |
| Narrative Delta | NarrativeDelta | Canonical |
| Quality Report | QualityReport | Canonical |
| Repair Plan | RepairPlan | Canonical |
| Reference Pack | ReferencePack | Canonical |
| Model Gateway | - | Canonical |

---

## 5. ABBREVIATIONS & ACRONYMS

**Approved**:
- **ADR**: Architecture Decision Record
- **P0-P14**: Implementation phases
- **M0-M7**: Milestones
- **V2-001 to V2-060**: Task IDs
- **T0-T7**: Truth hierarchy tiers
- **Q0-Q8**: Quality layers
- **E1-E4**: Quality confidence levels (fka Evidence Levels)
- **R1-R3**: Retcon levels
- **CA-01 to CA-24**: ccdoc audit findings
- **AR-01 to AR-20**: Architecture review findings
- **INV-001 to INV-015**: Invariants
- **PROHIBIT-001 to PROHIBIT-014**: Prohibitions
- **P-001 to P-020**: Core principles
- **CI**: Continuous Integration
- **PII**: Personally Identifiable Information
- **API**: Application Programming Interface
- **LLM**: Large Language Model

**Prohibited** (use full term):
- ~~"CC"~~ for Canon Commit → use "CanonCommit"
- ~~"GP"~~ for GenrePack → use "GenrePack"
- ~~"ND"~~ for NarrativeDelta → use "NarrativeDelta"

---

## 6. CROSS-SPECIFICATION TERMINOLOGY AUDIT

**Verified Consistent**:
- ✅ Canon / Canon Commit / Canon HEAD / Canon Event Log (all specs align)
- ✅ GenrePack / Genre Rules (GENRE spec authoritative)
- ✅ ChapterContract / SceneContract (PLANNING spec authoritative)
- ✅ WorkflowRun / Stage / Checkpoint (WORKFLOW spec authoritative)
- ✅ NarrativeDelta / ChangeSet (NARRATIVE_DOMAIN spec authoritative)
- ✅ Draft is NOT Canon (consistently enforced across all specs)

**Resolved in This Baseline**:
- ✅ "Evidence" → Context-specific: QualityConfidenceLevel / ReferencePack / ExperimentalProof
- ✅ "Authority" → Context-specific: SourcePrecedence / DocumentAuthority
- ✅ "Contract" → Qualified: ChapterContract/SceneContract vs StageContract (ExecutionContract)

**Requires Implementation Verification**:
- ⚠️ "Commit" alone (ambiguous) → Always qualify: CanonCommit, Git commit, etc.
- ⚠️ "State" alone (ambiguous) → Qualify: Canon state, Workflow state, Production state
- ⚠️ "Context" alone (ambiguous in English) → Usually clear from technical context

---

## 7. NAMING CONVENTIONS

### 7.1 Schema Files
- Pattern: `{entity}.schema.json`
- Examples: `character.schema.json`, `canon-commit.schema.json`, `quality-report.schema.json`

### 7.2 Policy Files
- Pattern: `{domain}-policy.yaml`
- Examples: `canon-commit-policy.yaml`, `genre-policy.yaml`, `quality-policy.yaml`

### 7.3 Test Matrix Files
- Pattern: `{domain}-test-matrix.yaml`
- Examples: `canon-test-matrix.yaml`, `planning-contract-test-matrix.yaml`

### 7.4 Code Modules (Suggested)
- Domain types: `PascalCase` (Character, CanonCommit, NarrativeDelta)
- Services: `PascalCase` with "Service" suffix (CanonCommitService, ContextCompiler)
- Functions: `snake_case` (extract_narrative_delta, validate_genre_rules)

---

## 8. GLOSSARY CROSS-REFERENCE

This terminology baseline is the **normative reference**. The following documents contain glossaries that must align:

- ✅ **PROJECT_CONSTITUTION.md Section 28**: High-level glossary (12 terms) - **ALIGNED**
- ✅ **CANONICAL_STATE_SPEC.md**: Canon-specific terms - **ALIGNED**
- ✅ **NARRATIVE_DOMAIN_SPEC.md**: Domain entity definitions - **ALIGNED**
- ✅ **GENRE_INTELLIGENCE_SPEC.md**: Genre terminology - **ALIGNED**
- ⚠️ **Other specs**: Glossaries should be checked against this baseline

**Action Items**:
- V2-002 (P0): Freeze this baseline
- All specs: Verify terminology alignment during implementation
- New specs: Must reference this baseline

---

## 9. CHANGE CONTROL

### 9.1 Adding New Terms
1. Verify term doesn't conflict with existing meanings
2. Define in primary spec
3. Add to this baseline
4. Update cross-references
5. Increment baseline version (MINOR)

### 9.2 Deprecating Terms
1. Mark as DEPRECATED in this baseline
2. Provide migration path
3. Update all specs
4. Remove after 1 major version (grace period)

### 9.3 Renaming Terms
1. Requires MAJOR version increment if term is in schemas/APIs
2. Update all specs simultaneously
3. Provide migration guide
4. Consider aliases during transition period

---

## 10. IMPLEMENTATION GATES

**P0 (V2-002)**: Freeze this terminology baseline  
**P2 (V2-005, V2-006)**: Schema files must use baseline terms  
**P4 (V2-011, V2-012)**: Planning contracts must use baseline terms  
**P5 (V2-013)**: Context compiler must implement SourcePrecedence (not "authority priority")  
**P6 (V2-020)**: Quality layer must use QualityConfidenceLevel (not "Evidence Level")  
**P7 (V2-022, V2-026)**: Quality enforcement must distinguish evidence types  
**P10 (V2-042)**: Genesis must use ReferencePack (not "Evidence Pack")  
**All Phases**: Architecture fitness tests must verify terminology consistency

---

## 11. MULTI-LINGUAL CONSIDERATIONS

**Primary Language**: English (for code, schemas, APIs)  
**Documentation**: English + 中文 parallel documentation allowed  
**User-Facing**: May use localized terms  
**Internal Consistency**: English terms are normative; translations must map consistently

**Key Chinese Mappings** (for reference):
- Canon → 正典 / 正式事实
- GenrePack → 题材包
- ChapterContract → 章节契约
- NarrativeDelta → 叙事变化
- Draft → 草稿
- Commit → 提交
- Retcon → 追溯修改

**Rule**: Chinese terms in comments/docs must map 1:1 to English normative terms.

---

## 12. SUMMARY: CRITICAL TERMINOLOGY DECISIONS

**Most Important Resolutions**:

1. ✅ **"Evidence" split into three terms** based on context (QualityConfidenceLevel / ReferencePack / ExperimentalProof)
2. ✅ **Draft ≠ Canon** enforced consistently (T6 vs T3)
3. ✅ **NarrativeDelta = Proposal** not truth (T6)
4. ✅ **SourcePrecedence** for Context (not generic "authority")
5. ✅ **Contract qualified** by layer (ChapterContract vs StageContract)
6. ✅ **Judge outputs = T7 evidence** not truth
7. ✅ **Reference cannot write Canon** (T5 → T3 requires commit)
8. ✅ **Workers are replaceable** not truth owners
9. ✅ **Plan vs Canon conflict → Canon wins** (T4 vs T3)
10. ✅ **Single Canon write boundary** only (no "Second Canon")

**Prohibited Patterns**:
- ❌ Using "Evidence" ambiguously
- ❌ Using "Authority" ambiguously without context
- ❌ Saying "Draft is Canon"
- ❌ Saying "AI Judge = Truth"
- ❌ Saying "Reference = Canon"
- ❌ Using "State" without qualifier (Canon state? Workflow state?)
- ❌ Using "Commit" without qualifier (Canon commit? Git commit?)

---

**Document Status**: NORMATIVE  
**Enforcement**: All V2 specifications, schemas, code, and documentation  
**Next Update**: When new terms added or conflicts discovered  
**Verification**: Architecture fitness tests + manual spec review

---

**END OF TERMINOLOGY BASELINE**
