# V2-061 Implementation Contract: Character Knowledge & Intent Core

**Contract Version**: 1.0.0  
**Task ID**: V2-061  
**Status**: DRAFT (Contract Refinement Phase)  
**Owner Role**: domain-maintainer  
**Phase**: P1  
**Priority**: P0

---

## Purpose

Implement the minimum reliable domain model required for high-quality Chinese web novels to distinguish:

- **Objective truth** vs **character knowledge** vs **character belief**
- **Character goals** vs **character intent** vs **planned actions** vs **occurred events**
- **What is known** vs **what is believed** vs **what is misbelieved** vs **what is uncertain**

This prevents character omniscience, information leakage across viewpoints, and maintains narrative coherence in multi-POV storytelling.

---

## Product Quality Rationale

### Core Narrative Problems V2-061 Solves

1. **Character Omniscience Prevention**
   - Characters cannot automatically know objective facts
   - Knowledge must have explicit acquisition paths
   - Prevents "author knowledge leaking into character head"

2. **Belief vs Reality Distinction**
   - Character can believe X while truth is ¬X
   - Misbeliefs drive dramatic irony and suspense
   - System must hold contradictory propositions without conflict

3. **Intent vs Occurrence Separation**
   - Planned action ≠ occurred event
   - Goals ≠ achieved outcomes
   - Prevents premature fact commitment from character intentions

4. **Multi-POV Coherence**
   - Different characters have different knowledge states
   - Scene generation must respect per-character knowledge boundaries
   - Prevents impossible dialogue and actions

---

## Scope

### In Scope

**Character Entity**:
- Stable identity (builds on V2-005)
- Lifecycle states
- Base/derived schema strategy (see ADR-002)
- Project isolation

**Knowledge Model**:
- Per-character knowledge state
- Knowledge levels: KNOWN, BELIEVED, SUSPECTED, UNKNOWN, FALSELY_BELIEVED
- Knowledge acquisition provenance
- Source tracking (observation, communication, inference, document, rumor)

**Belief Model**:
- Propositions held by characters
- Confidence levels
- Source attribution
- Distinction from objective facts

**Intent Model**:
- Character goals
- Character intents
- Planned actions (not yet occurred)
- Goal lifecycle: ACTIVE, BLOCKED, ACHIEVED, FAILED, ABANDONED

**Boundaries**:
- Character cannot act on unknown facts without explicit path
- Knowledge boundary validation
- Anti-omniscience enforcement

**Schema & Serialization**:
- `character.schema.json`
- `knowledge.schema.json` (if separate)
- Round-trip preservation of legal derived fields
- Rejection of invalid entity types and lifecycle states

---

### Out of Scope (Deferred to Other Tasks)

**V2-006 Responsibility**:
- General entity-to-entity relationship topology (already implemented)
- Relationship registry (use V2-006's RelationshipRegistry)

**V2-007 Responsibility**:
- Objective event occurrences
- Authoritative timeline ordering
- Promise semantics
- Event-promise temporal relationships

**V2-008 Responsibility**:
- NarrativeDelta for character knowledge changes
- Change representation: "character learned X", "character discovered belief was false"
- Delta consumer interfaces

**Later Extensions**:
- Emotion modeling
- Location tracking
- Faction membership
- Resource ownership
- Complex inference engines
- Automatic knowledge propagation
- Multi-step reasoning chains

---

## Non-Goals

- Generic relationship tracking (use V2-006)
- Timeline/event ordering (V2-007)
- Genre-specific fields (realm, cultivation level, company equity)
- Database/Provider implementation dependencies
- Complete epistemology framework
- Bayesian belief networks
- Automated knowledge acquisition without explicit paths

---

## Terminology

**Objective Fact**: A proposition committed to canonical state as truth in the story world.

**Character Knowledge**: What a specific character knows (or thinks they know) about the world.

**Belief**: A proposition a character holds as true, which may or may not align with objective fact.

**Misbelief**: A belief that contradicts objective fact (dramatic irony source).

**Knowledge Level**:
- `KNOWN`: Character has verified/reliable knowledge
- `BELIEVED`: Character accepts as true but unverified
- `SUSPECTED`: Character has weak/uncertain belief
- `UNKNOWN`: Character has no knowledge of this fact
- `FALSELY_BELIEVED`: Character believes X, but ¬X is objectively true

**Goal**: What a character wants to achieve (desired end state).

**Intent**: Character's formed intention to pursue a goal or take action.

**Planned Action**: Action a character intends to take (not yet occurred).

**Occurred Event**: Action/event that has actually happened in story world (V2-007 domain).

**Provenance**: Source/path by which character acquired knowledge.

**Knowledge Boundary**: Set of facts a character can legitimately access.

---

## Domain Model

### Character

```python
@dataclass
class Character:
    """Core character entity with identity, knowledge state, and intent."""
    
    # Identity (builds on V2-005 EntityIdentity)
    id: EntityId
    project_id: ProjectId
    canonical_name: str
    aliases: list[str]
    
    # Lifecycle
    lifecycle: Literal["PLANNED", "ACTIVE", "INACTIVE", "DECEASED", "SUPERSEDED"]
    
    # Knowledge State
    knowledge: dict[str, CharacterKnowledge]  # keyed by proposition ID or fact ID
    beliefs: list[Belief]
    
    # Intent State
    goals: list[Goal]
    intents: list[Intent]
    planned_actions: list[PlannedAction]
    
    # Base vs Derived (ADR-002 decision)
    # TBD: Which fields are base, which are derived/computed
    
    # Metadata
    created_at: datetime
    updated_at: datetime
    authority: str
    provenance: dict
```

### CharacterKnowledge

```python
@dataclass
class CharacterKnowledge:
    """Represents what a character knows about a proposition/fact."""
    
    knower: EntityId  # The character who knows
    proposition: Proposition | str  # What is known (structured or ref)
    
    knowledge_level: Literal[
        "KNOWN",
        "BELIEVED", 
        "SUSPECTED",
        "UNKNOWN",
        "FALSELY_BELIEVED"
    ]
    
    # Provenance: How did character acquire this knowledge?
    source_type: Literal[
        "DIRECT_OBSERVATION",
        "COMMUNICATION",  # Told by another character
        "DOCUMENT",  # Read from source
        "INFERENCE",  # Reasoned from other knowledge
        "RUMOR",  # Heard indirectly
        "AUTHORITATIVE_DISCLOSURE"  # Author/narrator revelation
    ]
    source_ref: str | None  # Reference to event/communication/document
    
    acquired_at: datetime | None  # When knowledge was acquired
    confidence: float | None  # 0.0-1.0 for BELIEVED/SUSPECTED
    
    # Validity
    contradicts_objective_fact: bool | None  # True if this is a misbelief
```

### Belief

```python
@dataclass
class Belief:
    """A proposition a character holds as true."""
    
    holder: EntityId  # Character who holds belief
    proposition: Proposition
    confidence: float  # 0.0-1.0
    source: str  # Where belief came from
    formed_at: datetime | None
    
    # Truth alignment
    aligns_with_fact: bool | None  # True=correct, False=misbelief, None=unknown
```

### Proposition

```python
@dataclass
class Proposition:
    """Structured representation of a claimable fact."""
    
    subject: EntityId | str
    predicate: str  # "betrayed", "loves", "owns", "is_alive"
    object: EntityId | str | None
    context: dict | None  # Additional structured context
```

### Goal

```python
@dataclass
class Goal:
    """What a character wants to achieve."""
    
    id: str
    character: EntityId
    description: str
    target_state: dict | None  # Desired end state
    
    status: Literal[
        "ACTIVE",
        "BLOCKED",
        "ACHIEVED",
        "FAILED",
        "ABANDONED",
        "SUPERSEDED"
    ]
    
    priority: int | None
    formed_at: datetime | None
    resolved_at: datetime | None
```

### Intent

```python
@dataclass
class Intent:
    """Character's intention to pursue goal or take action."""
    
    character: EntityId
    goal_ref: str | None  # Reference to Goal if intent serves a goal
    description: str
    formed_at: datetime | None
    abandoned_at: datetime | None
```

### PlannedAction

```python
@dataclass
class PlannedAction:
    """Action character intends to take (NOT yet occurred)."""
    
    character: EntityId
    action_description: str
    intent_ref: str | None
    planned_for: datetime | None
    
    # Status
    status: Literal["PLANNED", "CANCELLED", "OCCURRED"]
    occurred_event_ref: str | None  # Ref to V2-007 Event if executed
```

---

## Objective Fact Boundary

**V2-061 does NOT define objective facts**.

Objective facts are:
- Canonical state entities (V2-005)
- Relationships (V2-006)
- Events (V2-007)

V2-061 defines:
- **What characters know/believe about objective facts**
- **What characters intend to do** (not what they did)

**Invariant**: Character knowledge state is SEPARATE from canonical fact state.

---

## Knowledge Semantics

### Knowledge Acquisition Paths

Character can acquire knowledge through:

1. **DIRECT_OBSERVATION**: Character witnesses event/state directly
2. **COMMUNICATION**: Another character tells them
3. **DOCUMENT**: Character reads written source
4. **INFERENCE**: Character deduces from existing knowledge
5. **RUMOR**: Character hears indirectly (low reliability)
6. **AUTHORITATIVE_DISCLOSURE**: Narrator/author grants knowledge

**Hard Rule**: Character CANNOT have knowledge without one of these paths.

### Knowledge Levels

- `KNOWN`: High-confidence, verified knowledge
- `BELIEVED`: Accepted as true, not verified
- `SUSPECTED`: Weak belief, uncertain
- `UNKNOWN`: Character has no information
- `FALSELY_BELIEVED`: Character believes X, but objective fact is ¬X

### Knowledge vs Belief

**Knowledge**: Epistemological state (what character has access to)  
**Belief**: Doxastic state (what character accepts as true)

A character can:
- KNOW X and BELIEVE X (aligned)
- BELIEVE X without KNOWING X (unverified belief)
- KNOW ¬X but still emotionally BELIEVE X (denial)
- SUSPECT X (weak knowledge/belief)

---

## Belief Semantics

**Belief** represents character's acceptance of a proposition.

**Key Properties**:
- Beliefs can contradict objective facts (misbeliefs)
- Beliefs can contradict other characters' beliefs
- Beliefs can change over time
- Beliefs have confidence levels

**Validation**: System must allow:
```python
# Objective fact
canon.entities["char_a"].lifecycle = "ALIVE"

# Character B's belief
char_b.beliefs.append(Belief(
    holder="char_b",
    proposition=Proposition("char_a", "is_dead", None),
    confidence=0.9,
    aligns_with_fact=False  # Misbelief
))
```

---

## Misbelief Semantics

**Misbelief** = Belief that contradicts objective fact.

**Critical for**:
- Dramatic irony
- Suspense
- Character development arcs
- Plot twists

**Implementation**: 
- `Belief.aligns_with_fact = False`
- OR `CharacterKnowledge.contradicts_objective_fact = True`
- OR `knowledge_level = "FALSELY_BELIEVED"`

**Validation Rule**: Misbeliefs must be explicitly representable without causing system errors.

---

## Provenance

Every `CharacterKnowledge` entry SHOULD have:
- `source_type` (how acquired)
- `source_ref` (what event/communication/document)
- `acquired_at` (when)

**Purpose**:
- Prevents omniscience
- Enables knowledge validation
- Supports debugging/explanation
- Drives narrative causality

**V2-061 Minimum**: Define provenance fields, but do NOT implement full automatic tracking (future work).

---

## Uncertainty

Characters can be UNCERTAIN about facts.

**Representation**:
- `knowledge_level = "SUSPECTED"`
- `confidence < 0.5` in Belief
- Explicitly separate from KNOWN/UNKNOWN

**Use Cases**:
- Mystery/suspense genres
- Character investigation arcs
- Gradual revelation

---

## Goal Semantics

**Goal** = Desired end state or achievement.

**Lifecycle**:
- `ACTIVE`: Character pursuing
- `BLOCKED`: Temporarily prevented
- `ACHIEVED`: Success
- `FAILED`: Cannot be achieved
- `ABANDONED`: Character gave up
- `SUPERSEDED`: Replaced by new goal

**Example**:
```python
Goal(
    id="goal_001",
    character="char_protagonist",
    description="Rescue sister from kidnappers",
    status="ACTIVE",
    priority=10
)
```

---

## Intent Semantics

**Intent** = Character's formed intention to act.

**Relationship**:
- Intent MAY serve a Goal
- Intent MAY exist without explicit Goal
- Intent is formed BEFORE action occurs

**Example**:
```python
Intent(
    character="char_protagonist",
    goal_ref="goal_001",
    description="Infiltrate enemy compound tonight",
    formed_at="2024-05-20T22:00:00Z"
)
```

---

## PlannedAction Semantics

**PlannedAction** = Specific action character intends to take.

**Critical Distinction**:
- PlannedAction status = "PLANNED" → HAS NOT OCCURRED
- PlannedAction status = "OCCURRED" → Links to V2-007 Event

**Anti-Pattern Prevention**:
```python
# WRONG: Treating plan as fact
if character.planned_actions[0].status == "PLANNED":
    canon.add_event(...)  # NO! Plan ≠ occurrence

# CORRECT: Plan and occurrence are separate
if event_occurred:
    action.status = "OCCURRED"
    action.occurred_event_ref = event.id
    canon.add_event(event)  # Only event goes to canon
```

---

## Temporal Boundary

**V2-061 does NOT implement authoritative timeline**.

**Allowed**:
- Timestamp fields (`acquired_at`, `formed_at`, `resolved_at`)
- Ordering within single character's knowledge/intent history
- Relative sequencing hints

**NOT Allowed**:
- Cross-character temporal ordering
- Global timeline enforcement
- Promise/event occurrence ordering

**Rationale**: V2-007 owns timeline. V2-061 provides temporal hooks for V2-007 to consume.

---

## Project Isolation

All Character entities MUST include `project_id`.

**Rules**:
- Character from Project A cannot have knowledge of facts in Project B
- Character references across projects are invalid
- Knowledge provenance cannot cross project boundaries

**Enforcement**: V2-005 EntityId already provides project isolation. V2-061 inherits this.

---

## Lifecycle

Character lifecycle states:

- `PLANNED`: Defined but not yet active in story
- `ACTIVE`: Currently part of story
- `INACTIVE`: Temporarily not appearing (still alive)
- `DECEASED`: Character has died in story
- `SUPERSEDED`: Character concept replaced/merged

**Validation**:
- DECEASED character cannot form new intents (unless ghost/supernatural)
- PLANNED character cannot have knowledge of story events
- SUPERSEDED character cannot be referenced in new content

---

## V2-005 Boundary

**V2-005 provides**:
- `EntityId`, `ProjectId`
- Entity identity and alias resolution
- EntityRegistry

**V2-061 builds on V2-005**:
- Character IS an Entity (has EntityId)
- Character inherits identity/alias semantics
- Character extends Entity with knowledge/intent

**No Overlap**: V2-061 does not reimplement identity/aliases.

---

## V2-006 Boundary

**V2-006 provides**:
- Relationship topology (entity-to-entity relationships)
- RelationshipType, Relationship, RelationshipRegistry
- add_relationship, query_relationships

**V2-061 uses V2-006**:
- Character relationships are stored in V2-006's RelationshipRegistry
- Character knowledge about relationships is V2-061's CharacterKnowledge

**No Overlap**: V2-061 does NOT create second relationship system.

**Example**:
```python
# Objective relationship (V2-006)
registry.add_relationship(
    Relationship(char_a, "MARRIED_TO", char_b)
)

# Character C's knowledge of relationship (V2-061)
char_c.knowledge["rel_001"] = CharacterKnowledge(
    knower=char_c.id,
    proposition="char_a is married to char_b",
    knowledge_level="BELIEVED",
    source_type="RUMOR"
)
```

---

## V2-007 Boundary

**V2-007 provides**:
- Objective Event occurrences
- Timeline ordering
- Promise semantics
- Event-promise temporal relationships

**V2-061 defers to V2-007**:
- PlannedAction.occurred_event_ref points to V2-007 Event
- Character knowledge acquisition can reference V2-007 Events
- V2-061 does NOT define event occurrence semantics

**Separation**:
- V2-061: "Character plans to do X" (intent)
- V2-007: "X occurred" (event)
- V2-061: "Character knows X occurred" (knowledge of event)

---

## V2-008 Boundary

**V2-008 provides**:
- NarrativeDelta representation
- Change consumer interfaces
- Delta application semantics

**V2-061 supports V2-008**:
- Knowledge state changes are delta-able:
  - `CharacterLearnedFact`
  - `CharacterFormedBelief`
  - `CharacterDiscoveredMisbelief`
  - `CharacterFormedIntent`
  - `CharacterAbandonedGoal`

**V2-061 does NOT implement NarrativeDelta**.

V2-061 provides domain primitives; V2-008 defines how changes are represented.

---

## Determinism

All V2-061 operations MUST be deterministic given same inputs.

**Requirements**:
- Knowledge acquisition with same inputs → same knowledge state
- Belief updates with same inputs → same belief state
- Goal lifecycle transitions with same inputs → same status

**Non-Deterministic Operations** (NOT in V2-061):
- Inference/reasoning (future extension)
- Automatic knowledge propagation (future extension)
- Probabilistic belief updates (future extension)

---

## Serialization

**Schema Files**:
- `specs/schemas/character.schema.json`
- `specs/schemas/knowledge.schema.json` (if separate)

**Round-Trip Requirement**:
- Serialize Character → JSON
- Deserialize JSON → Character
- Result MUST equal original for all legal fields

**Derived Fields**:
- ADR-002 defines which fields are derived/computed
- Derived fields with non-default values MUST round-trip
- See ADR-002 for base vs derived strategy

---

## Failure Semantics

**Validation Failures** (MUST reject):
- Invalid entity type (e.g., `entity_type != "CHARACTER"`)
- Invalid lifecycle state (e.g., unknown status)
- Cross-project entity references
- Character acting on knowledge outside boundary (if validation enabled)

**Graceful Degradation**:
- Missing provenance → Warning, not error
- Unknown confidence → Default to None
- Missing timestamps → Allowed (optional fields)

---

## Acceptance Matrix

### Knowledge Acquisition (AC-1)

| Scenario | Expected |
|----------|----------|
| Character observes event directly | knowledge_level=KNOWN, source_type=DIRECT_OBSERVATION |
| Character told by another | knowledge_level=BELIEVED, source_type=COMMUNICATION |
| Character reads document | knowledge_level=KNOWN, source_type=DOCUMENT |
| Character hears rumor | knowledge_level=SUSPECTED, source_type=RUMOR |
| Character has no path to fact | knowledge entry NOT created OR knowledge_level=UNKNOWN |

### Belief vs Fact (AC-2)

| Objective Fact | Character Belief | System Behavior |
|----------------|------------------|-----------------|
| A is alive | B believes A is dead | Both stored without conflict |
| X betrayed Y | Y believes X is loyal | aligns_with_fact=False |
| Event occurred | Character unaware | Knowledge entry absent or UNKNOWN |

### Intent vs Occurrence (AC-3)

| Scenario | PlannedAction Status | Event Created? |
|----------|----------------------|----------------|
| Character plans to attack | PLANNED | NO |
| Plan executed successfully | OCCURRED | YES (V2-007) |
| Plan cancelled | CANCELLED | NO |

### Goal Lifecycle (AC-4)

| Transition | Valid? | Notes |
|------------|--------|-------|
| ACTIVE → ACHIEVED | YES | Goal completed |
| ACTIVE → FAILED | YES | Goal impossible |
| BLOCKED → ACTIVE | YES | Obstacle removed |
| ACHIEVED → ACTIVE | NO | Cannot un-achieve |
| ABANDONED → SUPERSEDED | YES | Replaced by better goal |

### Knowledge Boundary (AC-5)

| Scenario | Validation Result |
|----------|-------------------|
| Character acts on KNOWN fact | VALID |
| Character acts on BELIEVED fact | VALID (risky behavior) |
| Character acts on UNKNOWN fact | INVALID (unless inference/guess explicit) |
| Character references secret they shouldn't know | INVALID (anti-omniscience) |

### Schema Round-Trip (AC-6)

| Input | Round-Trip Preserves? |
|-------|----------------------|
| Legal derived field with value | YES |
| Base field with value | YES |
| Invalid entity type | REJECT on deserialize |
| Invalid lifecycle | REJECT on deserialize |

---

## Architecture Constraints

### Layering

```
V2-061 (Character/Knowledge/Intent)
    ↓ uses
V2-006 (Relationships)
    ↓ uses
V2-005 (Identity/Aliases)
```

V2-061 MUST NOT:
- Bypass V2-005 identity
- Reimplement V2-006 relationships
- Implement V2-007 events
- Implement V2-008 deltas

### Dependencies

**Allowed**:
- `from anovel.domain.identity import EntityId, ProjectId, EntityRegistry`
- `from anovel.domain.relationship import RelationshipRegistry`

**NOT Allowed**:
- Database imports
- Provider imports
- Workflow imports
- Canon commit imports (those are consumers, not dependencies)

### Testability

All V2-061 classes MUST:
- Be unit-testable without database
- Be instantiable from pure Python/JSON
- Have deterministic equality checks
- Support copy/deepcopy

---

## ADR Dependencies

### ADR-002: Character Base/Derived Schema Strategy

**Status**: REQUIRED  
**Decision Due**: Before V2-061 implementation  
**Timing**: before_interface_implementation

**Question**: Which Character fields are base (stored), which are derived/computed?

**Impact on V2-061**:
- Defines serialization strategy
- Affects round-trip preservation
- Influences schema design

**Recommendation** (draft, pending formal ADR-002 ratification):

**REVISE ADR-002** to address:

1. **Base Fields** (always stored):
   - Identity: `id`, `project_id`, `canonical_name`, `aliases`
   - Lifecycle: `lifecycle`
   - Knowledge: `knowledge` dict, `beliefs` list
   - Intent: `goals`, `intents`, `planned_actions`
   - Metadata: `created_at`, `updated_at`, `authority`, `provenance`

2. **Derived/Computed Fields** (calculated on demand, but MAY be serialized):
   - `active_goals` (filtered view of goals where status=ACTIVE)
   - `misbeliefs` (filtered view where aligns_with_fact=False)
   - `knowledge_summary` (statistics over knowledge dict)

3. **Round-Trip Strategy**:
   - Base fields: Always serialize/deserialize
   - Derived fields with non-default values: Serialize if present, recompute if absent
   - Derived fields with default values: May omit from serialization

**Rationale**:
- Prevents data loss on round-trip
- Allows optimization (don't recompute if already computed)
- Maintains schema extensibility

**Formal ADR-002 Decision Required Before Implementation Authorization**.

---

## Implementation Steps

### Step 1: Character Entity Core
- Define Character dataclass
- Integrate with V2-005 EntityId/ProjectId
- Implement lifecycle validation
- Schema: basic character.schema.json

### Step 2: Knowledge Model
- Define CharacterKnowledge dataclass
- Implement knowledge levels
- Define acquisition source types
- Add provenance fields

### Step 3: Belief Model
- Define Belief dataclass
- Define Proposition dataclass
- Implement misbelief support (aligns_with_fact field)

### Step 4: Intent Model
- Define Goal dataclass with lifecycle
- Define Intent dataclass
- Define PlannedAction dataclass
- Ensure separation from V2-007 events

### Step 5: Knowledge Boundary Validation
- Implement anti-omniscience checks
- Validate knowledge acquisition paths
- Reject unauthorized knowledge access

### Step 6: Serialization & Schema
- Complete character.schema.json
- Implement JSON Schema validation
- Test round-trip preservation

### Step 7: Integration with V2-006
- Character relationships via RelationshipRegistry
- Knowledge about relationships
- Ensure no overlap

### Step 8: Contract Tests
- Acceptance criteria validation
- Anti-pattern prevention tests
- Boundary condition tests

---

## Deferred Capabilities

**NOT in V2-061 initial implementation**:

1. **Automatic Knowledge Propagation**
   - Character A tells B → B automatically gains knowledge
   - Deferred: Requires communication event modeling (V2-007)

2. **Inference Engine**
   - Character deduces new knowledge from existing knowledge
   - Deferred: Complex reasoning system, future extension

3. **Emotion Modeling**
   - Character emotional states
   - Deferred: Separate feature, not P0 critical

4. **Location Tracking**
   - Character physical location
   - Deferred: Spatial reasoning, later phase

5. **Complex Provenance Chains**
   - Multi-hop knowledge: A→B→C
   - Deferred: Initial impl uses single-hop provenance

6. **Temporal Knowledge Validity**
   - Knowledge expires or becomes outdated
   - Deferred: Requires timeline integration (V2-007)

7. **Bayesian Belief Updates**
   - Probabilistic belief revision
   - Deferred: Advanced epistemology, not P1

---

## Risks & Mitigations

### Risk 1: ADR-002 Delay
**Impact**: Cannot finalize schema strategy  
**Mitigation**: Parallel ADR-002 drafting with contract refinement

### Risk 2: V2-006 Interface Mismatch
**Impact**: Relationship integration issues  
**Mitigation**: V2-006 already implemented and tested, interface stable

### Risk 3: Scope Creep (Inference/Emotion)
**Impact**: Timeline delay  
**Mitigation**: Strict deferred capabilities list, contract enforcement

### Risk 4: Knowledge Boundary Over-Engineering
**Impact**: System too rigid for creative writing  
**Mitigation**: Validation is OPTIONAL, warning-level initially

---

## Success Criteria

V2-061 implementation is COMPLETE when:

1. ✅ All acceptance criteria tests PASS
2. ✅ Contract tests validate all boundaries
3. ✅ Schema round-trip preserves legal fields
4. ✅ ADR-002 formally ratified
5. ✅ Integration with V2-005/V2-006 verified
6. ✅ Anti-omniscience enforcement working
7. ✅ Independent contract review APPROVED
8. ✅ Governance regression tests (test_governance, test_ai_execution) PASS

**Then and only then**: Implementation authorization may be granted.

---

## Machine SSOT Changes Required

**Current State**: Task status = OPEN

**Required Changes** (DO NOT APPLY YET):

None currently identified. If contract refinement reveals machine definition errors, they will be documented here for future application.

---

**Contract Status**: DRAFT  
**Next Phase**: ADR-002 Resolution → Independent Review → Ratification (blocked by governance debt)  
**Implementation**: NOT AUTHORIZED

