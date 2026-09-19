"""text_language.py — lightweight language/locale checks for prose.

This module provides deterministic heuristics for spotting language drift in
Chinese prose, such as long ASCII stretches or English-dominant paragraphs.
It is advisory only.
"""
from __future__ import annotations

from dataclasses import dataclass
import re

_ASCII_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9_'-]*")
_CHINESE_RE = re.compile(r"[\u4e00-\u9fff]")


@dataclass(frozen=True)
class LanguageMetrics:
    body_chars: int
    ascii_word_count: int
    chinese_char_count: int
    ascii_ratio: float
    chinese_ratio: float
    long_ascii_run: bool
    english_dominant: bool


def measure_text_language(text: str) -> LanguageMetrics:
    body_chars = len(text)
    ascii_words = len(_ASCII_WORD_RE.findall(text))
    chinese_chars = len(_CHINESE_RE.findall(text))
    nonspace = len("".join(text.split())) or 1
    ascii_ratio = ascii_words / max(nonspace, 1)
    chinese_ratio = chinese_chars / max(nonspace, 1)
    long_ascii_run = bool(re.search(r"[A-Za-z]{20,}", text))
    english_dominant = ascii_words > 0 and chinese_chars == 0
    return LanguageMetrics(
        body_chars=body_chars,
        ascii_word_count=ascii_words,
        chinese_char_count=chinese_chars,
        ascii_ratio=ascii_ratio,
        chinese_ratio=chinese_ratio,
        long_ascii_run=long_ascii_run,
        english_dominant=english_dominant,
    )
