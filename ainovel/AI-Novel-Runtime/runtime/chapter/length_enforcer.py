"""length_enforcer.py — Phase 1 Task 1.3.1: 生成后硬截断

解决问题：18/30章超长150%，prompt长度约束是软的、模型不遵守。

策略：在完整句处硬截断到目标+tolerance范围内。
"""
from __future__ import annotations
from typing import Optional
import re


def enforce_length_hard_limit(
    draft: dict,
    target: int,
    tolerance: float = 0.2,
    *,
    strict: bool = False
) -> dict:
    """生成后硬截断：在完整句处截断到目标长度。

    Args:
        draft: 章节草稿（包含body字段）
        target: 目标字数
        tolerance: 允许的超长比例（默认20%）
        strict: 严格模式（tolerance=0，精确截断到target）

    Returns:
        截断后的草稿（如果需要）或原草稿（未超长）

    Strategy:
        1. 检查是否超过hard_limit = target * (1 + tolerance)
        2. 如果未超长，原样返回
        3. 如果超长，在完整句处截断
        4. 标记truncated=True，记录原始长度

    Examples:
        >>> draft = {"body": "句子1。句子2。句子3。"}
        >>> enforce_length_hard_limit(draft, target=10, tolerance=0.2)
        # 如果body过长，会在完整句处截断
    """
    body = draft.get("body", "")
    if not body:
        return draft

    # Calculate actual word count (CJK-aware)
    word_count = _count_words_cjk(body)

    # Calculate hard limit
    if strict:
        hard_limit = target
    else:
        hard_limit = int(target * (1 + tolerance))

    # If within limit, return as-is
    if word_count <= hard_limit:
        return draft

    # Need truncation: find cutoff point at paragraph/sentence boundary.
    # Truncate at PARAGRAPH boundaries first so the reconstructed body keeps
    # its paragraph structure (the old path split on "\n" as a sentence
    # terminator and re-joined with "".join, collapsing every paragraph break —
    # a 115-paragraph chapter came out as a single line). Falls back to
    # sentence-level trimming within the final kept paragraph when a paragraph
    # alone overshoots.
    paragraphs = _split_paragraphs(body)
    if not paragraphs:
        return draft  # Edge case: no paragraphs found

    accumulated_words = 0
    cutoff_index = 0

    for i, paragraph in enumerate(paragraphs):
        paragraph_words = _count_words_cjk(paragraph)
        if accumulated_words + paragraph_words > hard_limit:
            break
        accumulated_words += paragraph_words
        cutoff_index = i + 1

    # Edge case: even the first paragraph exceeds limit — trim it at sentence
    # boundaries so we keep at least a coherent opening.
    if cutoff_index == 0:
        sentences = _split_sentences(paragraphs[0])
        if sentences:
            first = sentences[0]
            truncated_body = first
            accumulated_words = _count_words_cjk(first)
        else:
            truncated_body = paragraphs[0]
            accumulated_words = _count_words_cjk(paragraphs[0])
    else:
        # Reconstruct truncated body, preserving the "\n\n" paragraph breaks.
        truncated_body = "\n\n".join(paragraphs[:cutoff_index])

    # Return truncated draft with metadata
    return {
        **draft,
        "body": truncated_body,
        "truncated": True,
        "truncation_metadata": {
            "original_length": word_count,
            "truncated_length": accumulated_words,
            "target": target,
            "hard_limit": hard_limit,
            "paragraphs_kept": cutoff_index,
            "paragraphs_total": len(paragraphs),
        }
    }


def _count_words_cjk(text: str) -> int:
    """Count words in CJK-aware manner.

    Strategy:
        - CJK characters: each character is ~1 word
        - Latin words: space-separated tokens

    This matches the word count used in production (text_metrics.count_words_cjk).
    """
    if not text:
        return 0

    # Count CJK characters (each char ~1 word)
    cjk_chars = sum(1 for c in text if '一' <= c <= '鿿')

    # Count Latin words (space-separated, excluding CJK)
    latin_text = re.sub(r'[一-鿿]', ' ', text)  # Replace CJK with space
    latin_words = len([w for w in latin_text.split() if w.strip()])

    return cjk_chars + latin_words


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences at sentence-ending punctuation.

    Keeps the punctuation with each sentence. Newlines are preserved INSIDE
    each returned sentence (a paragraph break never ends a sentence), so a
    caller that re-joins with "".join keeps the original paragraph structure
    instead of collapsing the whole body into one line.
    """
    if not text:
        return []

    # Sentence-ending punctuation (Chinese + English). "\n" is deliberately
    # NOT a terminator: a paragraph break belongs to the sentence it follows.
    sentence_endings = re.compile(r'[。！？!?]+')

    sentences = []
    last_end = 0

    for match in sentence_endings.finditer(text):
        # Include everything from last_end to after this punctuation
        sentence = text[last_end:match.end()].strip()
        if sentence:
            sentences.append(sentence)
        last_end = match.end()

    # Don't forget trailing content (incomplete sentence)
    if last_end < len(text):
        trailing = text[last_end:].strip()
        if trailing:
            sentences.append(trailing)

    return sentences


def _split_paragraphs(text: str) -> list[str]:
    """Split text into paragraphs, preserving each paragraph's own text.

    A paragraph is a run of non-blank lines (separated by "\n" or "\n\n").
    Paragraph breaks are re-applied by the caller via "\n\n".join().
    """
    if not text:
        return []
    paragraphs = []
    current = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped:
            current.append(line.strip())
        elif current:
            paragraphs.append("".join(current))
            current = []
    if current:
        paragraphs.append("".join(current))
    return paragraphs


def should_enforce_length_limit(
    draft: dict,
    target: int,
    tolerance: float = 0.2
) -> bool:
    """Check if a draft needs length enforcement.

    Returns:
        True if draft exceeds target * (1 + tolerance)
    """
    body = draft.get("body", "")
    if not body:
        return False

    word_count = _count_words_cjk(body)
    hard_limit = int(target * (1 + tolerance))

    return word_count > hard_limit


def report_length_stats(draft: dict) -> dict:
    """Generate length statistics for a draft.

    Returns:
        Dictionary with word count, sentence count, avg sentence length
    """
    body = draft.get("body", "")
    if not body:
        return {
            "word_count": 0,
            "sentence_count": 0,
            "avg_sentence_length": 0.0
        }

    word_count = _count_words_cjk(body)
    sentences = _split_sentences(body)
    sentence_count = len(sentences)

    avg_length = word_count / sentence_count if sentence_count > 0 else 0.0

    return {
        "word_count": word_count,
        "sentence_count": sentence_count,
        "avg_sentence_length": round(avg_length, 1)
    }
