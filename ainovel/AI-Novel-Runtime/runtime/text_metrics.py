from __future__ import annotations

import re

# The single text-measurement entry for the whole runtime. CJK prose is not
# whitespace-delimited, so str.split() massively undercounts a Chinese chapter
# (a full 2000-字 body splits into ~1 "word"). Every production path that needs
# a length — draft word_count, length gates, the reviser's short-draft
# heuristic, the length-fallback selector — must fold through here, never
# through a raw split(). (LLM token *estimation* in the adapters is a different
# concept and intentionally does not use these.)
#
# The CJK class covers ext-A, the BMP block, compatibility ideographs, ext-B+,
# and kana so mixed CJK input measures consistently. count_cjk_chars restricts
# to the common Han block used by the reviewer's min_chars gate.
_CJK_CLASS = r"㐀-䶿一-鿿豈-﫿\U00020000-\U0002ffff぀-ヿ"
_CJK_RE = re.compile(f"[{_CJK_CLASS}]")
_HAN_RE = re.compile(r"[一-鿿]")


def count_cjk_chars(text: str) -> int:
    """Count common Han characters only (the reviewer min_chars gate basis)."""
    return len(_HAN_RE.findall(text or ""))


def count_words(text: str) -> int:
    """Length in 'words': each CJK character counts as one, plus each
    whitespace-delimited run of the remaining (latin/number) text."""
    text = text or ""
    cjk = len(_CJK_RE.findall(text))
    non_cjk = len(_CJK_RE.sub(" ", text).split())
    return cjk + non_cjk
