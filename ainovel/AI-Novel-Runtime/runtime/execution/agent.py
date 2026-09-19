"""agent.py — ChapterDraftAgent (ANES v2, Phase 3).

Closes the execution loop: consumes a compiled Task Package, renders a prompt,
calls a Model, and emits a ChapterDraft — a DERIVED artifact (ADR-006), carrying
provenance that pins exactly the sources it came from. It does NOT write into
registry/facts/ (prose is not a fact).

This is the first real CONSUMER of a Task Package. Until now the package was a
build artifact; here it becomes an execution artifact, which is what makes the
capability contract (input + output) actually binding.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Optional

from ..prompt.runtime import PromptRuntime
from ..text_metrics import count_words as _count_words
from .model import Model, DeterministicModel, StreamEvent
from ..prompt.routing import route_generation

# Length measurement folds through the single runtime entry (text_metrics),
# imported above as _count_words: CJK prose is not whitespace-delimited, so a
# raw split() undercounts it; text_metrics counts each CJK char as one word.


ARTIFACT_FORMAT = "1.0"


def _canonical(obj) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True)


def _hash(obj) -> str:
    return "sha256:" + hashlib.sha256(_canonical(obj).encode("utf-8")).hexdigest()


# A model sometimes echoes its own self-check block into the prose tail — e.g.
# a "# 寻轨反馈\n  [PASS] 叙事强制令：… [PASS] 导演目标：…" checklist that belongs to
# the reviewer, not the chapter (RUN-00001 ch13: 5 [PASS] lines leaked into
# final_text and false-fired the anaphora detector). Strip such a trailing
# metadata block DETERMINISTICALLY so the persisted body is clean and replay
# reproduces the same hash. Conservative: only triggers when a run of [TAG]-style
# meta lines sits at the very end — real 玄幻 prose carries no "[PASS]" bracket
# tags, so a clean draft is byte-identical (untouched).
_META_TAIL_RE = re.compile(
    r"(?:\n\s*-{3,}\s*)?(?:\n\s*#+[^\n]*)?(?:\n\s*\[[A-Z]{2,}\][^\n]*)+\s*$")


def _strip_meta_tail(text: str) -> str:
    """Remove a trailing model self-check block (a run of `[TAG] …` lines, with an
    optional leading markdown heading like `# 寻轨反馈`). Only the tail is touched;
    prose with no such block is returned unchanged. A degenerate all-metadata body
    (nothing but tag lines) is returned as-is — the sanitizer never empties a draft
    nor leaves a half-stripped residue."""
    if "[PASS]" not in text and not re.search(r"\[[A-Z]{2,}\]", text):
        return text
    cleaned = _META_TAIL_RE.sub("", text).rstrip()
    # If what remains is empty or still nothing but [TAG] lines, the whole body was
    # metadata — keep the original rather than emit an empty/half-stripped draft.
    residue = "\n".join(l for l in cleaned.splitlines() if l.strip())
    if not residue or all(re.match(r"\s*\[[A-Z]{2,}\]", l)
                          for l in residue.splitlines() if l.strip()):
        return text
    return cleaned


def _llm_metadata(model) -> Optional[dict]:
    request = getattr(model, "last_request", None)
    response = getattr(model, "last_response", None)
    if request is None or response is None:
        return None
    return {
        "request_id": response.request_id,
        "provider": response.provider,
        "model": response.model,
        "model_pin": asdict(request.model_pin),
        "prompt_provenance": asdict(request.prompt_provenance),
        "token_usage": asdict(response.token_usage),
        "cost": asdict(response.cost) if response.cost else None,
        "latency_ms": response.latency_ms,
        "response_hash": response.response_hash,
        "provider_request_id": response.provider_request_id,
        "replay_ref": response.replay_ref,
        "finish_reason": response.finish_reason,
        "attempts": list(response.attempts),
    }


def render_prompt(package: dict) -> str:
    """Render a deterministic prompt from a Task Package envelope.

    Minimal prompt builder (a full PromptLoader with versioned templates is
    deferred per ROADMAP). Deterministic: same package => same prompt.
    """
    task = package["task"]
    lines = [
        f"# Task {task['task_id']}: {task['goal']}",
        f"# Capability: {task['capability']}",
        "# Context (facts to honor):",
    ]
    for type_code in package["context"]:
        for rec in package["context"][type_code]:
            name = rec.get("name", rec["id"])
            lines.append(f"- {rec['id']} ({type_code}): {name}")
            summary = rec.get("summary") or rec.get("statement")
            if summary:
                lines.append(f"    {summary}")
    return "\n".join(lines)


def _default_prompt_runtime() -> PromptRuntime:
    standard = Path(__file__).resolve().parents[3] / "AI-Novel-Standard"
    return PromptRuntime(prompt_root=standard / "contracts" / "prompts")


@dataclass
class ChapterDraftAgent:
    model: Model
    prompt_runtime: Optional[PromptRuntime] = None
    prompt_id: str = "chapter-draft"
    prompt_version: str = "1.0.0"
    model_profile: Optional[dict] = None
    constraint_pack: Optional[dict] = None
    task_type: Optional[str] = None
    target_style: Optional[str] = None
    known_failure_mode: Optional[str] = None
    # v2: optional sink for streaming events (forwarded to a UI/log).
    on_event: Optional[Callable[[StreamEvent], None]] = None
    last_prompt_manifest: object = field(default=None, init=False)
    # The rendered prompt is kept BESIDE the manifest, not folded into it: the
    # manifest is provenance (hashes only) and prompt-manifest.schema.json is
    # additionalProperties:false with no rendered_text slot (ADR-007). Callers
    # that need the actual prompt text read this instead.
    last_rendered_prompt: object = field(default=None, init=False)
    last_route: object = field(default=None, init=False)
    last_route_dict: object = field(default=None, init=False)

    @classmethod
    def with_deterministic_model(cls) -> "ChapterDraftAgent":
        return cls(model=DeterministicModel())

    def run(self, package: dict, *, variables: Optional[dict] = None) -> dict:
        """Produce a ChapterDraft artifact dict from a Task Package.

        The returned dict is the INNER, contract-conformant ChapterDraft (it
        validates against the frozen Standard schema). Prompt-manifest linkage
        rides in the on-disk envelope (see execution.envelope), not in this
        artifact — the Standard is frozen and seals every object.

        `variables` are optional runtime prompt overrides (e.g. a Novel Brain
        style directive fed to the `style` variable). When None, the prompt uses
        its defaults — so a project with no Brain produces a byte-identical draft.
        """
        runtime = self.prompt_runtime or _default_prompt_runtime()
        task = package.get("task", {})
        resolved_model_id = getattr(self.model, "model_id", task.get("model_id", "unknown"))
        resolved_provider = getattr(self.model, "provider", None)
        route = route_generation(
            model_id=resolved_model_id,
            provider=resolved_provider,
            task_type=self.task_type or task.get("capability"),
            target_style=self.target_style,
            known_failure_mode=self.known_failure_mode,
            prompt_version=self.prompt_version,
        )
        self.last_route = route
        route_dict = route.to_dict()
        self.last_route_dict = route_dict
        self.model_profile = self.model_profile or {
            "model_id": route.model_id,
            "provider": route.provider,
            "prompt_version": route.prompt_version,
            "constraint_pack_id": route.constraint_pack_id,
            "task_type": self.task_type or task.get("capability"),
            "target_style": self.target_style,
            "known_failure_mode": self.known_failure_mode,
            "rationale": route.rationale,
        }
        if self.constraint_pack is None:
            self.constraint_pack = {
                "constraint_pack_id": route.constraint_pack_id,
                "directives": [],
            }
        prompt_version = route.prompt_version or self.prompt_version
        routed_variables = dict(variables or {})
        routed_variables.setdefault(
            "model_profile_note",
            f"model={route_dict['model_id']}; provider={route_dict['provider'] or 'unknown'}; prompt_version={route_dict['prompt_version']}; pack={route_dict['constraint_pack_id'] or 'none'}",
        )
        routed_variables.setdefault(
            "constraint_pack_note",
            "; ".join(route_dict.get("metadata", {}).get("constraint_directives", []))
            or self.model_profile["rationale"],
        )
        routed_variables.setdefault("route_summary", route_dict)
        routed_variables.setdefault(
            "approved_state_constraints",
            variables.get("approved_state_constraints") if variables else None,
        )
        rendered_prompt, prompt_manifest = runtime.render(
            prompt_id=self.prompt_id,
            version=prompt_version,
            package=package,
            variables=routed_variables,
        )
        self.last_prompt_manifest = prompt_manifest
        self.last_rendered_prompt = rendered_prompt

        if hasattr(self.model, "generate_rendered"):
            # v2 RenderedModel: rendered.messages is the source of truth; the
            # manifest carries provenance. Streaming flows via on_event.
            output = self.model.generate_rendered(
                rendered_prompt, prompt_manifest, on_event=self.on_event)
        elif hasattr(self.model, "generate_for_package"):
            output = self.model.generate_for_package(
                package, rendered_prompt.rendered_text, prompt_manifest)
        else:
            output = self.model.generate(rendered_prompt.rendered_text)

        # HASHED CORE — only replay-stable fields. produced_by is EXCLUDED so the
        # inner draft's content_hash is byte-reproducible across a live call and
        # a later replay (volatile LM metadata lives in produced_by, below).
        core = {
            "artifact_format": ARTIFACT_FORMAT,
            "kind": "prose",
            "capability": "ChapterDraft",
            "task_id": package["task"]["task_id"],
            "provenance": {
                # pin to the package and to the exact source versions it carried
                "package_hash": package["content_hash"],
                "derived_from": list(package["provenance"]["derived_from"]),
                "source_version": package["provenance"]["source_version"],
            },
            "body": _strip_meta_tail(output.text),
        }
        artifact = dict(core)
        artifact["content_hash"] = _hash(core)
        artifact["word_count"] = _count_words(core["body"])

        # AUDIT — volatile, NOT hashed. Kept out of the core above.
        produced_by = {
            "model_id": output.model_id,
            "model_kind": output.model_kind,
        }
        llm_meta = _llm_metadata(self.model)
        if llm_meta is not None:
            produced_by["llm"] = llm_meta
        artifact["produced_by"] = produced_by
        return artifact


def serialize(artifact: dict) -> str:
    return _canonical(artifact) + "\n"
