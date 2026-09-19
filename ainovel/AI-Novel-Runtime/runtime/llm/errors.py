class LLMError(Exception):
    pass


class TransientLLMError(LLMError):
    pass


class PermanentLLMError(LLMError):
    pass


class AuthLLMError(PermanentLLMError):
    pass


class RateLimitLLMError(TransientLLMError):
    pass


class TimeoutLLMError(TransientLLMError):
    pass


class ContentFilterLLMError(PermanentLLMError):
    pass


class InvalidRequestLLMError(PermanentLLMError):
    pass


class ProviderUnavailableLLMError(TransientLLMError):
    pass


class UnsupportedProviderError(PermanentLLMError):
    pass
