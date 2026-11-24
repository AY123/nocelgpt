#!/usr/bin/env python3
"""Validate a frozen Gateway request, or explicitly execute one live attempt.

The default dry run reads no credential, creates no ledger, and sends no HTTP.
--execute-live requires a frozen, exactly bound authorization validated by the
same fixed dispatcher as the task entry. It never establishes Owner approval.
There are no implicit retries, fallback models, reconciliation, or new budgets.
Use the same ledger/run after interruption; inspect UNKNOWN before deciding on
any further attempt. Actual response bytes are retained in the private result.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from contextlib import ExitStack
from datetime import UTC, datetime
from pathlib import Path
from typing import TextIO

sys.dont_write_bytecode = True

from anovel.gateway.ledger import BudgetLedger
from anovel.gateway.models import BudgetLimit, GatewayError, GatewayRequest, ModelPolicy
from anovel.gateway.probe_runtime import (
    private_probe_directory,
    read_hidden_credential,
)
from anovel.gateway.provider import (
    KimiChatCompletionsAdapter,
    OpenAIResponsesAdapter,
    strict_json,
)
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
        help="Require hidden input from a controllable /dev/tty for authorized live use",
    )
    parser.add_argument("--parent-tty-fd", type=int, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.prompt_key and not args.execute_live:
        parser.error("--prompt-key requires --execute-live")
    if args.parent_tty_fd is not None and not (args.execute_live and args.prompt_key):
        parser.error("--parent-tty-fd requires live hidden terminal input")

    stream = None
    contexts = ExitStack()
    try:
        config = None
        if args.execute_live:
            if not args.prompt_key:
                raise GatewayError("Live requires hidden terminal credential entry")
            root = Path(__file__).resolve().parents[1]
            sys.path.insert(0, str(root / "plan/scripts"))
            from probe_dispatch import validate_probe

            config = validate_probe(
                root,
                request_path=args.request,
                budget_path=args.budget,
                policy_path=args.policy_file,
                ledger=args.ledger,
                output=args.output,
                policy_id=args.policy_id,
                attempt_id=args.attempt_id,
            )
            request, budget, policy = config.request, config.budget, config.policy
        else:
            request = GatewayRequest.from_dict(strict_json(args.request.read_bytes()))
            budget = BudgetLimit.from_dict(strict_json(args.budget.read_bytes()))
            matched = next(
                (p for p in request.policies if p.id == args.policy_id), None
            )
            if matched is None or not args.attempt_id.strip():
                raise GatewayError("Frozen policy and nonempty attempt required")
            policy = matched
            configured = ModelPolicy.from_dict(
                strict_json(args.policy_file.read_bytes())
            )
            if configured != policy:
                raise GatewayError(
                    "Request policy differs from the current policy file"
                )
        if (request.project, request.branch, request.run_id) != (
            budget.project,
            budget.branch,
            budget.run_id,
        ):
            raise GatewayError("Budget and request scope differ")
        estimate_fee = None if config is None else config.estimate_fee
        reserve = policy.reserve_microusd + (
            estimate_fee.maximum_microusd if estimate_fee is not None else 0
        )
        instant = datetime.now(UTC)
        if (
            datetime.fromisoformat(budget.deadline_at) <= instant
            or datetime.fromisoformat(policy.price_expires_at) <= instant
            or reserve > budget.total_microusd
        ):
            raise GatewayError("Budget does not admit the frozen policy")
        if config is not None and (
            (policy.test_mode and not config.allow_test_transport)
            or policy.input_rate <= 0
            or policy.output_rate <= 0
        ):
            raise GatewayError("Live requires authorized transport and explicit rates")

        private = None
        if config is not None:
            private = contexts.enter_context(
                private_probe_directory(config.ledger, config.output, config.claim_path)
            )
            # Consumption survives missing credentials and interruptions. A later
            # invocation must inspect the same claim/ledger, never silently send.
            private.claim_authorization(config.authorization_id, args.attempt_id)
            stream = private.open_result()
        else:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            descriptor = os.open(
                args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
            )
            stream = os.fdopen(descriptor, "w", encoding="utf-8")
        summary: dict[str, object] = {
            "status": "DRY_RUN_VALIDATED",
            "request_hash": request.content_hash,
            "policy_hash": policy.content_hash,
            "run_id": request.run_id,
            "logical_id": request.logical_id,
            "attempt_id": args.attempt_id,
            "provider": "KIMI" if policy.is_kimi else "OPENAI",
            "reserve_microusd": reserve,
            "total_microusd": budget.total_microusd,
            "max_attempts": budget.max_attempts,
            "deadline_at": budget.deadline_at,
            "test_mode": policy.test_mode,
            "credential_read": False,
            "network_enabled": False,
            "live_authority": "NOT_ESTABLISHED_BY_THIS_SCRIPT",
        }
        if config is not None:
            summary.update(
                authorization_id=config.authorization_id,
                probe_environment="LOOPBACK_FIXTURE"
                if config.allow_test_transport
                else "LIVE_PROVIDER",
                first_capability_investigation=True,
                grant_validated=True,
            )
            if config.generation_only:
                summary["token_estimate"] = "NOT_REQUESTED"
        if estimate_fee is not None:
            summary["estimate_fee_reserve"] = {
                "maximum_microusd": estimate_fee.maximum_microusd,
                "evidence_sha256": estimate_fee.evidence_sha256,
                "expires_at": estimate_fee.expires_at,
            }
        _write(stream, summary)
        if not args.execute_live:
            print(json.dumps(summary))
            return 0

        if config is None or private is None:
            raise GatewayError("Fixed probe authorization required")
        key = read_hidden_credential(
            deadline_at=config.deadline_at,
            tty_fd=args.parent_tty_fd,
            kimi=policy.is_kimi,
        )
        config.revalidate()
        private.verify_files()
        adapter = (
            KimiChatCompletionsAdapter(
                key,
                allow_test_transport=config.allow_test_transport,
                generation_only=config.generation_only,
            )
            if policy.is_kimi
            else OpenAIResponsesAdapter(
                key, allow_test_transport=config.allow_test_transport
            )
        )
        del key
        ledger = BudgetLedger(config.ledger)
        ledger.provision(budget)
        config.revalidate()
        private.verify_files()
        summary.update(
            status="LIVE_ATTEMPT_STARTED", credential_read=True, network_enabled=True
        )
        _write(stream, summary)
        result = ModelGateway(ledger, adapter).submit(
            request, policy.id, args.attempt_id, estimate_fee=estimate_fee
        )
        private.verify_files()
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
        return (
            0 if result.status == "SUCCESS" and result.charge_status != "PENDING" else 1
        )
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
        try:
            if stream is not None:
                stream.close()
        finally:
            contexts.close()


if __name__ == "__main__":
    raise SystemExit(main())
