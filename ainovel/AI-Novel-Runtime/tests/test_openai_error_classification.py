"""test_openai_error_classification.py — 5xx must be retryable (real-model bug).

A real DeepSeek run returned a 503 "Service is too busy" InternalServerError.
The old adapter classified anything not named APIConnection/APITimeout/RateLimit
as PERMANENT, so the 503 was never retried — the commercial loop degraded on
provider overload with no retry. These tests pin: 5xx and 408/409/429 are
Transient (retryable), 4xx client errors stay Permanent.
"""
from __future__ import annotations

from runtime.llm.adapters.openai_compatible import _classify_openai_error
from runtime.llm.errors import TransientLLMError, PermanentLLMError


class _FakeSDKError(Exception):
    """Mimics an OpenAI-SDK error carrying an HTTP status_code."""
    def __init__(self, name: str, status_code=None):
        super().__init__(f"{name} error")
        self.__class__.__name__ = name  # spoof the class name the classifier reads
        if status_code is not None:
            self.status_code = status_code


def test_503_service_unavailable_is_transient():
    exc = _FakeSDKError("InternalServerError", status_code=503)
    assert isinstance(_classify_openai_error(exc), TransientLLMError)


def test_all_5xx_are_transient():
    for code in (500, 502, 503, 504):
        exc = _FakeSDKError("InternalServerError", status_code=code)
        assert isinstance(_classify_openai_error(exc), TransientLLMError), code


def test_429_and_408_and_409_are_transient():
    for code in (408, 409, 429):
        assert isinstance(_classify_openai_error(_FakeSDKError("X", code)),
                          TransientLLMError), code


def test_4xx_client_errors_stay_permanent():
    for code in (400, 401, 403, 404, 422):
        assert isinstance(_classify_openai_error(_FakeSDKError("BadRequestError", code)),
                          PermanentLLMError), code


def test_name_fallback_when_no_status_code():
    # connection/timeout/ratelimit are transient even without a status_code
    for name in ("APIConnectionError", "APITimeoutError", "RateLimitError",
                 "InternalServerError"):
        assert isinstance(_classify_openai_error(_FakeSDKError(name)), TransientLLMError), name
    # an unknown named error with no status is treated as permanent
    assert isinstance(_classify_openai_error(_FakeSDKError("WeirdError")), PermanentLLMError)
