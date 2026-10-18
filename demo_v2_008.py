"""Preview a fictional chapter's finite fact changes without publishing them."""

import json

from anovel.domain.delta import (
    FactBaseline,
    FactPath,
    MarkUnknown,
    NarrativeDelta,
    NoChange,
    OperationMeta,
    Precondition,
    ProseEvidence,
    RetractFact,
    SetFact,
    preview_delta,
)
from anovel.domain.events import NarrativePosition
from anovel.domain.identity import EntityId
from anovel.domain.knowledge import Proposition, WorldFact


def run_demo() -> dict[str, object]:
    def eid(name: str) -> EntityId:
        return EntityId("key_story", name)

    fact = WorldFact(
        eid("key_location"),
        Proposition(eid("key"), "located_at", "east_warehouse"),
        "initial:inventory",
    )
    baseline = FactBaseline.from_world_facts("key_story", "main", "parent_1", (fact,))
    source = eid("chapter_2_text")
    grant = "local-demo:proposal-check"
    metadata = OperationMeta(
        eid("move_key"),
        fact.id,
        FactPath.VALUE,
        Precondition.from_snapshot(baseline.get(fact.id)),
        ProseEvidence(source, NarrativePosition(2, 1), "chapter-2:paragraph-3"),
        grant,
    )

    def proposed(
        operation: SetFact | MarkUnknown | RetractFact | NoChange,
    ) -> NarrativeDelta:
        return NarrativeDelta(
            eid("chapter_2_delta"), "main", "parent_1", source, (operation,)
        )

    def preview(delta: NarrativeDelta, base: FactBaseline = baseline):
        return preview_delta(
            base, delta, source_id=source, authorization_refs=frozenset({grant})
        )

    delta = proposed(SetFact(metadata, "west_warehouse"))
    restored = NarrativeDelta.from_dict(json.loads(json.dumps(delta.to_dict())))
    result = preview(restored)
    unknown = preview(proposed(MarkUnknown(metadata))).candidate.get(fact.id)
    retracted = preview(proposed(RetractFact(metadata))).candidate.get(fact.id)
    unchanged = preview(proposed(NoChange(metadata)))
    rejected = {}
    for label, operation in (("wrong_type", proposed(SetFact(metadata, True))),):
        try:
            preview(operation)
        except ValueError:
            rejected[label] = True
        else:
            raise AssertionError(label + " was accepted")
    try:
        preview(delta, result.candidate)
    except ValueError:
        rejected["stale_replay"] = True
    else:
        raise AssertionError("Old precondition was accepted")
    return {
        "original_fact": baseline.get(fact.id).state.to_dict(),
        "candidate_fact": result.candidate.get(fact.id).state.to_dict(),
        "unknown": unknown.state.to_dict(),
        "retracted": retracted.state.to_dict(),
        "retracted_seed_preserved": retracted.seed_fact == fact,
        "no_change_preserves_baseline": unchanged.candidate == baseline
        and unchanged.changes == (),
        "rejected": rejected,
        "json_roundtrip": restored == delta,
        "scope": "fictional local preview; no Canon commit, Permit or prose authenticity claim",
    }


if __name__ == "__main__":
    print(json.dumps(run_demo(), ensure_ascii=False, indent=2))
