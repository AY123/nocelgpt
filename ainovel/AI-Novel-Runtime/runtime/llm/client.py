from __future__ import annotations

from dataclasses import replace
from typing import Optional

from .cost import CostCalculator
from .replay import ReplayStore
from .retry import RetryPolicy
from .types import (LLMRequest, LLMStreamEvent, TokenUsage, now_ms,
                    response_from_dict, sha256_obj)


class ManagedLLMClient:
    def __init__(
        self,
        adapter,
        *,
        retry_policy: Optional[RetryPolicy] = None,
        replay_store: Optional[ReplayStore] = None,
        cost_calculator: Optional[CostCalculator] = None,
    ):
        self.adapter = adapter
        self.retry_policy = retry_policy or RetryPolicy()
        self.replay_store = replay_store
        self.cost_calculator = cost_calculator

    def _price(self, response):
        """Set cost = f(token_usage, CURRENT pricing). Cost is a pure function of
        cached tokens times the live pricing table — NOT part of the replay key or
        the draft content_hash — so a REPLAYED response must be priced against the
        current table too, not frozen at whatever the table held when the response
        was first cached. Mirrors the live path exactly (adapters return cost=None;
        the managed client always prices). No calculator => cost untouched."""
        if not self.cost_calculator:
            return response
        return replace(
            response,
            cost=self.cost_calculator.calculate(
                response.provider, response.model, response.token_usage),
        )

    def generate(self, request: LLMRequest):
        request.temperature.validate()
        if self.replay_store:
            cached = self.replay_store.get(request)
            if cached:
                response = response_from_dict(cached["response"])
                response = replace(response, replay_ref=str(self.replay_store.path_for(request)))
                return self._price(response)

        response = self.retry_policy.run(lambda: self.adapter.generate(request))
        response = self._price(response)
        if self.replay_store:
            replay_ref = self.replay_store.put(request, response)
            response = replace(response, replay_ref=replay_ref)
        return response

    def stream(self, request: LLMRequest):
        request.temperature.validate()

        # Replay is a semantic reconstruction, not a transport: on a cache hit
        # we do NOT replay token deltas. We emit a single terminal `done` event
        # carrying the fully reconstructed response (Decision: replay is
        # semantically, not temporally, identical).
        if self.replay_store:
            cached = self.replay_store.get(request)
            if cached:
                response = response_from_dict(cached["response"])
                response = replace(
                    response, replay_ref=str(self.replay_store.path_for(request)))
                response = self._price(response)
                yield LLMStreamEvent(
                    request_id=request.request_id,
                    kind="done",
                    finish_reason=response.finish_reason,
                    response=response,
                )
                return

        # Live stream: forward deltas as they arrive and assemble the response
        # so it can be cost-priced, recorded for replay, and surfaced on `done`.
        started = now_ms()
        chunks = []
        usage = None
        finish_reason = "stop"
        for event in self.adapter.stream(request):
            if event.kind == "delta":
                chunks.append(event.text_delta)
                yield event
            elif event.kind == "usage" and event.token_usage is not None:
                usage = event.token_usage
                yield event
            elif event.kind == "error":
                yield event
                raise RuntimeError(event.error or "LLM stream failed")
            elif event.kind == "done":
                if event.finish_reason:
                    finish_reason = event.finish_reason
                if getattr(event, "response", None) is not None:
                    usage = event.response.token_usage
                # defer emitting our own terminal event until the response is built

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
        from .types import LLMResponse
        response = LLMResponse(
            request_id=request.request_id,
            provider=getattr(self.adapter, "provider", "unknown"),
            model=request.model_pin.model,
            text=text,
            finish_reason=finish_reason,
            token_usage=usage,
            cost=None,
            latency_ms=now_ms() - started,
            response_hash=sha256_obj({"text": text}),
            provider_request_id=None,
            replay_ref=None,
        )
        response = self._price(response)
        if self.replay_store:
            replay_ref = self.replay_store.put(request, response)
            response = replace(response, replay_ref=replay_ref)
        yield LLMStreamEvent(
            request_id=request.request_id,
            kind="done",
            finish_reason=response.finish_reason,
            response=response,
        )
