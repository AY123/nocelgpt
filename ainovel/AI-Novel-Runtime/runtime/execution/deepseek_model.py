"""Backward-compatible DeepSeek execution Model bridge."""
from __future__ import annotations

from typing import Optional

from .llm_model import DEFAULT_SYSTEM_PROMPT, LLMExecutionModel


DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-v4-pro"
DEFAULT_SYSTEM_PROMPT = (
    "You are a professional long-form fiction drafting assistant. "
    "Write prose that strictly honors the provided facts. Do not invent facts "
    "that contradict the context."
)


class DeepSeekModel(LLMExecutionModel):
    def __init__(
        self,
        *,
        model_id: str = DEFAULT_MODEL,
        api_key: Optional[str] = None,
        base_url: str = DEFAULT_BASE_URL,
        temperature: float = 0.7,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        timeout_seconds: float = 120,
        replay_dir: Optional[str] = None,
        stream: bool = False,
    ):
        if api_key is not None or base_url != DEFAULT_BASE_URL:
            raise RuntimeError(
                "DeepSeekModel bridge reads DEEPSEEK_API_KEY from environment "
                "and uses the runtime.llm factory; custom api_key/base_url should "
                "be configured in the unified LLM layer.")
        super().__init__(
            provider="deepseek",
            model_id=model_id,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            system_prompt=system_prompt,
            timeout_seconds=timeout_seconds,
            replay_dir=replay_dir,
            stream=stream,
        )
