#!/usr/bin/env python3
"""Validate a frozen Gateway request, or explicitly execute one live attempt.

The default dry run reads no credential, creates no ledger, and sends no HTTP.
--execute-live is an operator entry, not proof of Owner approval: an agent must
first satisfy the task's LIVE_CALL action and the approved numerical budget.
There are no implicit retries, fallback models, reconciliation, or new budgets.
Use the same ledger/run after interruption; inspect UNKNOWN before deciding on
any further attempt. Actual response bytes are retained in the private result.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import TextIO

sys.dont_write_bytecode = True

from anovel.gateway.ledger import BudgetLedger
from anovel.gateway.models import BudgetLimit, GatewayError, GatewayRequest, ModelPolicy
from anovel.gateway.provider import OpenAIResponsesAdapter, strict_json
from anovel.gateway.service import ModelGateway


def _write(stream: TextIO, record: dict[str, object]) -> None:
    stream.seek(0)
    json.dump(record, stream, ensure_ascii=False, indent=2)
    stream.write("\n")
    stream.truncate()
    stream.flush()
    os.fsync(stream.fileno())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--budget", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--policy-id", required=True)
    parser.add_argument("--policy-file", type=Path, default=Path("model-policy.yaml"))
    parser.add_argument("--attempt-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--execute-live", action="store_true")
    parser.add_argument(
        "--prompt-key",
        action="store_true",
        help="Read the key with hidden terminal input, instead of OPENAI_API_KEY",
    )
    args = parser.parse_args(argv)
    if args.prompt_key and not args.execute_live:
        parser.error("--prompt-key requires --execute-live")

    stream = None
    try:
        request = GatewayRequest.from_dict(strict_json(args.request.read_bytes()))
        budget = BudgetLimit.from_dict(strict_json(args.budget.read_bytes()))
        policy = next((p for p in request.policies if p.id == args.policy_id), None)
        if policy is None or not args.attempt_id.strip():
            raise GatewayError("Frozen policy and nonempty attempt required")
        configured = ModelPolicy.from_dict(strict_json(args.policy_file.read_bytes()))
        if configured != policy:
            raise GatewayError("Request policy differs from the current policy file")
        if (request.project, request.branch, request.run_id) != (
            budget.project,
            budget.branch,
            budget.run_id,
        ):
            raise GatewayError("Budget and request scope differ")
        instant = datetime.now(UTC)
        if (
            datetime.fromisoformat(budget.deadline_at) <= instant
            or datetime.fromisoformat(policy.price_expires_at) <= instant
            or policy.reserve_microusd > budget.total_microusd
        ):
            raise GatewayError("Budget does not admit the frozen policy")
        if args.execute_live and (
            policy.test_mode or policy.input_rate <= 0 or policy.output_rate <= 0
        ):
            raise GatewayError("Live requires a production policy and explicit rates")

        # Claim the output before any credential read or dispatch. A second
        # invocation cannot silently replace evidence from the first attempt.
        args.output.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        stream = os.fdopen(descriptor, "w", encoding="utf-8")
        summary: dict[str, object] = {
            "status": "DRY_RUN_VALIDATED",
            "request_hash": request.content_hash,
            "policy_hash": policy.content_hash,
            "run_id": request.run_id,
            "logical_id": request.logical_id,
            "attempt_id": args.attempt_id,
            "reserve_microusd": policy.reserve_microusd,
            "total_microusd": budget.total_microusd,
            "max_attempts": budget.max_attempts,
            "deadline_at": budget.deadline_at,
            "test_mode": policy.test_mode,
            "credential_read": False,
            "network_enabled": False,
            "live_authority": "NOT_ESTABLISHED_BY_THIS_SCRIPT",
        }
        _write(stream, summary)
        if not args.execute_live:
            print(json.dumps(summary))
            return 0

        key = (
            getpass.getpass("OpenAI API key: ")
            if args.prompt_key
            else os.environ.get("OPENAI_API_KEY", "")
        )
        if not key.strip():
            raise GatewayError("OpenAI credential entry missing")
        adapter = OpenAIResponsesAdapter(key)
        del key
        ledger = BudgetLedger(args.ledger)
        ledger.provision(budget)
        summary.update(
            status="LIVE_ATTEMPT_STARTED", credential_read=True, network_enabled=True
        )
        _write(stream, summary)
        result = ModelGateway(ledger, adapter).submit(
            request, policy.id, args.attempt_id
        )
        summary.update(
            status=result.status,
            response_hash=result.reply.response_hash,
            count_hash=result.reply.count_hash,
            provider_request_id=result.reply.provider_request_id,
            observed_model=result.reply.observed_model,
            usage=None if result.reply.usage is None else result.reply.usage.to_dict(),
            charge_status=result.charge_status,
            charge_microusd=result.charge_microusd,
            replayed=result.replayed,
            budget_summary=ledger.summary(request.run_id),
        )
        _write(stream, {"summary": summary, "result": result.to_dict()})
        print(json.dumps(summary))
        return 0 if result.status == "SUCCESS" else 1
    except (Exception, KeyboardInterrupt) as error:
        # Never print third-party exception text, request content or credentials.
        # A failure after dispatch does not prove a free attempt. The ledger is
        # authoritative for recovery, even if this result could not be written.
        failure: dict[str, object] = {
            "status": "INTERRUPTED_UNPROVEN_REVIEW_LEDGER"
            if isinstance(error, KeyboardInterrupt)
            else "BLOCKED_OR_UNPROVEN_REVIEW_LEDGER",
            "automatic_retry": False,
        }
        if stream is not None:
            try:
                _write(stream, failure)
            except OSError:
                pass
        print(json.dumps(failure))
        return 130 if isinstance(error, KeyboardInterrupt) else 1
    finally:
        if stream is not None:
            stream.close()


if __name__ == "__main__":
    raise SystemExit(main())
