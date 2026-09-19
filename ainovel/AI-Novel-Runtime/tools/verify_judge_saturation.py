"""verify_judge_saturation.py — does the LLM judge score market winners higher?

M9 acceptance probe (NOT a unit test — costs real API). Controlled sample:
sample N reference chapters (market-validated winners) + M generated chapters,
score BOTH with the SAME LLMQualityJudge at temp 0, and compare the mean per-
dimension scores. If the judge cannot separate a market winner from a mediocre
generated chapter, that CONFIRMS the "judge is saturated" hypothesis (and is the
whole reason the deterministic reference anchor exists). If it CAN separate them,
that FALSIFIES it and the judge stays a useful absolute signal.

Usage:
  python3 tools/verify_judge_saturation.py --project ../genesis-pilot \
      --n-ref 8 --n-gen 8 --provider deepseek
"""
from __future__ import annotations

import argparse
import json
import os
import statistics as stats
from pathlib import Path

def _load_env(project: Path) -> None:
    """Load DEEPSEEK_API_KEY etc. from the repo .env / project .env if present."""
    for candidate in (Path(__file__).resolve().parents[2] / ".env",
                      project / ".env"):
        if not candidate.exists():
            continue
        for line in candidate.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _sample(seq, n):
    """Evenly sample n items across seq (deterministic — no RNG)."""
    if n >= len(seq):
        return list(seq)
    step = len(seq) / n
    return [seq[int(i * step)] for i in range(n)]


def _reference_bodies(project: Path, n: int):
    from runtime.outline.sources import load_reference_sources, iter_source_texts
    from runtime.reference.segment import segment_reference_novel
    check = load_reference_sources(project)
    if not check.ok:
        raise SystemExit(f"reference sources invalid: {check.errors}")
    # one novel is enough for the probe; take the smallest for a cheaper run
    src, text = min(iter_source_texts(project, check.sources),
                    key=lambda st: len(st[1]))
    chapters = segment_reference_novel(src.id, text)
    # skip the first few (front matter / slow openings) then sample evenly
    body_pool = [c.body for c in chapters[3:] if len(c.body) > 800]
    return [(f"{src.id}#ref", b) for b in _sample(body_pool, n)]


def _generated_bodies(project: Path, n: int):
    drafts_dir = project / "registry" / "derived" / "drafts"
    files = sorted(p for p in drafts_dir.glob("*.json")
                   if "." not in p.stem.replace("TASK-", "").replace("-", ""))
    out = []
    for p in _sample(files, n):
        obj = json.loads(p.read_text(encoding="utf-8"))
        body = (obj.get("draft") or {}).get("body") or ""
        if body.strip():
            out.append((p.stem, body))
    return out


def _score(judge, label, body):
    report = judge.review({"body": body}, {"task": {"goal": "网文章节评审"}, "context": {}})
    d = report.to_dict()
    scores = d.get("scores") or {}
    degraded = (d.get("judge_provenance") or {}).get("degraded")
    return {"label": label, "chars": len(body), "degraded": bool(degraded),
            "scores": scores}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True, type=Path)
    ap.add_argument("--n-ref", type=int, default=8)
    ap.add_argument("--n-gen", type=int, default=8)
    ap.add_argument("--provider", default="deepseek")
    ap.add_argument("--model-id", default="")
    ap.add_argument("--out", default=None, help="write full JSON result here")
    args = ap.parse_args()

    _load_env(args.project)
    from runtime.execution.llm_model import LLMExecutionModel
    from runtime.execution.quality_center import (
        llm_quality_judge, SCORE_DIMENSIONS, LOWER_IS_BETTER)

    # 18 dimensions × (score + Chinese evidence + comment) + revision_plan +
    # predictions easily exceed 2k tokens; too small a cap truncates the JSON and
    # the judge report silently degrades. Give it real headroom.
    model = LLMExecutionModel(provider=args.provider, model_id=args.model_id,
                              temperature=0.0, top_p=1.0, max_tokens=8192,
                              timeout_seconds=180)
    judge = llm_quality_judge(model)

    refs = _reference_bodies(args.project, args.n_ref)
    gens = _generated_bodies(args.project, args.n_gen)
    print(f"scoring {len(refs)} reference + {len(gens)} generated chapters "
          f"with {args.provider} judge (temp 0)...")

    ref_reports, gen_reports = [], []
    for label, body in refs:
        r = _score(judge, label, body)
        ref_reports.append(r)
        print(f"  REF {label:16} degraded={r['degraded']}")
    for label, body in gens:
        r = _score(judge, label, body)
        gen_reports.append(r)
        print(f"  GEN {label:16} degraded={r['degraded']}")

    def _mean(reports, dim):
        xs = [rp["scores"][dim] for rp in reports
              if not rp["degraded"] and isinstance(rp["scores"].get(dim), (int, float))]
        return round(stats.mean(xs), 1) if xs else None

    print(f"\n{'dimension':<22}{'ref':>7}{'gen':>7}{'Δ(ref-gen)':>12}  winner")
    rows = []
    ref_higher = gen_higher = 0
    for dim in SCORE_DIMENSIONS:
        rm, gm = _mean(ref_reports, dim), _mean(gen_reports, dim)
        if rm is None or gm is None:
            continue
        delta = round(rm - gm, 1)
        # a "market winner should score higher" expectation flips for risk dims
        winner = "ref" if (delta > 0) != (dim in LOWER_IS_BETTER) else "gen"
        if abs(delta) < 1.0:
            winner = "tie"
        elif winner == "ref":
            ref_higher += 1
        else:
            gen_higher += 1
        rows.append({"dimension": dim, "ref": rm, "gen": gm, "delta": delta, "winner": winner})
        print(f"{dim:<22}{rm:>7}{gm:>7}{delta:>12}  {winner}")

    # overall means (risk-adjusted: for lower-is-better dims, invert so higher=better)
    def _quality_mean(reports):
        vals = []
        for rp in reports:
            if rp["degraded"]:
                continue
            for dim in SCORE_DIMENSIONS:
                s = rp["scores"].get(dim)
                if isinstance(s, (int, float)):
                    vals.append((100 - s) if dim in LOWER_IS_BETTER else s)
        return round(stats.mean(vals), 1) if vals else None

    ref_q, gen_q = _quality_mean(ref_reports), _quality_mean(gen_reports)
    print(f"\nrisk-adjusted quality mean:  ref={ref_q}  gen={gen_q}  "
          f"Δ={round((ref_q or 0) - (gen_q or 0), 1)}")
    print(f"per-dimension: ref-higher={ref_higher}  gen-higher={gen_higher}  "
          f"tie={len(rows) - ref_higher - gen_higher}")
    # Three outcomes, not two. The naive "saturated vs not" framing misses the
    # real risk: the judge may separate the two groups CONFIDENTLY but in the
    # WRONG direction — scoring its own AI-generated prose above a market winner.
    # That is worse than saturation for using the absolute score as a quality
    # truth, and is the strongest argument for the deterministic reference anchor.
    delta = round((ref_q or 0) - (gen_q or 0), 1)
    sep = abs(delta) >= 3.0 and abs(ref_higher - gen_higher) >= 3
    if not sep:
        verdict = ("SATURATED / cannot separate market winner from mediocre "
                   "generated prose")
    elif ref_higher > gen_higher:
        verdict = ("SEPARATES CORRECTLY (falsifies saturation): scores the "
                   "market winner higher — absolute score is a usable signal")
    else:
        verdict = ("SEPARATES but INVERTED: scores its own generated prose ABOVE "
                   "the market winner — the absolute judge score is NOT a quality "
                   "ground-truth; the deterministic reference anchor is (M9)")
    print(f"\nVERDICT: judge {verdict}")

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps({
            "provider": args.provider, "n_ref": len(refs), "n_gen": len(gens),
            "ref_reports": ref_reports, "gen_reports": gen_reports,
            "per_dimension": rows, "ref_quality_mean": ref_q, "gen_quality_mean": gen_q,
            "ref_higher": ref_higher, "gen_higher": gen_higher, "verdict": verdict,
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
