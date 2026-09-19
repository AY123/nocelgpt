from __future__ import annotations

from pathlib import Path

import yaml

from .types import PromptVersion, sha256_text


class PromptLoader:
    def __init__(self, prompt_root: str | Path, *, mode: str = "frozen"):
        self.prompt_root = Path(prompt_root)
        self.mode = mode
        self._cache = {}

    def _path(self, prompt_id: str, version: str) -> Path:
        major = version.split(".", 1)[0]
        return self.prompt_root / f"{prompt_id}.v{major}.prompt.yaml"

    def load(self, prompt_id: str, version: str) -> PromptVersion:
        path = self._path(prompt_id, version)
        cache_key = (prompt_id, version)
        stat = path.stat()
        cached = self._cache.get(cache_key)
        if self.mode != "dev" and cached:
            return cached[1]
        if self.mode == "dev" and cached and cached[0] == stat.st_mtime_ns:
            return cached[1]

        raw = path.read_text(encoding="utf-8")
        data = yaml.safe_load(raw)
        variables = data.get("variables", {})
        pv = PromptVersion(
            prompt_id=data["prompt_id"],
            version=data["version"],
            capability=data["capability"],
            engine=data.get("engine", "format"),
            source_path=str(path),
            source_hash=sha256_text(raw),
            required_variables=list(variables.get("required", [])),
            optional_variables=list(variables.get("optional", [])),
            messages=list(data["messages"]),
        )
        self._cache[cache_key] = (stat.st_mtime_ns, pv)
        return pv

