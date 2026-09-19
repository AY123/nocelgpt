"""n100_evidence_pack.py — generate the frozen protocol + chapter evidence ledger.

This is the single operator-facing hook for N100-002/N100-003 evidence material.
It reads an existing run manifest (default RUN-00025), freezes the experiment
protocol, folds a chapter evidence ledger, and writes both to stable analysis/
artifacts.

Usage (from AI-Novel-Runtime/):
  PYTHONPATH=. python3 scripts/n100_evidence_pack.py [run_id]
"""
from __future__ import annotations

import sys
from pathlib import Path

RT = Path(__file__).resolve().parents[1]
if str(RT) not in sys.path:
    sys.path.insert(0, str(RT))

from runtime.serialize.experiment_protocol import build_experiment_protocol, write_experiment_protocol
from runtime.serialize.chapter_evidence_ledger import build_chapter_evidence_ledger, write_chapter_evidence_ledger

PILOT = RT.parent / "genesis-pilot"
DEFAULT_RUN_ID = "RUN-00025"


def main() -> None:
    run_id = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_RUN_ID
    manifest_path = PILOT / "registry" / "derived" / "run-manifests" / f"{run_id}.json"
    if not manifest_path.is_file():
        raise SystemExit(f"run manifest not found: {manifest_path}")

    protocol = build_experiment_protocol(
        protocol_id="N100-PROTOCOL-0001",
        project_id="genesis-pilot",
        model_provider="deepseek",
        model_id="deepseek-chat",
        prompt_version="10.0.0",
        prompt_bundle_ref="AI-Novel-Standard/contracts/prompt-bundles/launch-30ch-v10.json",
        schema_ref="AI-Novel-Standard/phase-1/generated/json-schema",
        budget_limit_cny=20.0,
    )
    protocol_path = PILOT / "analysis" / f"{run_id.lower()}-experiment-protocol.json"
    write_experiment_protocol(protocol_path, protocol)

    ledger = build_chapter_evidence_ledger(
        project_path=PILOT,
        run_manifest_path=manifest_path,
        protocol=protocol,
    )
    ledger_path = PILOT / "analysis" / f"{run_id.lower()}-chapter-evidence-ledger.json"
    write_chapter_evidence_ledger(ledger_path, ledger)

    print(f"protocol: {protocol_path}")
    print(f"ledger  : {ledger_path}")
    print(f"chapters : {ledger['chapter_count']}")
    print(f"hash    : {ledger['content_hash']}")


if __name__ == "__main__":
    main()
