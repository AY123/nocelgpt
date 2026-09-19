"""test_deepseek_error_classification.py — curl transport failures must retry.

RUN-00023 (full-stack 5ch) aborted on ch5 generation: a curl (28) "Operation
timed out" is a transport-level failure wrapped as RuntimeError(stderr) with NO
status_code, so the class-name check ("runtimeerror" lacks timeout/connection)
fell through to PermanentLLMError → no retry → the whole serial run died on a
single network blip. Same bug CLASS as the openai 5xx misclassification. These
pin: transport-level timeout/DNS/connection failures are Transient (retryable);
a genuine 4xx / bad-request stays Permanent.
"""
from __future__ import annotations

from runtime.llm.adapters.deepseek import _classify
from runtime.llm.errors import TransientLLMError, PermanentLLMError


def test_curl_28_timeout_is_transient():
    # the exact RUN-00023 signature: curl exit 28, no status_code
    exc = RuntimeError("curl: (28) Operation timed out after 120004 milliseconds "
                       "with 1 bytes received")
    assert isinstance(_classify(exc), TransientLLMError)


def test_dns_and_connection_failures_are_transient():
    for stderr in (
        "curl: (6) Could not resolve host: api.deepseek.com",
        "curl: (7) Failed to connect: Connection refused",
        "curl: (56) Recv failure: Connection reset by peer",
    ):
        assert isinstance(_classify(RuntimeError(stderr)), TransientLLMError), stderr


def test_http_5xx_and_429_still_transient():
    # the pre-existing status_code path must keep working
    for code in (500, 502, 503, 504, 408, 409, 429):
        err = RuntimeError(f"DeepSeek HTTP {code}: busy")
        err.status_code = code
        assert isinstance(_classify(err), TransientLLMError), code


def test_named_timeout_exception_still_transient():
    class TimeoutError(Exception):
        pass
    assert isinstance(_classify(TimeoutError("slow")), TransientLLMError)


def test_genuine_client_error_stays_permanent():
    # a 4xx bad-request with no transient marker must NOT become retryable
    err = RuntimeError("DeepSeek HTTP 400: invalid request body")
    err.status_code = 400
    assert isinstance(_classify(err), PermanentLLMError)


def test_unknown_non_transient_message_stays_permanent():
    # a message with none of the transient markers stays permanent (no over-catch)
    assert isinstance(_classify(RuntimeError("malformed schema field 'x'")),
                      PermanentLLMError)
