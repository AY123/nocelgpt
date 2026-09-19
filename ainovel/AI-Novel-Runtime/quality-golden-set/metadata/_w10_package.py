#!/usr/bin/env python3
"""W10-02 blind review package builder (two-way: original vs automatic_revision).

For the 22 candidates whose auto arm DIFFERS from the original, emit a blind
packet a human reviewer can read:
  - each candidate gets shuffled A/B versions (provenance hidden, deterministic
    shuffle seeded by candidate id so it is reproducible but not guessable)
  - the unblind key (which of A/B is original vs auto) is written to a SEPARATE
    file so the reader cannot see it
  - a deterministic instrument delta (warning count + defect distance, orig vs
    auto) rides along as an ADVISORY companion, clearly NOT the verdict

The 8 identical-auto candidates are recorded as skipped (no comparable arm).
Winners are left null: only a human fills them (do_not_override_human_judgement).

No spend. Reads the bound inputs + the auto-revision artifacts + baseline finals.
"""
import hashlib
import json
import os
import sys
from pathlib import Path

META = Path(__file__).resolve().parent
RT = META.parents[1]
ROOT = RT.parent
PROJECT = ROOT / "genesis-pilot"
AUTO = RT / "quality-golden-set" / "w10-auto-revision"
PKG = RT / "quality-golden-set" / "w10-blind-package"

sys.path.insert(0, str(RT))


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def original_text(cid):
    doc = load(PROJECT / "registry" / "derived" / "chapter-final"
               / f"final-{cid}.json")
    return doc.get("final_text", "")


def auto_text(cid):
    doc = load(AUTO / f"auto-{cid}.json")
    return doc.get("artifact", {}).get("body", "")


def instrument_delta(orig_body, auto_body, profile):
    """Deterministic advisory: warning count + defect distance for both versions.
    Lower is better on both. This is a MEASUREMENT, not a winner."""
    from runtime.reference import measure_reference_chapter, compare_to_profile
    from runtime.execution.prose_hygiene import _defect_distance

    def measure(body):
        art = {"body": body}
        gap = compare_to_profile(measure_reference_chapter(body), profile)
        return {
            "out_of_band": gap["out_of_band"],
            "in_band": gap["in_band"],
            "defect_distance": _defect_distance(art, profile),
            "chars": len(body),
        }

    o, a = measure(orig_body), measure(auto_body)
    return {
        "original": o,
        "automatic_revision": a,
        "defect_distance_delta": round(a["defect_distance"] - o["defect_distance"], 4),
        "oob_delta": a["out_of_band"] - o["out_of_band"],
        "note": ("ADVISORY ONLY — deterministic instrument reading, NOT the blind "
                 "winner. Negative deltas mean the auto arm moved toward the market "
                 "band. The LLM judge is known-biased and is deliberately NOT used "
                 "to pick winners here."),
    }


def blinded_order(cid):
    """Deterministic A/B assignment seeded by candidate id: reproducible, but the
    reader has no provenance in the packet to reverse it."""
    h = int(hashlib.sha256(cid.encode()).hexdigest(), 16)
    # even -> A=original, odd -> A=automatic_revision
    return "original_first" if h % 2 == 0 else "automatic_first"


def main():
    PKG.mkdir(parents=True, exist_ok=True)
    from runtime.reference.profile import load_reference_profile
    profile = load_reference_profile(PROJECT)

    inputs = load(META / "w10-blind-review-inputs.json")

    runnable, skipped = [], []
    unblind_key = {}
    for batch in inputs["inputs"]:
        for cand in batch["bound_candidates"]:
            qgs = cand["candidate_id"]
            cid = cand["bound_chapter_id"]
            auto_payload = next(p for p in cand["payloads"]
                                if p["version_id"] == "automatic_revision")
            if auto_payload["status"] != "bound":
                skipped.append({"candidate_id": qgs, "bound_chapter_id": cid,
                                "reason": auto_payload["status"],
                                "auto_verdict": cand.get("auto_verdict")})
                continue

            o_text, a_text = original_text(cid), auto_text(cid)
            order = blinded_order(qgs)
            if order == "original_first":
                ver_a, ver_b = ("original", o_text), ("automatic_revision", a_text)
            else:
                ver_a, ver_b = ("automatic_revision", a_text), ("original", o_text)

            # NOTE: char counts are intentionally OMITTED from the reader packet —
            # they leak provenance (auto arm often differs in length, letting the
            # reviewer reverse the blind by matching lengths). The advisory delta
            # (also length-bearing) lives in the SEPARATE unblind file for the same
            # reason. The reader sees only the two texts.
            packet = {
                "candidate_id": qgs,
                "batch_id": batch["batch_id"],
                "instruction": ("Read version A and version B. Decide which reads "
                                "better as a commercial web-novel chapter. Record "
                                "winner (A / B / tie), confidence, and reason codes. "
                                "Provenance is hidden."),
                "version_A": {"text": ver_a[1]},
                "version_B": {"text": ver_b[1]},
                "human_result": {"winner": None, "confidence": None,
                                 "reason_codes": [], "notes": ""},
            }
            (PKG / f"packet-{qgs}.json").write_text(
                json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")
            unblind_key[qgs] = {
                "bound_chapter_id": cid,
                "version_A": ver_a[0], "version_B": ver_b[0],
                "advisory_instrument_delta": instrument_delta(o_text, a_text, profile),
            }
            runnable.append(qgs)

    (PKG / "_UNBLIND_KEY.json").write_text(
        json.dumps({"kind": "w10_blind_unblind_key",
                    "warning": "Do NOT open before recording human winners.",
                    "map": unblind_key}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    (PKG / "_manifest.json").write_text(
        json.dumps({"kind": "w10_blind_package_manifest",
                    "review_type": "two_way_original_vs_automatic",
                    "runnable_candidates": runnable,
                    "runnable_count": len(runnable),
                    "skipped_no_auto_arm": skipped,
                    "skipped_count": len(skipped),
                    "human_arm": "absent — three-way review still blocked",
                    "winner_authority": "human only (do_not_override_human_judgement)"},
                   ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"blind packets: {len(runnable)} runnable, {len(skipped)} skipped")
    print(f"unblind key + manifest written to {PKG.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
