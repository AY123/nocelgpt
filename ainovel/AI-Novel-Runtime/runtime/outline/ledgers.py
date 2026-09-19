from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class SemanticLedgerEntry:
    entry_id: str
    text: str
    source_chapter: int | None = None
    status: str | None = None
    confidence: float | None = None
    owner: str | None = None
    location: str | None = None
    severity: str | None = None
    recovery_status: str | None = None
    parties: list[str] = field(default_factory=list)
    expectation: str | None = None
    due_by: str | None = None
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SemanticLedger:
    knowledge: list[SemanticLedgerEntry]
    ability: list[SemanticLedgerEntry]
    injury: list[SemanticLedgerEntry]
    items: list[SemanticLedgerEntry]
    relationship_expectation: list[SemanticLedgerEntry]
    promise: list[SemanticLedgerEntry]
    conflict_detection: dict[str, Any]
    comparison_only: bool = True
    gating: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "knowledge": [x.to_dict() for x in self.knowledge],
            "ability": [x.to_dict() for x in self.ability],
            "injury": [x.to_dict() for x in self.injury],
            "items": [x.to_dict() for x in self.items],
            "relationship_expectation": [x.to_dict() for x in self.relationship_expectation],
            "promise": [x.to_dict() for x in self.promise],
            "conflict_detection": self.conflict_detection,
            "comparison_only": self.comparison_only,
            "gating": self.gating,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class ChapterFunctionSignature:
    chapter_no: int
    function_type: str
    promise: str
    setup: str
    payoff: str
    tension: str
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PromiseLedgerEntry:
    promise_id: str
    chapter_no: int
    status: str
    promise_text: str
    established_by: str | None = None
    resolved_by: str | None = None
    window: str | None = None
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CharacterArcEntry:
    character: str
    arc_axis: str
    starting_state: str
    ending_state: str
    progression: str
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NarrativeEconomyEntry:
    chapter_no: int
    introduced: list[str]
    paid_off: list[str]
    deferred: list[str]
    debt: int
    balance_note: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CI_M4Ledger:
    chapter_functions: list[ChapterFunctionSignature]
    promises: list[PromiseLedgerEntry]
    character_arcs: list[CharacterArcEntry]
    narrative_economy: list[NarrativeEconomyEntry]
    comparison_only: bool = True
    gating: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "chapter_functions": [x.to_dict() for x in self.chapter_functions],
            "promises": [x.to_dict() for x in self.promises],
            "character_arcs": [x.to_dict() for x in self.character_arcs],
            "narrative_economy": [x.to_dict() for x in self.narrative_economy],
            "comparison_only": self.comparison_only,
            "gating": self.gating,
            "metadata": self.metadata,
        }


def build_semantic_ledger(outline: Mapping[str, Any]) -> SemanticLedger:
    chapters = list(outline.get("first_30_chapters") or [])
    characters = list(outline.get("characters") or [])
    protagonist_name = str((characters[0] if characters else {}).get("name") or "主角")

    knowledge = [
        SemanticLedgerEntry(entry_id=f"K-{i:02d}", text=str(item.get("goal") or ""), source_chapter=int(item.get("chapter_no") or 0), confidence=0.8, evidence=[str(item.get("end_hook") or "")])
        for i, item in enumerate(chapters, start=1)
        if str(item.get("goal") or "")
    ]
    ability = [
        SemanticLedgerEntry(entry_id=f"A-{i:02d}", text=str(char.get("arc") or ""), source_chapter=None, status="active", evidence=[str(char.get("name") or "")])
        for i, char in enumerate(characters, start=1)
        if str(char.get("role") or "") == "protagonist"
    ]
    injury = []
    items = []
    relationship_expectation = [
        SemanticLedgerEntry(entry_id=f"R-{i:02d}", text=str(char.get("motivation") or ""), source_chapter=None, status="active", parties=[protagonist_name, str(char.get("name") or "")], expectation=str(char.get("arc") or ""), evidence=[str(char.get("role") or "")])
        for i, char in enumerate(characters, start=1)
        if str(char.get("name") or "") and str(char.get("role") or "") != "protagonist"
    ]
    promise = [
        SemanticLedgerEntry(entry_id=f"P-{int(item.get('chapter_no') or 0):02d}", text=str(item.get("reward_if_any") or item.get("goal") or ""), source_chapter=int(item.get("chapter_no") or 0), status=("resolved" if str(item.get("reward_if_any") or "").strip() and int(item.get("chapter_no") or 0) % 3 == 0 else "pending"), due_by=f"ch{int(item.get('chapter_no') or 0):02d}", evidence=[str(item.get("end_hook") or "")])
        for item in chapters
        if int(item.get("chapter_no") or 0) > 0
    ]
    return SemanticLedger(
        knowledge=knowledge,
        ability=ability,
        injury=injury,
        items=items,
        relationship_expectation=relationship_expectation,
        promise=promise,
        conflict_detection={"enabled": True, "outputs": ["conflict_flag", "conflict_type", "evidence"], "conflict_types": ["knowledge", "ability", "injury", "items", "relationship_expectation", "promise"]},
        metadata={"chapter_count": len(chapters), "protagonist": protagonist_name},
    )


def build_ci_m4_ledger(outline: Mapping[str, Any]) -> CI_M4Ledger:
    chapters = list(outline.get("first_30_chapters") or [])
    characters = list(outline.get("characters") or [])
    protagonist_name = str((characters[0] if characters else {}).get("name") or "主角")
    desire = str((outline.get("protagonist_engine") or {}).get("desire") or "核心目标")
    flaw = str((outline.get("protagonist_engine") or {}).get("flaw") or "核心缺口")

    # --- Chapter Function Signatures ---
    chapter_functions: list[ChapterFunctionSignature] = []
    for item in chapters:
        chapter_no = int(item.get("chapter_no") or 0)
        goal = str(item.get("goal") or "")
        hook = str(item.get("end_hook") or "")
        reward = str(item.get("reward_if_any") or "")
        function_type = "setup" if chapter_no in (1, 2) else "payoff" if reward else "escalation"
        chapter_functions.append(
            ChapterFunctionSignature(
                chapter_no=chapter_no,
                function_type=function_type,
                promise=reward or desire,
                setup=goal,
                payoff=hook,
                tension=str(item.get("escalation") or ""),
                evidence=[f"chapter:{chapter_no}", goal, hook],
            )
        )

    # --- Promise Ledger ---
    promises: list[PromiseLedgerEntry] = []
    for item in chapters:
        chapter_no = int(item.get("chapter_no") or 0)
        goal = str(item.get("goal") or "")
        hook = str(item.get("end_hook") or "")
        reward = str(item.get("reward_if_any") or "")
        promise_id = f"P-{chapter_no:02d}"
        if reward:
            status = "resolved" if chapter_no % 3 == 0 else "pending"
        elif chapter_no > 10 and chapter_no % 5 == 0:
            status = "overdue"
        else:
            status = "pending"
        promises.append(
            PromiseLedgerEntry(
                promise_id=promise_id,
                chapter_no=chapter_no,
                status=status,
                promise_text=reward or desire,
                established_by=goal or None,
                resolved_by=hook if reward else None,
                window=f"ch{chapter_no:02d}",
                evidence=[goal, hook, reward] if reward else [goal, hook],
            )
        )

    # --- Character Arc Ledger (all characters, not just protagonist) ---
    character_arcs: list[CharacterArcEntry] = []
    for char in characters:
        name = str(char.get("name") or "")
        if not name:
            continue
        role = str(char.get("role") or "")
        arc_text = str(char.get("arc") or "")
        motivation = str(char.get("motivation") or "")
        if role == "protagonist":
            arc_axis = "flaw_to_desire"
            starting_state = flaw
            ending_state = desire
            progression = arc_text or "chapters 1-30 gradually tighten the gap between flaw and desire"
        elif role == "rival":
            arc_axis = "opposition_to_reckoning"
            starting_state = motivation or "维护旧秩序"
            ending_state = "真相叛逃者" if "叛" in arc_text else "重新评估主角"
            progression = arc_text or "从对抗到理解或背叛"
        elif role == "mentor":
            arc_axis = "secrecy_to_confession"
            starting_state = "守秘"
            ending_state = "赎罪" if "赎" in motivation else "坦诚"
            progression = arc_text or "从守秘到面对旧错"
        else:
            arc_axis = "introduction_to_resolution"
            starting_state = motivation or "未知"
            ending_state = arc_text or "成长"
            progression = arc_text or "从登场到完成功能"
        character_arcs.append(
            CharacterArcEntry(
                character=name,
                arc_axis=arc_axis,
                starting_state=starting_state,
                ending_state=ending_state,
                progression=progression,
                evidence=[f"chapter:{c.get('chapter_no')}" for c in chapters[:5]],
            )
        )
    # Guarantee at least the protagonist arc even if characters list is empty
    if not character_arcs:
        character_arcs.append(
            CharacterArcEntry(
                character=protagonist_name,
                arc_axis="flaw_to_desire",
                starting_state=flaw,
                ending_state=desire,
                progression="chapters 1-30 gradually tighten the gap between flaw and desire",
                evidence=[f"chapter:{c.get('chapter_no')}" for c in chapters[:5]],
            )
        )

    # --- Narrative Economy Ledger ---
    economy: list[NarrativeEconomyEntry] = []
    open_promises: list[str] = []
    for item in chapters:
        chapter_no = int(item.get("chapter_no") or 0)
        goal = str(item.get("goal") or "")
        hook = str(item.get("end_hook") or "")
        reward = str(item.get("reward_if_any") or "")
        promise_id = f"P-{chapter_no:02d}"
        if chapter_no in (1, 5, 10, 15, 20, 25):
            open_promises.append(promise_id)
        if chapter_no in (3, 10, 20, 30):
            open_promises = [pid for pid in open_promises if pid != promise_id]
        introduced = [reward] if reward else []
        paid_off = [hook] if reward else []
        economy.append(
            NarrativeEconomyEntry(
                chapter_no=chapter_no,
                introduced=introduced,
                paid_off=paid_off,
                deferred=list(open_promises[-3:]),
                debt=max(0, len(open_promises) - 1),
                balance_note=f"{protagonist_name} 向「{desire}」推进，背负「{flaw}」",
            )
        )

    return CI_M4Ledger(
        chapter_functions=chapter_functions,
        promises=promises,
        character_arcs=character_arcs,
        narrative_economy=economy,
        metadata={
            "chapter_count": len(chapters),
            "protagonist": protagonist_name,
            "character_count": len(character_arcs),
            "promise_count": len(promises),
            "resolved_count": sum(1 for p in promises if p.status == "resolved"),
            "overdue_count": sum(1 for p in promises if p.status == "overdue"),
            "pending_count": sum(1 for p in promises if p.status == "pending"),
        },
    )
