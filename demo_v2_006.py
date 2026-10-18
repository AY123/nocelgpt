"""Run the local key-location example; no model, database or Canon writes."""

from __future__ import annotations

import json

from anovel.domain.character import Character
from anovel.domain.identity import EntityId
from anovel.domain.knowledge import (
    Belief,
    Goal,
    GoalStatus,
    Intent,
    KnowledgeState,
    Observation,
    Proposition,
    WorldFact,
)


def main() -> None:
    def eid(name: str) -> EntityId:
        return EntityId("demo_book", name)

    lin = Character(eid("lin"), "林岚")
    zhou = Character(eid("zhou"), "周宁")
    state = KnowledgeState("demo_book", (lin, zhou))
    fact = WorldFact(
        eid("key_location"),
        Proposition(eid("key"), "located_at", "东库"),
        "chapter-1:实际盘点",
    )
    mistaken = Belief(
        eid("rumour"),
        zhou.id,
        Proposition(eid("key"), "located_at", "西库"),
        "chapter-1:未核实传闻",
        confidence=0.8,
    )
    state.add_fact(fact)
    state.add_belief(mistaken)
    before = state.query(lin.id, fact.proposition).value
    original_facts = state.facts
    goal = Goal(eid("rescue"), zhou.id, "救出被困者", status=GoalStatus.ACTIVE)
    state.add_goal(goal)
    state.add_intent(
        Intent(
            eid("fetch"),
            zhou.id,
            goal.id,
            "去西库取钥匙",
            (mistaken.id,),
            expected_cost="可能暴露行踪",
        )
    )
    unchanged_by_plan = state.facts == original_facts
    observation = Observation(
        eid("lin_observed"), fact.id, frozenset({lin.id}), "chapter-2:林岚亲眼看到钥匙"
    )
    state.add_observation(observation)
    state.learn(lin.id, fact.id, observation.id)
    restored = KnowledgeState.from_dict(json.loads(json.dumps(state.to_dict())))
    assert restored.to_dict() == state.to_dict()
    assert unchanged_by_plan
    print(
        json.dumps(
            {
                "客观钥匙位置": fact.proposition.value,
                "林岚观察前": before,
                "林岚观察后": state.query(lin.id, fact.proposition).value,
                "周宁误信位置": mistaken.proposition.value,
                "周宁对误信的认知": state.query(zhou.id, mistaken.proposition).value,
                "周宁仍未获知东库": state.query(zhou.id, fact.proposition).value,
                "周宁计划": state.intents[0].action,
                "计划没有移动钥匙": unchanged_by_plan,
                "完整JSON往返": True,
                "运行范围": "纯内存领域演示，未生成小说、未调用模型或数据库",
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
