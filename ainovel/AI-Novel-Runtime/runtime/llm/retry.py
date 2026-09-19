from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass

from .errors import TransientLLMError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay_seconds: float = 0.5

    def run(self, fn):
        last_error = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                return fn()
            except TransientLLMError as exc:
                last_error = exc
                if attempt == self.max_attempts:
                    logger.warning(
                        f"LLM request failed after {self.max_attempts} attempts: {exc}"
                    )
                    break
                # P1-3: Add jitter to avoid thundering herd
                base_delay = self.base_delay_seconds * (2 ** (attempt - 1))
                jitter = base_delay * 0.1 * (random.random() * 2 - 1)  # ±10% jitter
                delay = base_delay + jitter
                logger.info(
                    f"LLM request failed (attempt {attempt}/{self.max_attempts}), "
                    f"retrying in {delay:.2f}s: {exc.__class__.__name__}: {str(exc)[:100]}"
                )
                time.sleep(delay)
        raise last_error

