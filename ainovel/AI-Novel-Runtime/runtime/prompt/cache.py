from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .types import PromptManifest, RenderedPrompt, sha256_obj, to_dict


class PromptCache:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def key(self, *, prompt_id: str, version: str, template_hash: str,
            binding_hash: str) -> str:
        return sha256_obj({
            "prompt_id": prompt_id,
            "version": version,
            "template_hash": template_hash,
            "binding_hash": binding_hash,
        })

    def path_for_key(self, key: str) -> Path:
        return self.root / f"{key.replace(':', '_')}.json"

    def get(self, key: str) -> Optional[dict]:
        path = self.path_for_key(key)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def put(self, key: str, rendered: RenderedPrompt, manifest: PromptManifest) -> str:
        path = self.path_for_key(key)
        payload = {
            "cache_key": key,
            "rendered": to_dict(rendered),
            "manifest": to_dict(manifest),
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
                        encoding="utf-8")
        return str(path)

