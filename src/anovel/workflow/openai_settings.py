"""Read local OpenAI settings as data and match them to the frozen Writer policy."""

from __future__ import annotations

import os
import shlex
import stat
from pathlib import Path

from anovel.gateway.models import OPENAI_RESPONSES_ENDPOINT, ModelPolicy

from .models import WorkflowError

_SETTINGS_LIMIT = 65_536


def _settings(path: Path, names: set[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        descriptor = os.open(
            path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC
        )
        with os.fdopen(descriptor, "rb") as stream:
            info = os.fstat(stream.fileno())
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_uid != os.getuid()
                or info.st_nlink != 1
                or stat.S_IMODE(info.st_mode) & 0o077
                or info.st_size > _SETTINGS_LIMIT
            ):
                raise ValueError
            raw = stream.read(_SETTINGS_LIMIT + 1)
            if len(raw) > _SETTINGS_LIMIT:
                raise ValueError
        for line in raw.decode("utf-8-sig").splitlines():
            key, equal, value = line.strip().removeprefix("export ").partition("=")
            key = key.strip()
            if not equal or key not in names:
                continue
            tokens = shlex.split(value, comments=True)
            if key in values or len(tokens) != 1 or not tokens[0]:
                raise ValueError
            values[key] = tokens[0]
        if set(values) != names:
            raise ValueError
        return values
    except (OSError, ValueError):
        raise WorkflowError("OPENAI_ENV_INVALID_OR_UNAVAILABLE") from None


def _match_policy(settings: dict[str, str], policy: ModelPolicy) -> None:
    endpoint = settings["OPENAI_BASE_URL"].rstrip("/") + "/responses"
    if (
        policy.test_mode
        or endpoint != OPENAI_RESPONSES_ENDPOINT
        or policy.endpoint != endpoint
        or policy.model != settings["OPENAI_MODEL"]
    ):
        raise WorkflowError("OPENAI_ENV_POLICY_MISMATCH")


def check_openai_env(path: Path, policy: ModelPolicy) -> None:
    """Validate public selectors without parsing a credential value."""
    _match_policy(_settings(path, {"OPENAI_BASE_URL", "OPENAI_MODEL"}), policy)


def read_openai_credential(path: Path, policy: ModelPolicy) -> str:
    """Check selectors again and read the key inside the admitted dispatch."""
    settings = _settings(path, {"OPENAI_BASE_URL", "OPENAI_MODEL", "OPENAI_API_KEY"})
    _match_policy(settings, policy)
    key = settings["OPENAI_API_KEY"]
    if (
        not key.startswith("sk-")
        or len(key) <= len("sk-proj-")
        or any(value.isspace() or ord(value) < 32 or ord(value) == 127 for value in key)
    ):
        raise WorkflowError("OPENAI_ENV_CREDENTIAL_INVALID")
    return key
