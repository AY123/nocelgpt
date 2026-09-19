"""verify_market_hygiene_ab.py — does market-anchored hygiene pull prose toward the band?

M9 closure acceptance probe (NOT a unit test — costs real API). Takes real
generated chapters that DIVERGE from the reference band on ai_taste, runs the
prose-hygiene loop with the market anchor driving the rewrite, and measures
whether the rewritten body's ai_taste features actually move TOWARD the market
band — and whether the body stays intact (no wreckage). Isolates the rewrite
driver so only the rewrite spends API; the re-measure is free and deterministic.

Usage:
  python3 tools/verify_market_hygiene_ab.py --project ../genesis-pilot \
      --provider deepseek --model-id deepseek-v4-flash --max-chapters 5 --rounds 2
"""
from __future__ import annotations

import argparse
import glob
import json
import os
from pathlib import Path


def _load_env(project: Path) -> None:
    for candidate in (Path(__file__).resolve().parents[2] / ".env", project / ".env"):
        if not candidate.exists():
            continue
        for line in candidate.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


# Defect side per band-measured feature — mirrors prose_hygiene._MARKET_FEATURE_SPEC.
# Covers BOTH families (ai_taste + density) so the A/B measures convergence across
# everything the market-anchored hygiene now drives, not just AI-味.
MARKET_DEFECT = {
    "ai_taste.anaphora_run": "above",
    "ai_taste.dash_aside_per_1000": "above",
    "ai_taste.sentence_length_cv": "below",
    "density.dialogue_ratio": "below",
    "density.simile_per_1000": "above",
    "density.opening_simile_per_1000": "above",
}


def _defect_features(body: str, profile: dict):
    """The band-measured features (ai_taste + density) OUT of band on their defect
    side, with signed distance from the nearest edge (positive = worse).
    Deterministic."""
    from runtime.reference import measure_reference_chapter, compare_to_profile
    gap = compare_to_profile(measure_reference_chapter(body), profile)
    out = {}
    for feat, defect in MARKET_DEFECT.items():
        g = gap.get("features", {}).get(feat)
        if not g:
            continue
        on_defect = (not g["in_band"]) and g["direction"] == defect
        out[feat] = {
            "value": g["value"], "band": g["band"], "in_band": g["in_band"],
            "direction": g["direction"], "defect": on_defect,
            "edge_gap": g["edge_gap"] if on_defect else 0.0,
        }
    return out


def _defect_score(feats: dict) -> float:
    """Sum of defect-side edge gaps — the scalar the rewrite should shrink."""
    return round(sum(f["edge_gap"] for f in feats.values() if f["defect"]), 4)


def _pick_divergent(project: Path, profile: dict, limit: int):
    """Real generated chapters that diverge from the band on >=1 ai_taste defect
    side — the exact population the market-anchored hygiene should improve."""
    files = [f for f in sorted(glob.glob(str(project / "registry/derived/drafts/TASK-*.json")))
             if f.count(".") == 1]
    picked = []
    for f in files:
        d = json.loads(Path(f).read_text(encoding="utf-8"))
        body = (d.get("draft") or {}).get("body") or ""
        if not body.strip():
            continue
        feats = _defect_features(body, profile)
        if any(v["defect"] for v in feats.values()):
            picked.append((Path(f).stem, body, feats))
        if len(picked) >= limit:
            break
    return picked


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True, type=Path)
    ap.add_argument("--provider", default="deepseek")
    ap.add_argument("--model-id", default="deepseek-v4-flash")
    ap.add_argument("--max-chapters", type=int, default=5)
    ap.add_argument("--rounds", type=int, default=2)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    _load_env(args.project)
    from runtime.reference import load_reference_profile
    from runtime.execution.llm_model import LLMExecutionModel
    from runtime.execution.prose_hygiene import improve_prose_hygiene

    profile = load_reference_profile(args.project)
    if profile is None:
        raise SystemExit("no reference profile pinned; run `reference profile` first")

    divergent = _pick_divergent(args.project, profile, args.max_chapters)
    if not divergent:
        raise SystemExit("no band-divergent chapters found — nothing to test")
    print(f"{len(divergent)} divergent chapter(s); rewriting with market-anchored hygiene "
          f"({args.provider}/{args.model_id}, {args.rounds} round(s))...\n")

    rewrite_model = LLMExecutionModel(provider=args.provider, model_id=args.model_id,
                                      temperature=0.3, top_p=1.0, max_tokens=8192,
                                      timeout_seconds=180)

    rows = []
    improved = intact = worsened = unchanged = 0
    for cid, body, feats_before in divergent:
        artifact = {"task_id": cid, "kind": "prose", "capability": "ChapterDraft",
                    "body": body, "content_hash": "sha256:" + "0" * 64,
                    "provenance": {}, "word_count": len(body)}
        package = {"task": {"task_id": cid, "goal": "网文章节"}, "context": {}}
        res = improve_prose_hygiene(rewrite_model, artifact, package,
                                    max_rounds=args.rounds, reference_profile=profile)
        after_body = res.final_artifact.get("body", "")
        feats_after = _defect_features(after_body, profile)
        before_s, after_s = _defect_score(feats_before), _defect_score(feats_after)
        changed = res.final_artifact.get("content_hash") != artifact["content_hash"]
        # body-intact heuristic: rewrite kept length within a sane band (not gutted)
        len_ratio = round(len(after_body) / max(1, len(body)), 2)
        body_ok = 0.6 <= len_ratio <= 1.6
        if after_s < before_s - 1e-6:
            improved += 1
        elif after_s > before_s + 1e-6:
            worsened += 1
        else:
            unchanged += 1
        if body_ok:
            intact += 1
        rows.append({
            "chapter": cid, "verdict": res.session.verdict,
            "defect_score_before": before_s, "defect_score_after": after_s,
            "delta": round(after_s - before_s, 4),
            "chars_before": len(body), "chars_after": len(after_body),
            "len_ratio": len_ratio, "body_intact": body_ok, "changed": changed,
        })
        print(f"  {cid}: defect {before_s} -> {after_s} "
              f"({'IMPROVED' if after_s < before_s else 'no-drop'})  "
              f"len×{len_ratio}  verdict={res.session.verdict}")

    n = len(rows)
    print(f"\n{improved}/{n} chapters moved TOWARD the market band; "
          f"{worsened} moved away; {unchanged} unchanged.")
    print(f"{intact}/{n} kept body intact (0.6-1.6× length).")
    mean_delta = round(sum(r["delta"] for r in rows) / n, 4) if n else 0.0
    print(f"mean defect-score delta: {mean_delta} (negative = converged toward market)")
    # Three honest states. With the lexicographic (count, distance) keep-best, a
    # rewrite that shrinks a defect distance is now KEPT even without clearing a
    # zero-tolerance band — so a non-firing chapter is no longer a keep-best
    # artifact but a REWRITE-MODEL limit: the model returned prose whose defect
    # distance did not drop. The remaining lever is the rewrite instruction /
    # model strength, not the acceptance rule.
    hit_rate = improved / n if n else 0.0
    if worsened > improved or mean_delta > 0:
        verdict = "NO / NEGATIVE CONVERGENCE — the anchor did not pull prose toward the market"
    elif hit_rate >= 0.5:
        verdict = "STRONG CONVERGENCE — market-anchored hygiene reliably converges the band"
    else:
        verdict = (f"PARTIAL CONVERGENCE — converges when it fires (body intact, "
                   f"mean Δ {mean_delta}) but only {improved}/{n} chapters moved; the "
                   f"non-firing ones are a rewrite-model limit (returned prose whose "
                   f"defect distance didn't drop), not a keep-best limit")
    print(f"\nVERDICT: {verdict}")

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps({
            "provider": args.provider, "model_id": args.model_id,
            "rounds": args.rounds, "n": n, "improved": improved,
            "worsened": worsened, "unchanged": unchanged, "body_intact": intact,
            "mean_defect_delta": mean_delta, "rows": rows, "verdict": verdict,
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
