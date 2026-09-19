from __future__ import annotations

from dataclasses import replace

from .errors import TransientLLMError
from .types import LLMRequest


class FallbackLLMClient:
    def __init__(self, clients: list[tuple[str, object]]):
        if not clients:
            raise ValueError("fallback chain requires at least one client")
        self.clients = clients

    def generate(self, request: LLMRequest):
        attempts = []
        last_error = None
        for name, client in self.clients:
            try:
                response = client.generate(request)
                attempts.append({"provider": name, "status": "ok"})
                return replace(response, attempts=attempts)
            except TransientLLMError as exc:
                last_error = exc
                attempts.append({
                    "provider": name,
                    "status": "transient_error",
                    "error": exc.__class__.__name__,
                })
        raise last_error

    def stream(self, request: LLMRequest):
        # Streaming fallback is intentionally conservative: fail over before
        # any stream is emitted would require provider-specific buffering.
        yield from self.clients[0][1].stream(request)

