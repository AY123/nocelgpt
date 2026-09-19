from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Dict, List, Literal, Optional


RENDERER_VERSION = "1.0.0"


def canonical_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_obj(obj) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


def sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def to_dict(obj):
    return asdict(obj)


@dataclass(frozen=True)
class PromptVersion:
    prompt_id: str
    version: str
    capability: str
    engine: Literal["format", "plain"]
    source_path: str
    source_hash: str
    required_variables: List[str]
    optional_variables: List[str]
    messages: List[dict]


@dataclass(frozen=True)
class PromptVariable:
    name: str
    value: object
    source: str
    source_hash: Optional[str] = None


@dataclass(frozen=True)
class PromptBinding:
    variables: Dict[str, PromptVariable]

    def values(self) -> dict:
        return {k: v.value for k, v in self.variables.items()}

    def hash_payload(self) -> dict:
        return {k: to_dict(v) for k, v in sorted(self.variables.items())}


@dataclass(frozen=True)
class RenderedPrompt:
    prompt_id: str
    version: str
    rendered_text: str
    rendered_hash: str
    messages: List[dict]
    binding_hash: str
    template_hash: str


@dataclass(frozen=True)
class PromptManifest:
    prompt_id: str
    version: str
    capability: str
    template_hash: str
    binding_hash: str
    rendered_hash: str
    package_hash: str
    derived_from: List[str]
    source_version: int
    rendered_at: str
    renderer_version: str
    cache_hit: bool
    replay_ref: Optional[str] = None
    route_summary: Optional[dict] = None


def prompt_manifest_artifact(manifest: PromptManifest) -> dict:
    return {
        "artifact_format": "1.0",
        "kind": "prompt-manifest",
        "id": f"{manifest.prompt_id}-{manifest.version}-{manifest.rendered_hash.split(':', 1)[1][:16]}",
        "content_hash": manifest.rendered_hash,
        "provenance": {
            "package_hash": manifest.package_hash,
            "derived_from": list(manifest.derived_from),
            "source_version": manifest.source_version,
        },
        "manifest": to_dict(manifest),
    }
