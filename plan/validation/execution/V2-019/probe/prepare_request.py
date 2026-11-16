"""Reproduce a Gateway protocol probe; no database, credential or network I/O.

The adopted story is real development input. The unpersisted component CanonView
below is synthetic and never evidence of an actual Canon commit/authority event.
Generated Context/request snapshots belong in dist, not repository source.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from anovel.canon.identity import canonical_bytes
from anovel.canon.models import CommitReceipt, StoredRoot
from anovel.context.compiler import compile_context
from anovel.context.models import (
    ContextBudget,
    ContextRequest,
    ContextRole,
    FrozenContextInputs,
)
from anovel.contracts.compiler import compile_contract
from anovel.contracts.models import CanonView
from anovel.domain.delta import FactBaseline
from anovel.domain.identity import EntityId
from anovel.gateway.models import GatewayRequest, ModelPolicy
from anovel.planning.models import StoryFixture
from anovel.planning.versions import PlanHistory, PlanVersion

ROOT = Path(__file__).resolve().parents[5]


def prepare() -> GatewayRequest:
    fixture = StoryFixture.from_dict(
        json.loads((ROOT / "specs/fixtures/stories/urban.json").read_text())
    )
    policy = ModelPolicy.from_dict(json.loads((ROOT / "model-policy.yaml").read_text()))
    history = PlanHistory(
        (
            PlanVersion(
                EntityId(fixture.project, "context-plan"),
                1,
                None,
                fixture.vision,
                fixture.content_hash,
            ),
        )
    )
    parent = "sha256:" + "a" * 64
    receipt = CommitReceipt(
        fixture.project,
        "main",
        "context-component-root",
        parent,
        "b" * 64,
        "2026-11-15T00:00:00.000000Z",
    )
    root = StoredRoot(
        receipt, fixture.root_seed, b"explicit-component-source", b"component-authority"
    )
    baseline = FactBaseline.from_world_facts(
        fixture.project,
        "main",
        parent,
        fixture.root_seed.facts,
        extensions=fixture.root_seed.extensions,
    )
    contract = compile_contract(
        history,
        fixture.vision.chapters[0].id,
        fixture,
        CanonView(root, baseline, None, 1),
    )
    if not contract.ok or contract.contract is None:
        raise ValueError("Component contract did not compile")
    context = compile_context(
        FrozenContextInputs.from_contract(
            contract.contract,
            ContextRequest(
                fixture.project,
                "main",
                parent,
                contract.contract.content_hash,
                ContextRole.WRITER,
                ContextBudget(100000),
            ),
        )
    )
    if not context.ok or context.artifact is None:
        raise ValueError("Role-safe component context did not compile")
    return GatewayRequest(
        fixture.project,
        "main",
        "v2019-openai-probe-20261116",
        "protocol-scene-1",
        context.artifact,
        "这是模型网关协议探针，不是正式章节。仅依据所给角色安全上下文，返回JSON对象：text为100至200字中文场景片段。不要将作者意图当作已发生事实，不得补充隐藏真相或改变世界规则。",
        "gateway-protocol-probe-v1",
        canonical_bytes(
            {
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
                "additionalProperties": False,
            }
        ),
        (policy,),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    request = prepare()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / "dist"):
        parser.error("Generated request snapshots must remain in project dist")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x") as stream:
        json.dump(request.to_dict(), stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(
        json.dumps(
            {
                "status": "PREPARED_NO_NETWORK",
                "request_hash": request.content_hash,
                "context_bytes": len(request.context.model_bytes),
                "live_calls": 0,
            }
        )
    )


if __name__ == "__main__":
    main()
