from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import json
from jsonschema import Draft202012Validator

from .binding import bind_chapter_draft
from .cache import PromptCache
from .loader import PromptLoader
from .renderer import render_template
from .types import (PromptBinding, PromptManifest, RenderedPrompt,
                    RENDERER_VERSION, to_dict)


class PromptRuntime:
    def __init__(
        self,
        *,
        prompt_root: str | Path,
        cache_root: str | Path | None = None,
        manifest_schema: str | Path | None = None,
        mode: str = "frozen",
    ):
        self.loader = PromptLoader(prompt_root, mode=mode)
        self.cache = PromptCache(cache_root) if cache_root else None
        self._manifest_validator = None
        if manifest_schema is None:
            root = Path(prompt_root)
            candidate = root.parent / "prompt-manifest.schema.json"
            manifest_schema = candidate if candidate.exists() else None
        if manifest_schema:
            schema = json.loads(Path(manifest_schema).read_text(encoding="utf-8"))
            self._manifest_validator = Draft202012Validator(schema)

    def validate_manifest(self, manifest: PromptManifest) -> list[str]:
        if self._manifest_validator is None:
            return []
        errors = []
        for err in sorted(self._manifest_validator.iter_errors(to_dict(manifest)),
                          key=lambda e: list(e.path)):
            loc = "/".join(str(p) for p in err.path) or "(root)"
            errors.append(f"{loc}: {err.message}")
        return errors

    def bind(self, prompt_id: str, package: dict, variables: Optional[dict]) -> PromptBinding:
        if prompt_id == "chapter-draft":
            return bind_chapter_draft(package, variables)
        raise ValueError(f"unknown prompt_id {prompt_id!r}")

    def render(
        self,
        *,
        prompt_id: str,
        version: str,
        package: dict,
        variables: Optional[dict] = None,
    ) -> tuple[RenderedPrompt, PromptManifest]:
        prompt = self.loader.load(prompt_id, version)
        binding = self.bind(prompt_id, package, variables)
        rendered = render_template(prompt, binding)
        key = None
        if self.cache:
            key = self.cache.key(
                prompt_id=rendered.prompt_id,
                version=rendered.version,
                template_hash=rendered.template_hash,
                binding_hash=rendered.binding_hash,
            )
            cached = self.cache.get(key)
            if cached:
                cached_manifest = dict(cached["manifest"])
                cached_manifest.setdefault(
                    "source_version", package["provenance"]["source_version"])
                manifest = PromptManifest(**cached_manifest)
                errs = self.validate_manifest(manifest)
                if errs:
                    raise ValueError("prompt manifest contract failed: " + "; ".join(errs))
                return rendered, replace(manifest, cache_hit=True,
                                         replay_ref=str(self.cache.path_for_key(key)))

        manifest = PromptManifest(
            prompt_id=rendered.prompt_id,
            version=rendered.version,
            capability=prompt.capability,
            template_hash=rendered.template_hash,
            binding_hash=rendered.binding_hash,
            rendered_hash=rendered.rendered_hash,
            package_hash=package["content_hash"],
            derived_from=list(package["provenance"]["derived_from"]),
            source_version=package["provenance"]["source_version"],
            rendered_at=datetime.now(timezone.utc).isoformat(),
            renderer_version=RENDERER_VERSION,
            cache_hit=False,
            replay_ref=None,
            route_summary=variables.get("route_summary") if variables else None,
        )
        errs = self.validate_manifest(manifest)
        if errs:
            raise ValueError("prompt manifest contract failed: " + "; ".join(errs))
        if self.cache and key:
            replay_ref = self.cache.put(key, rendered, manifest)
            manifest = replace(manifest, replay_ref=replay_ref)
            errs = self.validate_manifest(manifest)
            if errs:
                raise ValueError("prompt manifest contract failed: " + "; ".join(errs))
        return rendered, manifest
