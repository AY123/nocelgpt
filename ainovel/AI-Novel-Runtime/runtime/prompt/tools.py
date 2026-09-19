from __future__ import annotations

import json
from pathlib import Path


def load_prompt_record(path: str | Path) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if "manifest" not in data:
        raise ValueError(f"{path} is not a prompt manifest/cache record")
    return data


def manifest_view(path: str | Path) -> dict:
    record = load_prompt_record(path)
    manifest = record["manifest"]
    rendered = record.get("rendered")
    return {
        "path": str(path),
        "prompt_id": manifest["prompt_id"],
        "version": manifest["version"],
        "capability": manifest["capability"],
        "template_hash": manifest["template_hash"],
        "binding_hash": manifest["binding_hash"],
        "rendered_hash": manifest["rendered_hash"],
        "package_hash": manifest["package_hash"],
        "derived_from": manifest["derived_from"],
        "source_version": manifest.get("source_version"),
        "cache_hit": manifest["cache_hit"],
        "replay_ref": manifest["replay_ref"],
        "messages": rendered.get("messages", []) if rendered else [],
    }


def diff_records(left_path: str | Path, right_path: str | Path) -> list[str]:
    left = manifest_view(left_path)
    right = manifest_view(right_path)
    lines = []
    for key in (
        "prompt_id",
        "version",
        "template_hash",
        "binding_hash",
        "rendered_hash",
        "package_hash",
        "source_version",
    ):
        if left.get(key) != right.get(key):
            lines.append(f"{key}: {left.get(key)} != {right.get(key)}")
    if left.get("derived_from") != right.get("derived_from"):
        lines.append("derived_from changed")
    if not lines:
        lines.append("no manifest-level differences")
    return lines


def audit_project(project_path: str | Path) -> list[str]:
    root = Path(project_path) / "registry" / "derived" / "prompt-manifests"
    if not root.exists():
        return ["no prompt-manifests directory"]
    rows = []
    for path in sorted(root.glob("*.json")):
        try:
            view = manifest_view(path)
            rows.append(
                f"{path.name}: {view['prompt_id']}@{view['version']} "
                f"rendered={view['rendered_hash']} package={view['package_hash']}")
        except Exception as exc:
            rows.append(f"{path.name}: invalid ({exc})")
    return rows or ["no prompt manifests found"]

