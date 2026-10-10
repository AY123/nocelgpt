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

**Objective Fact**: A proposition committed to canonical state as truth in the story world (V2-007 authority for events, V2-005/V2-006 for entities/relationships).

**Character Knowledge**: What a specific character knows (or thinks they know) about the world. Epistemic state.

**Proposition**: A structured claim about story-world state with stable identity (PropositionId).

**Misbelief**: Character knowledge where `aligns_with_fact = False` (character believes X, but ¬X is objectively true). Source of dramatic irony.

**Knowledge Level**:
- `KNOWN`: Character has high-confidence, verified knowledge
- `BELIEVED`: Character accepts as true but hasn't independently verified
- `SUSPECTED`: Character has weak/uncertain belief

**UNKNOWN Semantics**:
- **No epistemic record** = ordinary UNKNOWN (character has no information)
- Explicit `knowledge_level = "UNKNOWN"` is NOT used (removed from V2-061)
- Higher-order epistemic states like "knowing that you don't know" are deferred

**Goal**: What a character wants to achieve (desired end state).

**Intent**: Character's formed intention to pursue a goal or take action.

**Planned Action**: Action a character intends to take (not yet occurred).

**Occurred Event**: Action/event that has actually happened in story world (V2-007 domain).

**Provenance**: Source/path by which character acquired knowledge. REQUIRED for all epistemic records.

**Knowledge Boundary**: Set of facts a character can legitimately access given their acquisition paths.

**Anti-Omniscience**: Core invariant preventing author/reader knowledge from automatically becoming character knowledge.

---

## Domain Model

### Character

```python
@dataclass
class Character:
    """Core character entity with identity, knowledge state, and intent.

    Identity Authority: V2-061 does NOT own canonical_name or aliases.
    Character identity is provided by V2-005 EntityIdentity. This class
    extends entity with epistemic and intentional state.
    """

    # Identity (V2-005 authority - DO NOT duplicate canonical_name/aliases here)
    entity_id: EntityId  # References V2-005 EntityIdentity
    project_id: ProjectId  # Project scope (must match EntityIdentity.project_id)

    # Lifecycle
    lifecycle: Literal["PLANNED", "ACTIVE", "INACTIVE", "DECEASED", "SUPERSEDED"]

    # Knowledge State
    # Key: PropositionId (stable proposition identifier)
    # Value: What this character knows/believes about that proposition
    knowledge: dict[PropositionId, CharacterKnowledge]

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

### PropositionId

```python
PropositionId = NewType("PropositionId", str)
"""
Stable identifier for propositions (claims about story-world state).

Format: UUID v4 (lowercase, with hyphens, 36 characters)

A proposition has stable identity independent of its content.
This allows belief revision, truth alignment checks, and NarrativeDelta targeting.

Contract: V2-061 §3.6
"""
```

### Proposition

```python
@dataclass(frozen=True)
class Proposition:
    """
    Structured representation of a claimable fact about story-world state.

    Immutable. Identity is proposition_id.
    Content equality does NOT imply identity equality (two characters
    can independently form beliefs about "the same" content with different IDs).
    """

    proposition_id: PropositionId
    subject: EntityId | str  # What the claim is about
    predicate: str  # "betrayed", "loves", "owns", "is_alive", "is_dead"
    object: EntityId | str | None  # Target of predicate (if applicable)
    context: dict | None  # Additional structured context
```

### CharacterKnowledge

```python
@dataclass
class CharacterKnowledge:
    """
    Represents what a character knows/believes about a proposition.

    This is the epistemic state: what information the character has access to
    and how they relate to it.
    """

    knower: EntityId  # The character who holds this epistemic state
    proposition_id: PropositionId  # What proposition this is about

    # Epistemic Level
    knowledge_level: Literal[
        "KNOWN",      # High-confidence, verified knowledge
        "BELIEVED",   # Accepted as true, not independently verified
        "SUSPECTED",  # Weak belief, uncertain
    ]

    # Truth Alignment (can be checked against objective Canon state)
    # None = alignment unknown/not yet evaluated
    # True = belief aligns with objective fact
    # False = misbelief (character believes X, but ¬X is objectively true)
    aligns_with_fact: bool | None

    # Provenance: How did character acquire this knowledge? (REQUIRED)
    acquisition_source: Literal[
        "DIRECT_OBSERVATION",  # Character witnessed directly
        "COMMUNICATION",       # Told by another character (source_character required)
        "DOCUMENT",           # Read from written source (source_ref required)
        "INFERENCE",          # Reasoned from other knowledge (basis_ref required)
        "RUMOR",              # Heard indirectly (low reliability)
    ]

    # Source References (requirements depend on acquisition_source)
    source_character: EntityId | None  # For COMMUNICATION
    source_ref: str | None  # For DOCUMENT, event reference, etc.
    basis_ref: list[PropositionId] | None  # For INFERENCE (what was reasoned from)

    acquired_at: datetime | None  # When knowledge was acquired
    confidence: float | None  # 0.0-1.0 confidence level
```

### Belief

**REMOVED**: The `Belief` dataclass is removed from V2-061.

**Rationale**: `Belief` and `CharacterKnowledge` were redundant - both represented "what a character accepts as true about a proposition". This led to confusion about which to use and when.

**Single Model**: `CharacterKnowledge` now serves as the unified epistemic state representation, covering:
- What character knows (KNOWN)
- What character believes but hasn't verified (BELIEVED)
- What character suspects (SUSPECTED)
- Whether belief aligns with objective fact (aligns_with_fact)

**Migration**: Any reference to "Belief" in this contract should be understood as `CharacterKnowledge` with appropriate `knowledge_level` and `aligns_with_fact` settings.

### Goal

```python
@dataclass
class Goal:
    """What a character wants to achieve."""

    goal_id: GoalId  # Stable identifier (UUID v4)
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


GoalId = NewType("GoalId", str)
"""Stable identifier for character goals (UUID v4 format)."""
```

### Intent

```python
@dataclass
class Intent:
    """Character's intention to pursue goal or take action."""

    intent_id: IntentId  # Stable identifier (UUID v4)
    character: EntityId
    goal_ref: GoalId | None  # Reference to Goal if intent serves a goal
    description: str
    formed_at: datetime | None
    abandoned_at: datetime | None


IntentId = NewType("IntentId", str)
"""Stable identifier for character intents (UUID v4 format)."""
```

### PlannedAction

```python
@dataclass
class PlannedAction:
    """Action character intends to take (NOT yet occurred)."""

    action_id: PlannedActionId  # Stable identifier (UUID v4)
    character: EntityId
    action_description: str
    intent_ref: IntentId | None
    planned_for: datetime | None

    # Status
    status: Literal["PLANNED", "CANCELLED", "OCCURRED"]
    occurred_event_ref: str | None  # Ref to V2-007 Event if executed


PlannedActionId = NewType("PlannedActionId", str)
"""Stable identifier for planned actions (UUID v4 format)."""
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

### Knowledge Acquisition Paths (REQUIRED)

Character can ONLY acquire knowledge through explicit paths:

1. **DIRECT_OBSERVATION**: Character witnesses event/state directly
2. **COMMUNICATION**: Another character tells them (requires `source_character`)
3. **DOCUMENT**: Character reads written source (requires `source_ref`)
4. **INFERENCE**: Character deduces from existing knowledge (requires `basis_ref`)
5. **RUMOR**: Character hears indirectly (low reliability, source may be unknown)

**Hard Rule**: Character CANNOT have knowledge without one of these paths.

**Validation**: New epistemic records MUST specify `acquisition_source` and required source references. Missing provenance is INVALID (not just a warning).

**Anti-Omniscience Enforcement**:
- NO "AUTHORITATIVE_DISCLOSURE" source type (removed)
- Author/narrator knowledge does NOT automatically transfer to characters
- Even if author reveals X to reader, character only knows X if they have valid acquisition path

**Story-World Acquisition**:
If character receives information through:
- Divine revelation / oracle
- System messages in LitRPG
- Telepathy
- Prophecy
- Official announcements

These MUST still be modeled as story-world events with appropriate acquisition_source:
- Oracle = COMMUNICATION (from oracle entity) or DOCUMENT (from prophecy text)
- System message = DOCUMENT (system interface as document source)
- Telepathy = COMMUNICATION (from telepathic entity)

There is NO bypass that lets author inject knowledge directly into character head.

### Knowledge Levels

- `KNOWN`: High-confidence, verified knowledge
  - Character has strong evidence
  - Typically from DIRECT_OBSERVATION or trusted COMMUNICATION

- `BELIEVED`: Accepted as true, not independently verified
  - Character accepts proposition without verification
  - May be from COMMUNICATION (trusting source) or INFERENCE

- `SUSPECTED`: Weak belief, uncertain
  - Character has doubts or partial evidence
  - Often from RUMOR or incomplete INFERENCE

### UNKNOWN Semantics

**Representation**: Absence of epistemic record.

If `character.knowledge` does NOT contain entry for `proposition_id`, the character has no knowledge of that proposition (ordinary UNKNOWN state).

**No Explicit UNKNOWN Record**: Do NOT create CharacterKnowledge with `knowledge_level = "UNKNOWN"`. This literal is removed from the enum.

**Higher-Order Epistemic States** (deferred to future):
- "Character knows they don't know X" (metacognitive awareness)
- "Character believes they know X but actually doesn't" (false confidence)

These require more complex epistemic modeling and are OUT OF SCOPE for V2-061 initial implementation.

### Truth Alignment

**Field**: `aligns_with_fact: bool | None`

**Semantics**:
- `True`: Character's epistemic state aligns with objective canonical fact
- `False`: **Misbelief** - character believes/knows X, but ¬X is objectively true
- `None`: Alignment unknown or not yet evaluated

**Authority**: Truth alignment is determined by comparing:
- Character epistemic state (V2-061)
- Objective canonical state (V2-005 entities, V2-006 relationships, V2-007 events)

**V2-061 does NOT define objective truth**. V2-061 only:
- Stores character epistemic states
- References propositions that CAN BE aligned with objective truth
- Provides `aligns_with_fact` field for alignment results

**Evaluation**: Truth alignment evaluation is application-layer responsibility (may be in V2-007 or quality checking layer). V2-061 provides the field to store results.

### Misbelief Representation

**Misbelief** = Character epistemic state where `aligns_with_fact = False`.

**Critical for**:
- Dramatic irony (reader knows truth, character doesn't)
- Suspense (will character discover the truth?)
- Character development (belief revision arcs)
- Plot twists (character acts on false belief)

**Example**:
```python
# Objective fact (V2-007): Character B is alive
# (committed to Canon as event or entity lifecycle state)

# Character A's misbelief (V2-061)
char_a.knowledge[prop_id] = CharacterKnowledge(
    knower=char_a.entity_id,
    proposition_id=prop_id,  # "Character B is dead"
    knowledge_level="KNOWN",  # A is confident
    acquisition_source="COMMUNICATION",
    source_character=char_c.entity_id,  # C told A this (C lied or was wrong)
    aligns_with_fact=False,  # Misbelief
    confidence=0.95
)
```

**Validation Rule**: System MUST allow misbeliefs without error. A character having `aligns_with_fact=False` is VALID and expected.

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

**CONSOLIDATED**: Misbelief semantics are now fully covered in "Knowledge Semantics" section above.

See "Knowledge Semantics → Truth Alignment" and "Knowledge Semantics → Misbelief Representation" for:
- How to represent misbeliefs (`aligns_with_fact = False`)
- Why misbeliefs are critical for narrative quality
- Validation rules (misbeliefs are valid, not errors)
- Examples of misbelief representation

---

## Provenance

Every `CharacterKnowledge` entry MUST have:
- `acquisition_source` (how acquired) - **REQUIRED**
- Source references appropriate to acquisition type - **REQUIRED WHERE APPLICABLE**
- `acquired_at` (when) - OPTIONAL but recommended

**Purpose**:
- Prevents omniscience (no knowledge without path)
- Enables knowledge validation
- Supports debugging/explanation
- Drives narrative causality

**Source Reference Requirements by Acquisition Type**:

| acquisition_source | source_character | source_ref | basis_ref |
|-------------------|------------------|------------|-----------|
| DIRECT_OBSERVATION | - | OPTIONAL (event ref) | - |
| COMMUNICATION | **REQUIRED** | OPTIONAL (conversation ref) | - |
| DOCUMENT | - | **REQUIRED** (document id/ref) | - |
| INFERENCE | - | OPTIONAL | **REQUIRED** (proposition ids) |
| RUMOR | OPTIONAL | OPTIONAL | - |

**Validation**:
- Missing required source reference → INVALID (reject, not warning)
- Validation enforces provenance completeness
- No "warning-only" mode for missing provenance

**V2-061 Minimum**: Define provenance fields and validation rules.

**NOT in V2-061**: Automatic knowledge propagation (e.g., "A tells B, so B automatically gains knowledge"). This requires V2-007 communication event modeling.

---

## Uncertainty

Characters can be UNCERTAIN about facts.

**Representation**:
- `knowledge_level = "SUSPECTED"` (weak belief, uncertain)
- `confidence < 0.5` in CharacterKnowledge
- Explicitly separate from KNOWN/ordinary-UNKNOWN

**Use Cases**:
- Mystery/suspense genres
- Character investigation arcs
- Gradual revelation
- Partial evidence scenarios

**Example**:
```python
# Character suspects but isn't certain
char.knowledge[prop_id] = CharacterKnowledge(
    knower=char.entity_id,
    proposition_id=prop_id,
    knowledge_level="SUSPECTED",  # Uncertain
    acquisition_source="RUMOR",
    confidence=0.3,  # Low confidence
    aligns_with_fact=None,  # Unknown if true
    ...
)
```

**Creative Freedom**: Characters can act on uncertain knowledge:
- Investigate based on suspicion
- Make decisions under uncertainty
- Take calculated risks
- Guess or assume

This is VALID narrative behavior, not an error condition.

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

All Character entities MUST include explicit `project_id`.

**Isolation Rules**:
- Character from Project A cannot have knowledge of facts in Project B
- Character references across projects are INVALID
- Knowledge provenance cannot cross project boundaries
- All epistemic records inherit character's `project_id`

**Enforcement Mechanism**:

V2-005 EntityId is **opaque** (does NOT carry project scope).

Project isolation is enforced by:
1. **EntityIdentity.project_id** (in V2-005, source of truth)
2. **Character.project_id** (in V2-061, MUST match EntityIdentity.project_id)
3. **EntityRegistry project-scoped queries** (in V2-005)

**Validation**:
```python
# When creating Character from EntityId
identity = entity_registry.get_entity(entity_id)
if identity is None:
    raise ValueError(f"EntityId {entity_id} not found")
if identity.project_id != character.project_id:
    raise ValueError(
        f"Character.project_id ({character.project_id}) must match "
        f"EntityIdentity.project_id ({identity.project_id})"
    )
```

**Cross-Project References**:
All entity references in V2-061 (knower, source_character, proposition subjects/objects) MUST be validated for project ownership:

- `knower` must belong to character's project
- `source_character` (in COMMUNICATION) must belong to same project
- Proposition `subject`/`object` (if EntityId) must belong to same project

**Project Scope Propagation**:
- CharacterKnowledge inherits `project_id` from Character
- Goal/Intent/PlannedAction inherit `project_id` from Character
- Proposition references must be project-scoped

**NO Cross-Project Contamination**:
- UUID collision across projects does NOT imply same entity
- Knowledge acquired in Project A cannot reference entities in Project B
- Even if two projects have "similar" entities, they are completely isolated

---

## Lifecycle

Character lifecycle states:

- `PLANNED`: Defined but not yet active in story
- `ACTIVE`: Currently part of story
- `INACTIVE`: Temporarily not appearing (still alive/existing)
- `DECEASED`: Character has died in story
- `SUPERSEDED`: Character concept replaced/merged

**Validation Rules**:

**Genre-Neutral Core**:
- DECEASED character cannot form new intents/goals (default rule)
- PLANNED character cannot have knowledge of story events (not yet in story)
- SUPERSEDED character cannot be referenced in new content

**Genre-Specific Overrides** (NOT in Core):
Core does NOT embed genre-specific rules like:
- "unless ghost/supernatural"
- "unless reincarnation"
- "unless undead"

These are Genre extension concerns (separate from Core).

**Lifecycle Transitions**:
Allowed transitions depend on story semantics:
- PLANNED → ACTIVE (character enters story)
- ACTIVE → INACTIVE (character leaves temporarily)
- ACTIVE → DECEASED (character dies)
- INACTIVE → ACTIVE (character returns)
- DECEASED → ACTIVE (NOT allowed by default, genre may override)

**Core Principle**: V2-061 Core provides minimal lifecycle semantics. Genre extensions can add:
- Additional states (UNDEAD, SPIRIT, etc.)
- State-specific rules
- Custom transition logic

Do NOT pollute Core with genre-specific conditionals.

---

## V2-005 Boundary

**V2-005 provides (CLOSED, VERIFIED)**:
- `EntityId`, `ProjectId` (opaque stable identifiers)
- `EntityIdentity` (canonical_name, aliases, entity_type)
- `EntityRegistry` (project-scoped resolution)
- Operations: `create_identity`, `rename_identity`, `add_alias`, `remove_alias`, `resolve_alias`

**V2-061 builds on V2-005**:
- Character references `EntityId` (does NOT duplicate canonical_name/aliases)
- Character inherits identity semantics from V2-005
- Character extends Entity with epistemic and intentional state

**Critical Invariant**: V2-005 is the **sole authority** for:
- `canonical_name` (what entity's primary name is)
- `aliases` (alternative names for resolution)
- Entity identity lifecycle (rename, alias add/remove)

**V2-061 Responsibility**:
- What character **knows** about entities (including self and others)
- What character **intends** to do
- Epistemic state (knowledge/belief about propositions)

**No Overlap**: V2-061 does NOT:
- Store canonical_name in Character dataclass
- Store aliases in Character dataclass
- Reimplement identity resolution
- Manage entity naming lifecycle

**Identity Access Pattern**:
```python
# CORRECT: V2-061 references entity via EntityId
character = Character(entity_id=EntityId("..."), ...)

# To get canonical name, query V2-005:
identity = entity_registry.get_entity(character.entity_id)
name = identity.canonical_name

# WRONG: Duplicating identity fields in Character
# character.canonical_name = "张三"  # NO - this is V2-005's authority
```

**Project Isolation Mechanism**:
- `EntityId` is an **opaque identifier** (does NOT carry project scope)
- Project isolation is enforced by:
  1. `EntityIdentity.project_id` (in V2-005)
  2. `Character.project_id` (in V2-061, must match EntityIdentity.project_id)
  3. `EntityRegistry` project-scoped queries (in V2-005)

**V2-061 Project Validation**:
- All `Character` entities MUST include explicit `project_id`
- All epistemic records (CharacterKnowledge) inherit character's `project_id`
- Cross-project entity references are INVALID
- Knowledge provenance cannot cross project boundaries

**Validation Rule**:
```python
# When creating Character, verify project_id matches
identity = entity_registry.get_entity(entity_id)
if identity.project_id != character.project_id:
    raise ValueError("Character project_id must match EntityIdentity project_id")
```

---

## V2-006 Boundary

**V2-006 provides (CLOSED, VERIFIED)**:
- `RelationshipId`, `RelationshipType`, `EntityRelationship`
- `RelationshipRegistry`
- Operations: `create_relationship`, `delete_relationship`, `get_relationships`

**V2-006 Semantics**:
- Directed relationships between entities (no automatic inverse)
- Project-scoped (cross-project isolation)
- Immutable after creation
- API: `create_relationship(source, target, type, project)` generates fresh RelationshipId

**V2-061 uses V2-006**:
- Character relationships are stored in V2-006's RelationshipRegistry
- Character **knowledge about relationships** is V2-061's CharacterKnowledge

**No Overlap**: V2-061 does NOT:
- Create second relationship registry
- Reimplement relationship topology
- Store relationship data in Character

**Example - Objective vs Epistemic**:
```python
# Objective relationship (V2-006 authority)
relationship_registry.add_relationship(
    create_relationship(
        source_entity_id=char_a_id,
        target_entity_id=char_b_id,
        relationship_type=RelationshipType("MARRIED_TO"),
        project_id=project_id
    )
)

# Character C's KNOWLEDGE of relationship (V2-061 authority)
char_c.knowledge[prop_id] = CharacterKnowledge(
    knower=char_c.entity_id,
    proposition_id=prop_id,  # "char_a is married to char_b"
    knowledge_level="BELIEVED",  # C believes it but hasn't verified
    acquisition_source="RUMOR",
    aligns_with_fact=True,  # Belief happens to be correct
    ...
)

# Character D's MISBELIEF about relationship (V2-061 authority)
char_d.knowledge[prop_id_2] = CharacterKnowledge(
    knower=char_d.entity_id,
    proposition_id=prop_id_2,  # "char_a is single"
    knowledge_level="KNOWN",  # D is confident
    acquisition_source="DIRECT_OBSERVATION",  # D thinks they saw evidence
    aligns_with_fact=False,  # Misbelief - A is actually married
    ...
)
```

**Separation of Concerns**:
- V2-006: "A is married to B" (objective relationship exists in story-world)
- V2-061: "Character C believes A is married to B" (epistemic state)
- V2-061: "Character D believes A is single" (epistemic state - misbelief)

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

All V2-061 operations MUST be deterministic given same explicit inputs.

**Deterministic Operations**:
- Creating Character with explicit EntityId and fields → same Character
- Adding CharacterKnowledge with explicit PropositionId → same knowledge state
- Goal lifecycle transition with explicit GoalId and new status → same result
- Serialization/deserialization round-trip → same semantic state

**Sources of Non-Determinism** (NOT in V2-061 control):
- UUID generation (v4 uses random)
- System timestamp generation
- External service calls

**Contract Guarantee**:
Given:
- Explicit IDs (EntityId, PropositionId, GoalId, etc.)
- Explicit timestamp values
- Explicit external inputs
- Same EntityRegistry/RelationshipRegistry state

A V2-061 operation produces the same result every time.

**Example - Non-Deterministic**:
```python
# Different every call (generates new UUID)
char1 = create_character(...)
char2 = create_character(...)
assert char1.entity_id != char2.entity_id  # Different IDs
```

**Example - Deterministic**:
```python
# Same inputs → same result
char1 = Character(
    entity_id=EntityId("550e8400-e29b-41d4-a716-446655440000"),
    project_id=ProjectId("proj_001"),
    lifecycle="ACTIVE",
    knowledge={},
    goals=[],
    intents=[],
    planned_actions=[],
    ...
)

char2 = Character(
    entity_id=EntityId("550e8400-e29b-41d4-a716-446655440000"),
    project_id=ProjectId("proj_001"),
    lifecycle="ACTIVE",
    knowledge={},
    goals=[],
    intents=[],
    planned_actions=[],
    ...
)

assert char1 == char2  # Deterministic equality
```

**Serialization Round-Trip**:
```python
# Must be deterministic
json_str = serialize(character)
restored = deserialize(json_str)
assert restored == character  # Exact equality
```

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
| Character observes event directly | knowledge_level=KNOWN, acquisition_source=DIRECT_OBSERVATION |
| Character told by another | knowledge_level=BELIEVED, acquisition_source=COMMUNICATION, source_character REQUIRED |
| Character reads document | knowledge_level=KNOWN, acquisition_source=DOCUMENT, source_ref REQUIRED |
| Character hears rumor | knowledge_level=SUSPECTED, acquisition_source=RUMOR |
| Character has no path to fact | NO knowledge entry (ordinary UNKNOWN) |

### Misbelief Representation (AC-2)

| Objective Fact | Character Knowledge | System Behavior |
|----------------|---------------------|-----------------|
| A is alive | B believes A is dead | Both stored; B's knowledge has aligns_with_fact=False |
| X betrayed Y | Y believes X is loyal | Y's knowledge has aligns_with_fact=False |
| Event occurred | Character unaware | NO knowledge entry for character |

### Intent vs Occurrence (AC-3)

| Scenario | PlannedAction Status | V2-007 Event Created? |
|----------|----------------------|----------------|
| Character plans to attack | PLANNED | NO |
| Plan executed successfully | OCCURRED | YES |
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
| Character acts on SUSPECTED fact | VALID (uncertainty-based action) |
| Character acts on UNKNOWN fact (no record) | VALID (character can guess/assume) |
| Character has knowledge without acquisition_source | INVALID (provenance required) |
| Cross-project knowledge reference | INVALID (project isolation) |

### Schema Round-Trip (AC-6)

| Input | Round-Trip Preserves? |
|-------|----------------------|
| Legal derived field with value | YES (ADR-002) |
| Base field with value | YES |
| Invalid entity type | REJECT on deserialize |
| Invalid lifecycle | REJECT on deserialize |

### Identity Authority (AC-7)

| Scenario | Expected Behavior |
|----------|-------------------|
| Character.canonical_name field | DOES NOT EXIST (V2-005 authority) |
| Character.aliases field | DOES NOT EXIST (V2-005 authority) |
| Character.entity_id | References V2-005 EntityId |
| Get character name | Query EntityRegistry.get_entity(entity_id).canonical_name |
| Character rename | V2-005 operation; V2-061 records unaffected (use EntityId) |

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

**Question**: Which Character fields are base (authoritative, stored), which are derived/computed (can be recalculated)?

**Impact on V2-061**:
- Defines serialization strategy
- Affects round-trip preservation requirements
- Influences schema design and cache semantics

**Core Principle** (to be formalized in ADR-002):

**Base State** (authoritative):
- Must be serialized
- Cannot be recalculated from other fields
- Source of truth
- Examples: `entity_id`, `project_id`, `lifecycle`, `knowledge` dict, `goals`, `intents`, `planned_actions`

**Derived State** (computed):
- CAN be recalculated from base state
- May be cached for performance
- NOT authoritative (if derived conflicts with base, base wins)
- Examples: `active_goals` (filter of `goals` where status=ACTIVE), `misbeliefs` (filter of `knowledge` where aligns_with_fact=False)

**Cache** (performance optimization):
- Derived state that's expensive to compute
- Can be discarded and regenerated
- Must NOT affect semantic equality
- Must be clearly marked as cache

**Round-Trip Strategy**:
1. **Base fields**: Always serialize, always deserialize
2. **Derived fields with non-default values**:
   - Serialize if present (performance optimization - avoid recompute)
   - If absent on deserialize, recompute from base
   - Round-trip MUST preserve semantic state (not necessarily byte-identical)
3. **Cache fields**: Optional serialization, never affects equality

**Critical Requirement**:
```python
# Round-trip must preserve semantic state
char1 = Character(...)
serialized = to_json(char1)
char2 = from_json(serialized)

# Semantic equality (may recompute derived fields)
assert char1.entity_id == char2.entity_id
assert char1.knowledge == char2.knowledge  # Base state identical
assert char1.active_goals() == char2.active_goals()  # Derived state equivalent

# Byte-identical serialization NOT required
# (derived fields may or may not be serialized)
```

**Scope of ADR-002 Decision**:
1. Explicit list of base vs derived vs cache fields for Character
2. Serialization rules for each category
3. Equality semantics (which fields participate in equality check)
4. Schema strategy (which fields appear in character.schema.json)

**Recommendation for ADR-002** (draft, pending formal ratification):

**Base Fields** (always serialized):
```python
entity_id: EntityId          # Identity
project_id: ProjectId        # Scope
lifecycle: Literal[...]      # State
knowledge: dict[PropositionId, CharacterKnowledge]  # Epistemic state
goals: list[Goal]            # Intentional state
intents: list[Intent]
planned_actions: list[PlannedAction]
created_at: datetime         # Metadata
updated_at: datetime
authority: str
provenance: dict
```

**Derived Fields** (computed from base, may cache):
```python
@property
def active_goals(self) -> list[Goal]:
    """Goals where status == ACTIVE."""
    return [g for g in self.goals if g.status == "ACTIVE"]

@property
def misbeliefs(self) -> list[CharacterKnowledge]:
    """Knowledge where aligns_with_fact == False."""
    return [k for k in self.knowledge.values() if k.aligns_with_fact is False]

@property
def knowledge_count(self) -> int:
    """Total epistemic records."""
    return len(self.knowledge)
```

**NOT in Character** (V2-005 authority):
```python
# canonical_name: NO - query EntityRegistry
# aliases: NO - query EntityRegistry
```

**Formal ADR-002 Decision Required Before Implementation Authorization**.

Current ADR-002 machine state: `status=REQUIRED, decision_record=null`

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
**Mitigation**:
- Characters CAN act on uncertain knowledge (SUSPECTED)
- Characters CAN guess/assume (no record = ordinary UNKNOWN, still valid basis for action)
- Provenance required = prevents omniscience, NOT prevents creative character behavior
- Focus on preventing knowledge leakage, not constraining character agency

---

## Adversarial Test Cases

The following cases MUST be correctly handled by V2-061 implementation. These are not edge cases - they are core narrative scenarios that the system exists to support.

### Case 1: Misbelief About Identity

**Scenario**:
- Objective fact: The murderer is Character B (EntityId `char_b`)
- Character A believes the murderer is Character C (EntityId `char_c`)

**V2-061 Representation**:
```python
# Character A's misbelief
char_a.knowledge[prop_murder] = CharacterKnowledge(
    knower=char_a.entity_id,
    proposition_id=prop_murder,  # "char_c is the murderer"
    knowledge_level="BELIEVED",
    acquisition_source="INFERENCE",
    basis_ref=[prop_motive, prop_opportunity],  # A reasoned incorrectly
    aligns_with_fact=False,  # Misbelief - it's actually char_b
    confidence=0.8
)
```

**Validation**: System must allow A's belief and objective fact to coexist without conflict or error.

### Case 2: Reader Knowledge vs Character Knowledge

**Scenario**:
- Reader knows B is the murderer (narrator revealed it)
- Character A does not know

**V2-061 Representation**:
```python
# NO epistemic record for char_a about B being murderer
# char_a.knowledge does NOT contain entry for "B is murderer"

# This is ordinary UNKNOWN - absence of record
```

**Anti-Pattern Prevention**: System MUST NOT:
- Automatically create knowledge entry for A because reader knows
- Provide "AUTHORITATIVE_DISCLOSURE" bypass
- Leak narrator knowledge into character epistemic state

**Test**: Verify narrator can reveal to reader WITHOUT creating character knowledge record.

### Case 3: Rumor vs Reality

**Scenario**:
- Character A hears rumor: "B is dead"
- Objective fact: B is alive (EntityIdentity lifecycle = ACTIVE)

**V2-061 Representation**:
```python
# A's belief from rumor
char_a.knowledge[prop_b_dead] = CharacterKnowledge(
    knower=char_a.entity_id,
    proposition_id=prop_b_dead,  # "char_b is dead"
    knowledge_level="BELIEVED",
    acquisition_source="RUMOR",
    source_character=None,  # Unknown original source
    aligns_with_fact=False,  # B is actually alive
    confidence=0.6
)

# Objective fact (V2-005 or lifecycle state)
char_b.lifecycle = "ACTIVE"  # B is alive
```

**Validation**: Rumor-based misbelief coexists with objective lifecycle state.

### Case 4: Acting on Suspicion

**Scenario**:
- Character A suspects B betrayed them
- A has no proof, just suspicion
- A decides to take action based on suspicion

**V2-061 Representation**:
```python
# A's suspicion (weak epistemic state)
char_a.knowledge[prop_betrayal] = CharacterKnowledge(
    knower=char_a.entity_id,
    proposition_id=prop_betrayal,  # "char_b betrayed me"
    knowledge_level="SUSPECTED",  # Uncertain
    acquisition_source="INFERENCE",
    basis_ref=[prop_unusual_behavior],
    aligns_with_fact=None,  # Unknown if true
    confidence=0.4  # Low confidence
)

# A forms intent based on suspicion (VALID)
intent = Intent(
    intent_id=IntentId("..."),
    character=char_a.entity_id,
    description="Investigate B's activities",
    ...
)
```

**Creative Freedom**: Character CAN act on SUSPECTED knowledge. This is valid narrative behavior, not an error.

**Anti-Pattern Prevention**: System MUST NOT reject character actions based on uncertain epistemic state.

### Case 5: Plan vs Execution

**Scenario**:
- Character A plans to kill B tomorrow
- Plan has NOT been executed yet

**V2-061 Representation**:
```python
# A's planned action (intent, not fact)
planned = PlannedAction(
    action_id=PlannedActionId("..."),
    character=char_a.entity_id,
    action_description="Kill char_b at dawn",
    status="PLANNED",  # NOT occurred
    occurred_event_ref=None,  # No event yet
    ...
)
```

**Critical Invariant**: `status="PLANNED"` means event has NOT occurred.

**Anti-Pattern Prevention**:
- System MUST NOT treat planned action as occurred event
- System MUST NOT create V2-007 Event when action is PLANNED
- System MUST NOT update Canon state based on plan

**Test**: Verify planned action does NOT affect Canon entity states or create events.

### Case 6: Belief Revision

**Scenario**:
- Day 1: A believes "C is trustworthy"
- Day 3: A discovers C betrayed them
- A revises belief to "C is untrustworthy"

**V2-061 Representation**:
```python
# Initial belief (day 1)
belief_v1 = CharacterKnowledge(
    knower=char_a.entity_id,
    proposition_id=prop_trust,  # "char_c is trustworthy"
    knowledge_level="BELIEVED",
    acquired_at=datetime(2024, 1, 1),
    aligns_with_fact=False,  # Was wrong
    ...
)

# Revised belief (day 3) - NEW proposition
belief_v2 = CharacterKnowledge(
    knower=char_a.entity_id,
    proposition_id=prop_distrust,  # "char_c is untrustworthy"
    knowledge_level="KNOWN",
    acquired_at=datetime(2024, 1, 3),
    acquisition_source="DIRECT_OBSERVATION",  # Witnessed betrayal
    aligns_with_fact=True,
    ...
)
```

**Requirements**:
- Historical belief (belief_v1) should be retained or superseded (not destroyed)
- Belief revision is explicit operation, not silent overwrite
- System can track belief history (for narrative explanation)

**V2-008 Integration**: Belief revision generates NarrativeDelta like `CharacterRevisedBelief`.

### Case 7: Cross-Project Isolation

**Scenario**:
- Project A: Character Alice (EntityId `alice_a`)
- Project B: Character Alice (EntityId `alice_b`, different project)
- Both have EntityIdentity.canonical_name = "Alice"

**V2-061 Representation**:
```python
# Project A
char_alice_a = Character(
    entity_id=EntityId("alice_a"),
    project_id=ProjectId("project_a"),
    ...
)

# Project B
char_alice_b = Character(
    entity_id=EntityId("alice_b"),
    project_id=ProjectId("project_b"),
    ...
)
```

**Isolation Requirements**:
- alice_a cannot have knowledge about entities in project_b
- alice_b cannot have knowledge about entities in project_a
- Cross-project EntityId reference is INVALID

**Test**: Verify validation rejects cross-project knowledge provenance.

### Case 8: Character Rename

**Scenario**:
- Character starts as "张三"
- Character is renamed to "张三丰"
- Existing knowledge records must still reference same character

**V2-005 Authority**:
```python
# V2-005 handles rename
identity_v1 = EntityIdentity(
    entity_id=EntityId("char_123"),
    canonical_name="张三",
    aliases=frozenset(),
    ...
)

# After rename (V2-005 operation)
identity_v2 = rename_identity(identity_v1, "张三丰")
# identity_v2.entity_id == "char_123"  # SAME ID
# identity_v2.canonical_name == "张三丰"
# identity_v2.aliases == {"张三"}  # Old name preserved
```

**V2-061 Behavior**:
```python
# Character references EntityId (stable)
character = Character(
    entity_id=EntityId("char_123"),  # NEVER CHANGES
    project_id=ProjectId("proj"),
    ...
)

# Knowledge records use EntityId
knowledge = CharacterKnowledge(
    knower=EntityId("char_123"),  # Still valid after rename
    ...
)
```

**Invariant**: Character rename (V2-005 operation) does NOT break V2-061 knowledge records because they reference stable EntityId, not canonical_name.

**Anti-Pattern Prevention**: V2-061 MUST NOT duplicate canonical_name, preventing desync with V2-005.

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

