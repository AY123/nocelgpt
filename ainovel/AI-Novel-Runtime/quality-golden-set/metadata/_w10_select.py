#!/usr/bin/env python3
"""W10-02 candidate selection: rank the 33 real baseline chapters by warning load
and pick the 30 most-defective as blind-review candidates. Deterministic, no spend.

Output: prints a JSON list of {chapter_id, warnings, tags} sorted worst-first."""
import json
import glob
import os

BASELINE = os.path.expanduser(
    "~/Documents/xiaoshuo/AINovel/genesis-pilot/registry/derived"
)


def warn_count(section):
    """Count severity=='warning' findings in an evaluative section."""
    if not isinstance(section, dict):
        return 0
    return sum(
        1
        for f in section.get("findings", [])
        if isinstance(f, dict) and f.get("severity") == "warning"
    )


def rank():
    rows = []
    for path in sorted(glob.glob(f"{BASELINE}/chapter-run/*.json")):
        run = json.load(open(path, encoding="utf-8"))
        cid = run.get("task_id")
        tags = []
        w = 0
        for key in ("ai_taste", "density", "end_hook", "pacing", "integrity"):
            c = warn_count(run.get(key))
            if c:
                tags.append(f"{key}:{c}")
            w += c
        # reference_gap out-of-band features add defect signal (advisory only)
        rg = run.get("reference_gap") or {}
        oob = rg.get("out_of_band", 0) if isinstance(rg, dict) else 0
        rows.append(
            {"chapter_id": cid, "warnings": w, "ref_oob": oob, "tags": tags}
        )
    # worst-first: warnings desc, then ref_oob desc, then id asc (stable/deterministic)
    rows.sort(key=lambda r: (-r["warnings"], -r["ref_oob"], r["chapter_id"]))
    return rows


if __name__ == "__main__":
    rows = rank()
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    print(f"\n# total chapters: {len(rows)}")
    print(f"# top-30 warning range: "
          f"{rows[0]['warnings']} .. {rows[29]['warnings']}")
