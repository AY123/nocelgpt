"""refs.py — Reference Grammar parser (ANES v2).

Implements the single reference syntax from the Standard's Reference Grammar:

    <ref> ::= [<project-id>:] <id> [#<fragment>] [@<version>]

A reference is always a string scalar. This module is the one place references
are parsed; every other component depends on it (Schema-First, ADR-007).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

# Mirrors spec/01 + spec/02 in AI-Novel-Standard.
_REF_RE = re.compile(
    r"^(?:(?P<project>[a-z0-9-]{1,32}):)?"
    r"(?P<id>[A-Z]{3,4}-\d{5,})"
    r"(?:#(?P<fragment>[A-Za-z0-9_.\[\]-]+))?"
    r"(?:@(?P<version>v\d+|latest))?$"
)
_ID_RE = re.compile(r"^[A-Z]{3,4}-\d{5,}$")


@dataclass(frozen=True)
class Ref:
    """A parsed reference. `raw` is the original string."""
    raw: str
    id: str
    project: Optional[str] = None
    fragment: Optional[str] = None
    version: Optional[str] = None  # "v7" | "latest" | None (=> latest)

    @property
    def type_code(self) -> str:
        return self.id.split("-", 1)[0]

    @property
    def is_local(self) -> bool:
        return self.project is None

    @property
    def is_pinned(self) -> bool:
        return self.version is not None and self.version != "latest"

    @property
    def pinned_version(self) -> Optional[int]:
        if self.is_pinned:
            return int(self.version[1:])  # strip leading 'v'
        return None

    def key(self) -> str:
        """Identity used for de-duplication: project + id (ignores version/frag)."""
        return f"{self.project}:{self.id}" if self.project else self.id


def is_reference(value) -> bool:
    """True if `value` is a string that parses as a reference."""
    return isinstance(value, str) and bool(_REF_RE.match(value))


def parse(value: str) -> Ref:
    m = _REF_RE.match(value)
    if not m:
        raise ValueError(f"not a valid reference: {value!r}")
    return Ref(
        raw=value,
        id=m.group("id"),
        project=m.group("project"),
        fragment=m.group("fragment"),
        version=m.group("version"),
    )


def is_bare_id(value) -> bool:
    return isinstance(value, str) and bool(_ID_RE.match(value))
