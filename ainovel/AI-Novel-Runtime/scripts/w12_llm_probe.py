"""w12_llm_probe.py — small LLM-extraction probe (3 chapters) for W12 reflow.

Before spending API on all 33 chapters, this validates the LLM path on 3 real
RUN-00025 chapters: does the LLMExtractor produce new/additive candidates the
deterministic extractor cannot? Read-only reconcile against the real registry;
plans are NOT staged. Uses an isolated replay bucket so a re-run is free.

Usage (from AI-Novel-Runtime/):
  PYTHONPATH=. python3 scripts/w12_llm_probe.py [N]
"""
from __future__ import annotations

import json
import glob
import os
import sys
from pathlib import Path

RT = Path(__file__).resolve().parents[1]
PILOT = RT.parent / "genesis-pilot"
DRAFTS = PILOT / "analysis" / "run-00025-snapshot" / "derived" / "drafts"
REPLAY = PILOT / "registry" / "derived" / "serial-replay-w12probe-gen"


def _load_env() -> None:
    for f in (PILOT / ".env", RT.parent / ".env"):
        if f.is_file():
            for line in f.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def main() -> None:
    _load_env()
    if not os.environ.get("DEEPSEEK_API_KEY"):
        raise SystemExit("DEEPSEEK_API_KEY not set — cannot run the LLM probe")

    from runtime.candidates.extract import entity_roster, LLMExtractor, DeterministicExtractor
    from runtime.candidates.reconcile import reconcile
    from runtime.registry_loader import load as load_registry
    from runtime.execution.llm_model import LLMExecutionModel

    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    reg = load_registry(PILOT)
    roster = entity_roster(reg, reg.all_ids())
    model = LLMExecutionModel(provider="deepseek", model_id="deepseek-chat",
                              temperature=0.0, replay_dir=str(REPLAY))
    llm = LLMExtractor(model)
    det = DeterministicExtractor()

    files = sorted(glob.glob(str(DRAFTS / "*.json")))[:n]
    print(f"probing {len(files)} chapters with LLM extractor (replay={REPLAY.name})\n")
    for f in files:
        env = json.load(open(f))
        draft = env.get("draft") or env
        tid = draft.get("task_id")
        det_c = det.extract(draft, known_entities=roster)
        llm_c = llm.extract(draft, known_entities=roster)
        det_recon = reconcile(reg, det_c).counts()
        llm_recon = reconcile(reg, llm_c).counts()
        print(f"{tid} (body={len(draft.get('body','') or '')}ch)")
        print(f"  deterministic: {len(det_c)} cand  {det_recon}")
        print(f"  LLM         : {len(llm_c)} cand  {llm_recon}")
        # show a few LLM candidates that are NOT plain status=active (the deterministic ceiling)
        interesting = [c for c in llm_c if not (getattr(c, 'field', '') == 'status'
                                                and getattr(c, 'value', '') == 'active')]
        for c in interesting[:4]:
            attrs = {k: getattr(c, k) for k in ('entity_type', 'field', 'value', 'entity_id')
                     if hasattr(c, k)}
            print(f"    · {attrs}")
        print()


if __name__ == "__main__":
    main()
