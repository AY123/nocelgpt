#!/usr/bin/env python3
"""W10-02 binding: map the 30 ranked real baseline chapters onto the QGS candidate
slots and bind real content refs into candidates / batches / inputs.

- original arm  -> chapter-final/final-<cid>.json#final_text  (real, exists)
- automatic arm -> w10-auto-revision/auto-<cid>.json#artifact.body  (generated)
- human arm     -> null, marked pending_human (does not exist; not faked)

Deterministic, no spend. Rewrites the 3 metadata files in place, preserving their
declared shape (no frozen schema governs these files).
"""
import json
import sys
from pathlib import Path

META = Path(__file__).resolve().parent
RT = META.parents[1]
AUTO = RT / "quality-golden-set" / "w10-auto-revision"
BASELINE = "genesis-pilot/registry/derived"

sys.path.insert(0, str(META))
import _w10_select as sel  # noqa: E402


def load(p):
    return json.loads((META / p).read_text(encoding="utf-8"))


def dump(p, obj):
    (META / p).write_text(
        json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    rows = sel.rank()[:30]
    chapter_ids = [r["chapter_id"] for r in rows]

    candidates = load("w10-blind-review-candidates.json")
    # QGS slot order in the frozen candidate list == slot order we bind into.
    slots = candidates["candidates"]
    assert len(slots) == 30, f"expected 30 candidate slots, got {len(slots)}"

    # Build QGS-slot -> real chapter map, worst-first onto the existing slot order.
    slot_to_chapter = {}
    for slot, cid, row in zip(slots, chapter_ids, rows):
        qgs = slot["sample_id"]
        slot_to_chapter[qgs] = cid
        slot["bound_chapter_id"] = cid
        slot["source"] = "baseline_30ch"
        slot["warning_rank"] = {"warnings": row["warnings"],
                                "ref_oob": row["ref_oob"], "tags": row["tags"]}
    candidates["binding_status"] = "bound_to_real_baseline"
    candidates["note"] = ("Candidate QGS slots are now bound to real 30-chapter "
                          "baseline chapter ids (worst-first by warning load). "
                          "original+automatic arms are real; human arm pending.")
    candidates["candidate_chapter_map"] = slot_to_chapter
    dump("w10-blind-review-candidates.json", candidates)

    # ---- inputs.json: real content refs per version -------------------------
    inputs = load("w10-blind-review-inputs.json")

    def orig_ref(cid):
        return f"{BASELINE}/chapter-final/final-{cid}.json#final_text"

    def auto_ref(cid):
        # repo-root-relative, matching the original arm's genesis-pilot/... refs
        return (f"AI-Novel-Runtime/quality-golden-set/w10-auto-revision/"
                f"auto-{cid}.json#artifact.body")

    # An auto file counts as a usable arm only if its body actually DIFFERS from
    # the original. rejected_gutting / no_improvement keep-best returns the
    # original byte-for-byte -> not a comparable arm. Flag it, never hide it.
    # The run-summary's per-chapter `changed` flag is the authoritative signal.
    summary = json.loads((AUTO / "_run-summary.json").read_text(encoding="utf-8"))
    auto_meta = {c["chapter_id"]: c for c in summary.get("chapters", [])}
    auto_present = {cid for cid, m in auto_meta.items() if m.get("changed")}
    auto_identical = {cid for cid, m in auto_meta.items() if not m.get("changed")}

    for batch in inputs["inputs"]:
        # one batch holds 3 candidate slots -> bind each to its mapped chapter
        bound = []
        for qgs in batch["candidate_ids"]:
            cid = slot_to_chapter[qgs]
            differs = cid in auto_present
            identical = cid in auto_identical
            if differs:
                auto_status = "bound"
            elif identical:
                auto_status = "identical_to_original"
            else:
                auto_status = "missing_auto"
            bound.append({
                "candidate_id": qgs,
                "bound_chapter_id": cid,
                "auto_verdict": (auto_meta.get(cid) or {}).get("verdict"),
                "payloads": [
                    {"version_id": "original",
                     "content_ref": orig_ref(cid), "provenance_hidden": True},
                    {"version_id": "automatic_revision",
                     "content_ref": auto_ref(cid),
                     "status": auto_status,
                     "provenance_hidden": True},
                    {"version_id": "human_revision",
                     "content_ref": None,
                     "status": "pending_human",
                     "provenance_hidden": True},
                ],
            })
        batch["bound_candidates"] = bound
        # drop the old redacted placeholder payloads
        batch.pop("payloads", None)
    inputs["binding_status"] = "original_and_auto_bound_human_pending"
    inputs["execution_note"] = ("original arm bound to real chapter-final text; "
                                "automatic_revision bound to market-anchored "
                                "prose-hygiene output; human_revision pending "
                                "(no human material exists yet).")
    dump("w10-blind-review-inputs.json", inputs)

    n_diff = len(auto_present & set(chapter_ids))
    n_same = len(auto_identical & set(chapter_ids))
    print(f"bound {len(chapter_ids)} chapters; auto differs for {n_diff}/30, "
          f"identical (no comparable auto arm) for {n_same}/30")
    print("chapter map (worst-first):")
    for qgs, cid in slot_to_chapter.items():
        if cid in auto_identical:
            flag = f"  [AUTO==ORIG: {(auto_meta.get(cid) or {}).get('verdict')}]"
        elif cid not in auto_present:
            flag = "  [AUTO MISSING]"
        else:
            flag = ""
        print(f"  {qgs} -> {cid}{flag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
