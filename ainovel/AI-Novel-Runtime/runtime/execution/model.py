"""model.py — model adapter seam (ANES v2, ADR-005 resource path).

An agent consumes a Task Package and calls a Model to produce output. The model
is a swappable resource (ADR-005: { Registry, Prompt, Model, Tool, Memory }).

Two implementations:
  - DeterministicModel : no network, no API key — renders the package's facts
    into a stable prose stub. This lets the FULL execution loop run in CI and be
    byte-reproducible. Same package => same draft.
  - (real LLM adapters: ClaudeModel / OpenAIModel) plug in here behind the same
    `generate()` protocol. They are NOT implemented in this phase because the
    deterministic adapter is sufficient to prove the loop closes; a real adapter
    is a drop-in that returns model_kind="llm".

The agent never imports a concrete model — it depends on the Model protocol, so
swapping deterministic <-> real is a one-line change at the call site.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Protocol, runtime_checkable


@dataclass
class ModelOutput:
    text: str
    model_id: str
    model_kind: str   # "deterministic" | "llm"
    # v2: surfaced for audit; defaulted so DeterministicModel needs no change.
    finish_reason: str = "stop"
    attempts: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class StreamEvent:
    """A provider-agnostic streaming event the agent can forward to a UI/log.

    The execution layer never sees a vendor SDK's stream type — adapters below
    the ADR-005 boundary translate into this, and the agent forwards it via an
    `on_event` callback. In replay mode only a single `done` event is emitted
    (replay is a semantic reconstruction, not a transport — see ROADMAP)."""
    kind: str                              # "delta" | "done" | "error"
    text_delta: str = ""
    finish_reason: Optional[str] = None
    error: Optional[str] = None


OnEvent = Callable[[StreamEvent], None]


class Model(Protocol):
    def generate(self, prompt: str) -> ModelOutput: ...


@runtime_checkable
class RenderedModel(Protocol):
    """v2 capability: a model that consumes the rendered prompt + its manifest
    directly, rather than a flattened string. The agent feature-detects this
    (hasattr) exactly as it does for generate_for_package, so DeterministicModel
    (which only implements `generate`) keeps working unchanged.

    `rendered` and `manifest` are duck-typed (runtime.prompt.types.RenderedPrompt
    / PromptManifest) so this seam carries no import of the prompt subdomain."""

    def generate_rendered(
        self,
        rendered,
        manifest,
        *,
        on_event: Optional[OnEvent] = None,
    ) -> ModelOutput: ...


class DeterministicModel:
    """Renders a prompt into a stable, reproducible stub. For CI and for proving
    the execution loop without external dependencies."""

    model_id = "deterministic-stub-v1"
    model_kind = "deterministic"

    def generate(self, prompt: str) -> ModelOutput:
        # Pure function of the prompt: no randomness, no time, no I/O.
        # The "draft" simply echoes the structured prompt as prose-like lines,
        # which is enough for deterministic structural QA to act on.
        lines = [ln for ln in prompt.splitlines() if ln.strip()]
        body = "\n".join(lines)
        return ModelOutput(text=body, model_id=self.model_id,
                           model_kind=self.model_kind)
