"""Reproduce a Gateway protocol probe; no database, credential or network I/O.

The adopted story is real development input. The unpersisted component CanonView
below is synthetic and never evidence of an actual Canon commit/authority event.
Generated Context/request snapshots belong in dist, not repository source.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from hashlib import sha256
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
from anovel.gateway.models import KIMI_CHAT_ENDPOINT, GatewayRequest, ModelPolicy
from anovel.gateway.provider import strict_json
from anovel.planning.models import StoryFixture
from anovel.planning.versions import PlanHistory, PlanVersion

ROOT = Path(__file__).resolve().parents[5]
LEGACY_RUN_ID = "v2019-openai-probe-20261116"


def prepare(
    *, policy: ModelPolicy | None = None, run_id: str = LEGACY_RUN_ID
) -> GatewayRequest:
    fixture = StoryFixture.from_dict(
        json.loads((ROOT / "specs/fixtures/stories/urban.json").read_text())
    )
    if policy is None:
        policy = ModelPolicy.from_dict(
            json.loads((ROOT / "model-policy.yaml").read_text())
        )
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
        run_id,
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


def _prepare_kimi_policy(path: Path) -> tuple[ModelPolicy, str]:
    try:
        raw = path.read_bytes()
        policy = ModelPolicy.from_dict(strict_json(raw))
    except (OSError, ValueError) as error:
        raise ValueError("A readable, valid Kimi policy file is required") from error
    if policy.test_mode or policy.endpoint != KIMI_CHAT_ENDPOINT:
        raise ValueError("The Kimi probe requires the fixed non-test endpoint")
    if policy.max_output_tokens > 1024 or policy.timeout_seconds > 30:
        raise ValueError("The policy exceeds the first-probe output or timeout limit")
    if policy.input_rate <= 0 or policy.output_rate <= 0:
        raise ValueError("The policy must supply positive frozen rates")
    if datetime.fromisoformat(policy.price_expires_at) <= datetime.now(UTC):
        raise ValueError("The policy has expired")
    return policy, sha256(raw).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--policy-file", type=Path, help="Explicit Kimi policy file")
    parser.add_argument("--run-id", help="Fresh run identity for the Kimi request")
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / "dist"):
        parser.error("Generated request snapshots must remain in project dist")
    if args.policy_file is None:
        if args.run_id is not None:
            parser.error("--run-id requires --policy-file")
        request = prepare()
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x") as stream:
            json.dump(request.to_dict(), stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        extra = {}
    else:
        if not args.run_id or not args.run_id.strip() or args.run_id == LEGACY_RUN_ID:
            parser.error("--policy-file requires a new --run-id")
        if args.output.is_symlink():
            parser.error("The Kimi request destination must not be a symlink")
        if output.is_relative_to(ROOT / "dist/validation"):
            parser.error("Prepare Kimi inputs outside historical dist/validation")
        try:
            policy, policy_file_sha256 = _prepare_kimi_policy(args.policy_file)
        except ValueError as error:
            parser.error(str(error))
        request = prepare(policy=policy, run_id=args.run_id)
        raw = request.to_bytes()
        output.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        descriptor = os.open(
            output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
        )
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
        extra = {
            "provider": "KIMI",
            "policy_hash": policy.content_hash,
            "policy_file_sha256": policy_file_sha256,
            "request_file_sha256": sha256(raw).hexdigest(),
            "live_authority": False,
        }
    print(
        json.dumps(
            {
                "status": "PREPARED_NO_NETWORK",
                "request_hash": request.content_hash,
                "context_bytes": len(request.context.model_bytes),
                "live_calls": 0,
                **extra,
            }
        )
    )


if __name__ == "__main__":
    main()
