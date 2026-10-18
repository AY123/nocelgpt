"""Run the local Event/Timeline/Promise example; no DB, Provider or Canon writes."""

import json

from anovel.domain.events import (
    Event,
    NarrativePosition,
    Occurrence,
    StoryTime,
    Timeline,
)
from anovel.domain.identity import EntityId
from anovel.domain.promises import Promise, PromiseWindow


def run_demo() -> dict[str, object]:
    def eid(name: str) -> EntityId:
        return EntityId("key_story", name)

    revelation = Event(
        eid("key_revealed"),
        "REVELATION",
        NarrativePosition(2, 1),
        StoryTime.exact(20),
        Occurrence.OCCURRED,
        evidence_ref="chapter-2:reader-sees-east-warehouse",
        description="读者发现钥匙在东库",
    )
    flashback = Event(
        eid("key_hidden"),
        "HIDE",
        NarrativePosition(2, 2),
        StoryTime.exact(-5),
        Occurrence.OCCURRED,
        evidence_ref="chapter-2:flashback",
        description="插叙：钥匙此前已藏入东库",
    )
    uncertain = Event(
        eid("claimed_rescue"),
        "RESCUE",
        NarrativePosition(3, 1),
        StoryTime.unknown(),
        Occurrence.UNKNOWN,
        evidence_ref="chapter-3:unverified-rumour",
        description="救援成功尚未证实",
    )
    timeline = Timeline("key_story", (uncertain, flashback, revelation))
    promise = Promise(
        eid("key_promise"),
        "第二章解释钥匙去向",
        NarrativePosition(1, 1),
        PromiseWindow.between(NarrativePosition(2, 1), NarrativePosition(2, 3)),
        evidence_ref="chapter-1:promise",
    )
    paid = promise.pay_off(timeline, revelation.id, "reader-review:location-revealed")
    restored = Promise.from_dict(
        json.loads(json.dumps(paid.to_dict())), timeline=timeline
    )
    try:
        promise.pay_off(timeline, uncertain.id, "reader-review:unverified")
    except ValueError:
        unknown_payoff = "REJECTED"
    else:
        raise AssertionError("Unknown occurrence was accepted as payoff")
    return {
        "narration_order": [str(e.id) for e in timeline.narration_order()],
        "story_order": [str(e.id) for e in timeline.story_order()],
        "window_result": paid.window_result(revelation.narrative_position).value,
        "promise_status": restored.status.value,
        "original_promise_status": promise.status.value,
        "unknown_event_payoff": unknown_payoff,
        "json_roundtrip": restored == paid,
        "scope": "local structural contracts; no prose authenticity or Canon commit",
    }


if __name__ == "__main__":
    print(json.dumps(run_demo(), ensure_ascii=False, indent=2))
