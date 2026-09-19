"""Bridge from the unified LLM layer to the legacy execution Model protocol."""
from __future__ import annotations

from dataclasses import replace
import json
import os
from typing import Optional

from ..llm.adapters.openai_compatible import openai_model_pin
from ..llm.cost import CostCalculator
from ..llm.factory import (DEEPSEEK_BASE_URL, DEFAULT_PRICING, OPENAI_BASE_URL,
                           create_llm_client)
from ..llm.types import (LLMRequest, PromptMessage, PromptProvenance,
                         TemperatureContract, LLMResponse, TokenUsage,
                         new_request_id, now_ms, sha256_obj)
from .model import ModelOutput, StreamEvent


# The language register lock (两周清单 Week-1 item 1). The chapter-draft
# templates (v1-v10) each ship an ENGLISH system message describing the task
# (IR / director / character runtime …). Before this constant existed, that
# English system message set has_system=True in _request_from_rendered, so the
# Chinese DEFAULT_SYSTEM_PROMPT was NEVER prepended — the model received an
# all-English system prompt with no "write in Chinese" instruction, the
# deterministic root cause of the observed 中英文随机切换. This directive is
# therefore ALWAYS merged into the leading system message on the wire, whether
# or not the template supplied one. It does not touch the frozen template
# bytes or the prompt-manifest rendered_hash (computed at render time); it only
# shapes the wire messages (and thus the replay key, correctly — the request
# genuinely changed).
LANGUAGE_REGISTER_DIRECTIVE = (
    "语言要求（最高优先级）：本章正文必须全程使用简体中文写作，"
    "不得切换到英文语域，不得整句或整段使用英文；"
    "仅在原文设定确有的专有名词处可保留必要外文。"
    "请保持章节长度稳定，避免过短或过长的波动。"
)

DEFAULT_SYSTEM_PROMPT = (
    "你是专业的中文长篇网文写作助手。"
    "请始终使用中文输出，严格遵守已给事实，不要编造与上下文冲突的内容。"
    "请保持章节长度稳定，避免过短或过长的波动。"
)


def manifest_to_prompt_provenance(manifest) -> PromptProvenance:
    """ADR-005 seam: translate a prompt-domain PromptManifest into the
    llm-domain PromptProvenance. Prompt types stop here — the adapter layer
    never imports runtime.prompt. `rendered_at` is carried for audit but is
    excluded from the replay stable-hash by ReplayStore, so it cannot perturb
    replay determinism."""
    return PromptProvenance(
        prompt_id=manifest.prompt_id,
        prompt_hash=manifest.rendered_hash,
        template_id=manifest.prompt_id,
        template_version=manifest.version,
        package_hash=manifest.package_hash,
        derived_from=list(manifest.derived_from),
        rendered_at=manifest.rendered_at,
    )


class LLMExecutionModel:
    model_kind = "llm"

    def __init__(
        self,
        *,
        provider: str,
        model_id: str,
        temperature: float = 0.7,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        timeout_seconds: float = 120,
        replay_dir: Optional[str] = None,
        stream: bool = False,
    ):
        self.provider = provider
        self.primary_provider = provider.split(",", 1)[0].strip()
        # Preserve the CLI's historic default for every provider except the
        # 92code relay, whose configured default is independently selectable.
        self.model_id = (
            os.environ.get("CODE92_MODEL", "gpt-5.6-sol")
            if self.primary_provider == "92code" and model_id == "deepseek-v4-pro"
            else (
                os.environ.get("CC_VIBE_OPENAI_MODEL", "gpt-5.6-sol")
                if self.primary_provider == "cc-vibe-openai" and model_id == "deepseek-v4-pro"
                else model_id
            )
        )
        self.temperature = temperature
        self.top_p = top_p
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt
        self.timeout_seconds = timeout_seconds
        self.replay_dir = replay_dir
        self.stream = stream
        self.client = create_llm_client(provider, replay_dir=replay_dir)
        self.supports_structured_output = self.primary_provider == "claude"
        # The streaming paths assemble their own LLMResponse (the managed client
        # only prices the non-stream generate()), so price them here too or a
        # --stream run would report cost=None even for a priced model.
        self._cost_calculator = CostCalculator(DEFAULT_PRICING)

    def _api_base(self):
        if self.primary_provider == "deepseek":
            return DEEPSEEK_BASE_URL
        if self.primary_provider == "openai":
            return OPENAI_BASE_URL
        return None

    def _request(self, *, prompt: str, package: Optional[dict], prompt_manifest=None) -> LLMRequest:
        messages = [
            PromptMessage("system", self.system_prompt),
            PromptMessage("user", prompt),
        ]
        package_hash = "unknown"
        derived_from = []
        source_version = None
        if package is not None:
            package_hash = package["content_hash"]
            derived_from = list(package["provenance"]["derived_from"])
            source_version = str(package["provenance"]["source_version"])
        prompt_id = "legacy-execution-prompt"
        prompt_hash = sha256_obj([
            {"role": m.role, "content": m.content}
            for m in messages
        ])
        template_version = None
        rendered_at = "unknown"
        replay_ref = None
        if prompt_manifest is not None:
            prompt_id = prompt_manifest.prompt_id
            prompt_hash = prompt_manifest.rendered_hash
            template_version = prompt_manifest.version
            package_hash = prompt_manifest.package_hash
            derived_from = list(prompt_manifest.derived_from)
            rendered_at = prompt_manifest.rendered_at
            replay_ref = prompt_manifest.replay_ref
        request = LLMRequest(
            request_id=new_request_id(),
            capability=(package["task"]["capability"] if package else "ChapterDraft"),
            messages=messages,
            model_pin=openai_model_pin(
                provider=self.primary_provider,
                model=self.model_id,
                api_base=self._api_base(),
            ),
            temperature=TemperatureContract(temperature=self.temperature, top_p=self.top_p),
            timeout_seconds=self.timeout_seconds,
            max_output_tokens=self.max_tokens,
            prompt_provenance=PromptProvenance(
                prompt_id=prompt_id,
                prompt_hash=prompt_hash,
                template_id=prompt_id,
                template_version=template_version,
                package_hash=package_hash,
                derived_from=derived_from,
                rendered_at=rendered_at,
            ),
            metadata={
                "bridge": "execution.LLMExecutionModel",
                **({"source_version": source_version} if source_version else {}),
                **({"prompt_replay_ref": replay_ref} if replay_ref else {}),
            },
        )
        return request

    def generate(self, prompt: str) -> ModelOutput:
        request = self._request(prompt=prompt, package=None, prompt_manifest=None)
        self.last_request = request
        response = self._execute_request(request)
        # Plain generate() is used by outline agents and evaluative judges.  Keep
        # the same audit seam as generate_for_package/generate_rendered so their
        # archives can record request/response hashes, usage and cost status.
        self.last_response = response
        return ModelOutput(
            text=response.text,
            model_id=response.model,
            model_kind=self.model_kind,
            finish_reason=response.finish_reason,
            attempts=list(response.attempts),
        )

    def generate_structured(self, prompt: str, schema: dict, *,
                            tool_name: str = "submit_structured_result") -> ModelOutput:
        """Generate through a provider-enforced JSON schema when supported.

        Claude relays commonly ignore ``output_config`` but honor forced tool
        choice. The adapter translates these metadata fields into that wire
        protocol. Other providers keep using ``generate`` and never enter here.
        """
        request = self._request(prompt=prompt, package=None, prompt_manifest=None)
        request = replace(request, metadata={
            **request.metadata,
            "structured_output_schema": json.dumps(
                schema, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
            "structured_output_tool_name": tool_name,
        })
        self.last_request = request
        # Structured tool output is one terminal object. Use the managed
        # non-streaming path even when the surrounding CLI enables streaming,
        # so the Claude adapter can enforce and extract the tool schema.
        response = self.client.generate(request)
        self.last_response = response
        return ModelOutput(
            text=response.text,
            model_id=response.model,
            model_kind=self.model_kind,
            finish_reason=response.finish_reason,
            attempts=list(response.attempts),
        )

    def generate_for_package(self, package: dict, prompt: str, prompt_manifest=None) -> ModelOutput:
        request = self._request(
            prompt=prompt, package=package, prompt_manifest=prompt_manifest)
        response = self._execute_request(request)
        self.last_request = request
        self.last_response = response
        return ModelOutput(
            text=response.text,
            model_id=response.model,
            model_kind=self.model_kind,
        )

    # ---- v2 primary path: RenderedPrompt + PromptManifest -------------------
    def _request_from_rendered(self, rendered, manifest) -> LLMRequest:
        """Build an LLMRequest whose wire payload IS rendered.messages (the
        single source of truth) and whose provenance is the manifest projection.
        The Chinese language-register directive is ALWAYS merged into the
        leading system message (前置), whether or not the template supplied a
        system message — the templates ship an English task system prompt that
        would otherwise be the ONLY system instruction, causing 语域漂移. When
        the template has no system message, the full static system prompt is
        prepended instead (which already carries the language lock)."""
        messages = []
        template_system = next(
            (m for m in rendered.messages if m["role"] == "system"), None)
        if template_system is None:
            # No template system message: the static system prompt already
            # carries the language lock, so use it as-is.
            messages.append(PromptMessage("system", self.system_prompt))
            for m in rendered.messages:
                messages.append(PromptMessage(m["role"], m["content"]))
        else:
            # Template supplied a (historically English) system message: prepend
            # the language directive to it so the register lock leads the wire
            # system prompt, then keep the remaining messages in order.
            for m in rendered.messages:
                if m is template_system:
                    merged = f"{LANGUAGE_REGISTER_DIRECTIVE}\n\n{m['content']}"
                    messages.append(PromptMessage("system", merged))
                else:
                    messages.append(PromptMessage(m["role"], m["content"]))
        return LLMRequest(
            request_id=new_request_id(),
            capability=manifest.capability,
            messages=messages,
            model_pin=openai_model_pin(
                provider=self.primary_provider,
                model=self.model_id,
                api_base=self._api_base(),
            ),
            temperature=TemperatureContract(temperature=self.temperature, top_p=self.top_p),
            timeout_seconds=self.timeout_seconds,
            max_output_tokens=self.max_tokens,
            prompt_provenance=manifest_to_prompt_provenance(manifest),
            metadata={
                "bridge": "execution.LLMExecutionModel.generate_rendered",
                "source_version": str(manifest.source_version),
                **({"prompt_replay_ref": manifest.replay_ref}
                   if manifest.replay_ref else {}),
            },
        )

    def generate_rendered(self, rendered, manifest, *, on_event=None) -> ModelOutput:
        request = self._request_from_rendered(rendered, manifest)
        if self.stream:
            response = self._stream_request(request, on_event)
        else:
            response = self.client.generate(request)
            if on_event is not None:
                on_event(StreamEvent(kind="done", finish_reason=response.finish_reason))
        self.last_request = request
        self.last_response = response
        return ModelOutput(
            text=response.text,
            model_id=response.model,
            model_kind=self.model_kind,
            finish_reason=response.finish_reason,
            attempts=list(response.attempts),
        )

    def _stream_request(self, request: LLMRequest, on_event) -> LLMResponse:
        """Consume a provider stream into a terminal LLMResponse, forwarding
        deltas via on_event. In replay mode there is no live stream: the managed
        client serves the cached response, which surfaces as a single terminal
        event (Decision: replay is semantically, not temporally, identical)."""
        started = now_ms()
        chunks = []
        usage = None
        final_response = None
        finish_reason = "stop"
        for event in self.client.stream(request):
            if event.kind == "delta":
                chunks.append(event.text_delta)
                if on_event is not None:
                    on_event(StreamEvent(kind="delta", text_delta=event.text_delta))
            elif event.kind == "usage" and event.token_usage is not None:
                usage = event.token_usage
            elif event.kind == "done":
                final_response = getattr(event, "response", None)
                if getattr(event, "finish_reason", None):
                    finish_reason = event.finish_reason
            elif event.kind == "error":
                if on_event is not None:
                    on_event(StreamEvent(kind="error", error=event.error))
                raise RuntimeError(event.error or "LLM stream failed")

        # Replay path: the managed client returned a reconstructed final response
        # as the terminal event instead of token deltas.
        if final_response is not None:
            if on_event is not None:
                on_event(StreamEvent(kind="done",
                                     finish_reason=final_response.finish_reason))
            return final_response

        text = "".join(chunks).strip()
        if on_event is not None:
            on_event(StreamEvent(kind="done", finish_reason=finish_reason))
        if usage is None:
            input_tokens = sum(len(m.content.split()) for m in request.messages)
            output_tokens = len(text.split())
            usage = TokenUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
                usage_estimated=True,
            )
        return LLMResponse(
            request_id=request.request_id,
            provider=self.primary_provider,
            model=request.model_pin.model,
            text=text,
            finish_reason=finish_reason,
            token_usage=usage,
            cost=self._cost_calculator.calculate(
                self.primary_provider, request.model_pin.model, usage),
            latency_ms=now_ms() - started,
            response_hash=sha256_obj({"text": text}),
            provider_request_id=None,
            replay_ref=None,
        )

    def _execute_request(self, request: LLMRequest) -> LLMResponse:
        if not self.stream:
            return self.client.generate(request)

        started = now_ms()
        chunks = []
        usage = None
        for event in self.client.stream(request):
            if event.kind == "delta":
                chunks.append(event.text_delta)
            elif event.kind == "usage" and event.token_usage is not None:
                usage = event.token_usage
            elif event.kind == "error":
                raise RuntimeError(event.error or "LLM stream failed")
        text = "".join(chunks).strip()
        if usage is None:
            input_tokens = sum(len(m.content.split()) for m in request.messages)
            output_tokens = len(text.split())
            usage = TokenUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
                usage_estimated=True,
            )
        return LLMResponse(
            request_id=request.request_id,
            provider=self.primary_provider,
            model=request.model_pin.model,
            text=text,
            finish_reason="stop",
            token_usage=usage,
            cost=self._cost_calculator.calculate(
                self.primary_provider, request.model_pin.model, usage),
            latency_ms=now_ms() - started,
            response_hash=sha256_obj({"text": text}),
            provider_request_id=None,
            replay_ref=None,
        )
