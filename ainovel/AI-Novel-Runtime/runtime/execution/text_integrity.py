"""text_integrity.py — deterministic text-integrity gate for chapter prose.

R2-a: a hard gate that blocks drafts whose text was broken by finalize / rewrite /
postprocess steps. It is intentionally narrow: it does not score prose quality,
commercial strength, hook power, or AI taste. It only answers whether the body
still looks like continuous natural text.

Detection strategy:
  - rule scan for obvious mid-word / mid-phrase break markers
  - structural scan for suspicious newline-in-word / punctuation splits
  - optional raw-vs-final alignment to attribute finalize corruption

The gate is conservative: ambiguous cases return `not_assessed` or
`review_required` rather than overfiring on normal paragraphing.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import List, Optional

from .draft_review import ReviewFinding, ReviewReport

TEXT_INTEGRITY_REVIEWER_ID = "text-integrity-gate-v1"
LANGUAGE_DRIFT_REVIEWER_ID = "language-drift-gate-v1"


class TextIntegrityBlockError(RuntimeError):
    """Exception raised when critical text integrity issues block chapter finalization.

    Used in Phase 1 Task 1.1.2 to enforce hard gates on text quality.
    """
    def __init__(self, chapter_id: str, issues: list):
        self.chapter_id = chapter_id
        self.issues = issues
        message = (
            f"Chapter {chapter_id} blocked by {len(issues)} critical text integrity issue(s). "
            f"Issues: {[i.check for i in issues]}"
        )
        super().__init__(message)


# A genuine word-split orphans a VERY SHORT fragment line (1-2 chars) above a
# blank line — e.g. "车\n\n祸来了" where the word 车祸 was broken by a finalize/
# rewrite step. A markdown heading ("# Chapter 1\n\n…", "# 第一章\n\n…") or a
# normal paragraph leaves a LONG line, or one ending in sentence punctuation,
# before the blank line. word_split is judged on the PRECEDING physical LINE,
# not on the 1-2 chars adjacent to the newlines; the old adjacency regex
# blocked 100% of real chapters that start with a heading (A7 live baseline
# finding, 2026-07-14).
_BLANK_LINE_RE = re.compile(r"\n[ \t\u00a0]*\n")
# A heading line is either markdown (#\u2026) or a Chinese web-novel chapter/volume
# title (\u7b2cN\u7ae0/\u8282/\u5377\u2026, \u5e8f\u7ae0, \u6954\u5b50, \u5c3e\u58f0) \u2014 short, standalone, and legitimately
# followed by a paragraph break, so none of the three checks should fire on it.
_HEADING_RE = re.compile(
    r"^\s{0,3}(?:#{1,6}\s"
    r"|\u7b2c[0-9\u96f6\u4e00\u4e8c\u4e09\u56db\u4e94\u516d\u4e03\u516b\u4e5d\u5341\u767e\u5343\u4e24]+[\u7ae0\u8282\u7bc0\u56de\u5377\u90e8\u7bc7\u6298]"
    r"|\u5e8f\u7ae0|\u6954\u5b50|\u5c3e\u58f0|\u5c3e\u8072|\u540e\u8bb0|\u5f8c\u8a18|\u756a\u5916)"
)
_FRAGMENT_MAX = 2  # a broken token orphans a 1-2 char fragment line


def _line_at(body: str, pos: int) -> str:
    """The physical line (stripped) that position `pos` falls on."""
    line_start = body.rfind("\n", 0, pos) + 1
    end = body.find("\n", pos)
    if end == -1:
        end = len(body)
    return body[line_start:end].strip()


def _is_heading(line: str) -> bool:
    return bool(_HEADING_RE.match(line))


# A chapter-END marker line the model legitimately writes into the body —
# （第一章 完）, （本章完）, （未完待续）, ——全文完—— and the like. The space
# inside 第一章 完 is normal marker layout, NOT serialization word-splitting, so
# _WORD_JOIN_RE must skip a line that is such a marker — the same heading-
# exclusion discipline that keeps word_split from firing on 第一章 titles. Kept
# narrow: a short standalone bracketed/dashed line ending in 完/续/结束/完结.
_CHAPTER_END_MARKER_RE = re.compile(
    r"^[\s（(【\[—\-]*"  # P0-4: Use raw string to avoid \s escape sequence warning
    r"(?:第[0-9零一-鿿]+[章节節回]\s*)?"
    r"(?:本章|全文|全书|全書)?"
    r"(?:完|未完待续|未完待續|待续|待續|结束|完结|完結)"
    r"[\s）)】\]—\-。.]*$"
)


def _is_chapter_end_marker(line: str) -> bool:
    return bool(_CHAPTER_END_MARKER_RE.match(line.strip()))


# A scene-divider line the model legitimately writes to separate scenes within a
# chapter — a bare 井号 (#, not markdown heading which needs "# "), a dash run
# (——/—/---), a symbol row (***, ===, ◇◆◇, ＊, ·····), or 星号/中点 fills. These
# are layout, NOT a serialization word-split: a short standalone divider line
# orphaned by blank lines otherwise trips word_split (a GATING check → blocks the
# whole chapter). Same exclusion discipline as _is_heading / _is_chapter_end_marker.
# 3rd instance of this false-positive class (heading = A7, chapter-end = 48f6459,
# scene-divider = here). Kept narrow: a short line made ONLY of divider glyphs.
_SCENE_DIVIDER_RE = re.compile(r"^[#*=＊·・.。—\-–—_~〜※◇◆○●□■☆★\s]{1,20}$")


def _is_scene_divider(line: str) -> bool:
    s = line.strip()
    # must contain at least one glyph (not pure whitespace) and no CJK/latin words
    return bool(s) and bool(_SCENE_DIVIDER_RE.match(s))
_DOUBLE_NEWLINE_WORD_RE = re.compile(r"(?<![。！？!?])([A-Za-z0-9\u4e00-\u9fff])\s*\n\s*\n\s*([A-Za-z0-9\u4e00-\u9fff])")
_WORD_JOIN_RE = re.compile(r"[\u4e00-\u9fff][\s\u00a0]+[\u4e00-\u9fff]")
_SENTENCE_END_RE = re.compile(r"[。！？!?…]$|\n+$")


@dataclass(frozen=True)
class TextIntegrityFinding:
    check: str
    severity: str
    message: str
    start: Optional[int] = None
    end: Optional[int] = None

    def to_review(self) -> ReviewFinding:
        return ReviewFinding(self.check, self.severity, self.message)


@dataclass(frozen=True)
class TextIntegrityReport:
    reviewer: str = TEXT_INTEGRITY_REVIEWER_ID
    axis: str = "gate"
    gating: bool = True
    status: str = "not_assessed"   # pass | fail | review_required | not_assessed
    reason_codes: list[str] = field(default_factory=list)
    evidence_spans: list[dict] = field(default_factory=list)
    severity: str = "low"
    action: str = "allow"          # allow | block | require_review
    findings: list[TextIntegrityFinding] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "reviewer": self.reviewer,
            "axis": self.axis,
            "gating": self.gating,
            "status": self.status,
            "reason_codes": list(self.reason_codes),
            "evidence_spans": list(self.evidence_spans),
            "severity": self.severity,
            "action": self.action,
            "findings": [f.__dict__ for f in self.findings],
        }


def _span(text: str, start: int, end: int) -> dict:
    return {"start": start, "end": end, "context": text[max(0, start - 8): min(len(text), end + 8)]}


_ASCII_WORD_RE = re.compile(r"[A-Za-z]{4,}")
_GATING_PATTERNS = {
    "reader_signal": re.compile(r"reader[_\s-]?signal", re.I),
    "platform_feedback": re.compile(r"platform[_\s-]?feedback", re.I),
}


def _simple_sentences(text: str) -> list[str]:
    """Simple sentence splitter for cross-chapter checks.

    Split on sentence-ending punctuation, keeping the punctuation with the sentence.
    """
    if not text:
        return []

    # Split on sentence endings, but keep track of what ended where
    # Use finditer to keep punctuation marks
    sentences = []
    last_end = 0

    for match in re.finditer(r'[。！？!?]+', text):
        # Include everything from last_end to after this punctuation
        sentence = text[last_end:match.end()].strip()
        if sentence and not sentence.startswith('#'):
            sentences.append(sentence)
        last_end = match.end()

    # Don't forget the trailing part (if any) - this would be incomplete
    if last_end < len(text):
        trailing = text[last_end:].strip()
        if trailing and not trailing.startswith('#'):
            sentences.append(trailing)

    return sentences


def check_cross_chapter_continuity(
    current_body: str,
    previous_body: str | None
) -> list[TextIntegrityFinding]:
    """Check for sentence splits across chapter boundaries.

    Detects:
    1. Previous chapter ends with incomplete sentence
    2. Current chapter begins by continuing previous chapter's sentence

    Returns critical findings if cross-chapter split detected.
    """
    findings: list[TextIntegrityFinding] = []

    if not previous_body or not current_body:
        return findings  # No cross-chapter check possible

    # Extract last sentence of previous chapter (last 200 chars for context)
    prev_tail = previous_body.strip()[-200:] if len(previous_body.strip()) > 200 else previous_body.strip()
    prev_sentences = _simple_sentences(prev_tail)

    if not prev_sentences:
        return findings

    last_sentence = prev_sentences[-1].strip()

    # Check if last sentence is incomplete (no sentence-ending punctuation)
    if last_sentence and not _SENTENCE_END_RE.search(last_sentence):
        findings.append(TextIntegrityFinding(
            check="cross_chapter_continuity",
            severity="critical",
            message=f"Previous chapter ends with incomplete sentence: 「{last_sentence[-50:]}」",
            start=len(previous_body) - len(last_sentence),
            end=len(previous_body)
        ))

    # Extract first sentence of current chapter (first 200 chars for context)
    curr_head = current_body.strip()[:200] if len(current_body.strip()) > 200 else current_body.strip()
    curr_sentences = _simple_sentences(curr_head)

    if not curr_sentences:
        return findings

    first_sentence = curr_sentences[0].strip()

    # Check if first sentence continues the last sentence of previous chapter
    # (lowercase continuation without capitalization/subject, or shared n-gram)
    if first_sentence and last_sentence:
        # Heuristic: if first sentence starts lowercase in latin script, likely continuation
        if first_sentence[0].islower() and first_sentence[0].isalpha():
            findings.append(TextIntegrityFinding(
                check="cross_chapter_sentence_split",
                severity="critical",
                message=f"Current chapter begins with sentence continuation. Prev: 「{last_sentence[-30:]}」 Curr: 「{first_sentence[:30]}」",
                start=0,
                end=len(first_sentence)
            ))

        # Check for semantic continuation: shared 3-gram at boundary
        prev_tail_chars = ''.join(last_sentence.split())[-6:] if len(''.join(last_sentence.split())) >= 6 else ''
        curr_head_chars = ''.join(first_sentence.split())[:6] if len(''.join(first_sentence.split())) >= 6 else ''

        if prev_tail_chars and curr_head_chars and len(prev_tail_chars) >= 3:
            # Look for shared n-grams (3+ chars)
            for n in range(3, min(len(prev_tail_chars), len(curr_head_chars)) + 1):
                if prev_tail_chars[-n:] == curr_head_chars[:n]:
                    findings.append(TextIntegrityFinding(
                        check="cross_chapter_sentence_split",
                        severity="critical",
                        message=f"Detected sentence split across chapters (shared boundary: '{prev_tail_chars[-n:]}'). Prev: 「{last_sentence[-40:]}」 Curr: 「{first_sentence[:40]}」",
                        start=0,
                        end=len(first_sentence)
                    ))
                    break

    return findings


def check_word_internal_punctuation(body: str) -> list[TextIntegrityFinding]:
    """Detect punctuation inside words (e.g., '晶矿。城' instead of '晶矿城').

    Real word-internal punctuation happens when serialization breaks a word:
    - "晶矿。城" (should be "晶矿城")
    - "大喊！声" (should be "大喊声")

    We MUST exclude legitimate sentence boundaries:
    - "晶矿城。这是..." (period ends sentence)

    Approach: Improved heuristics without external dependencies.
    - For Chinese: Use expanded sentence-starter whitelist (100+ common chars)
    - For English: Use strict word-boundary detection
    - High threshold for reporting to minimize false positives

    Updated 2026-08-27: Restored with improved Chinese detection using expanded
    whitelist instead of jieba segmentation to avoid external dependencies.
    """
    findings: list[TextIntegrityFinding] = []

    if not body:
        return findings

    # Chinese sentence starters - focused list of most common sentence beginnings
    # (~80 chars covering ~70% of real cases, intentionally conservative
    # to allow detection of real word-internal punctuation)
    CHINESE_SENTENCE_STARTERS = (
        # Pronouns and demonstratives (most common)
        '这那但然我他她它'
        '此彼其谁哪里'
        # High-frequency verbs
        '是有在为从到说做去来'
        # Common conjunctions and modals
        '就都还也才只又不没'
        '要会能可应该必须'
        # Prepositions
        '把对已被给让使向着用'
        # Numbers (most common)
        '一二三四五六七八九十'
        # Logical markers
        '所因虽如经过关于由于通过'
        # Time markers
        '当时候刚正好'
    )

    def _is_mostly_chinese(text: str) -> bool:
        """Detect if text is primarily Chinese."""
        if not text:
            return False
        chinese_chars = sum(1 for c in text if '一' <= c <= '鿿')
        return chinese_chars / len(text) > 0.5

    is_chinese = _is_mostly_chinese(body)

    if is_chinese:
        # Chinese text: Use expanded whitelist with high threshold
        pattern = re.compile(r'([一-鿿])([。！？])([一-鿿])')
        matches = []

        for match in pattern.finditer(body):
            char_after = match.group(3)

            # Skip if next char is a common sentence starter
            if char_after in CHINESE_SENTENCE_STARTERS:
                continue

            matches.append(match)

        # Report any suspicious instances, but adjust severity based on count
        if matches:
            evidence_samples = []
            for match in matches[:5]:
                context_start = max(0, match.start() - 10)
                context_end = min(len(body), match.end() + 10)
                evidence_samples.append(body[context_start:context_end])

            # Determine severity based on instance count
            if len(matches) >= 10:
                severity = "critical"
                confidence = "high confidence"
            elif len(matches) >= 3:
                severity = "critical"
                confidence = "likely"
            else:
                severity = "warning"  # Lower severity for 1-2 instances (could be rare sentence starters)
                confidence = "possible"

            findings.append(TextIntegrityFinding(
                check="word_internal_punctuation",
                severity=severity,
                message=f"Detected {confidence} word-internal punctuation in Chinese text. Found {len(matches)} instance(s). This may indicate serialization errors breaking words. Examples: {evidence_samples[:3]}",
                start=matches[0].start(),
                end=matches[0].end()
            ))
    else:
        # English text: Use strict word-boundary detection
        # True word-internal punctuation: "hello.world" (no spaces)
        pattern = re.compile(r'\b\w+[.!?]\w+\b')
        matches = list(pattern.finditer(body))

        if matches:
            evidence_samples = []
            for match in matches[:5]:
                context_start = max(0, match.start() - 10)
                context_end = min(len(body), match.end() + 10)
                evidence_samples.append(body[context_start:context_end])

            findings.append(TextIntegrityFinding(
                check="word_internal_punctuation",
                severity="critical",
                message=f"Detected word-internal punctuation in English text. Found {len(matches)} instances. Examples: {evidence_samples[:3]}",
                start=matches[0].start(),
                end=matches[0].end()
            ))

    return findings


def check_abnormal_line_breaks(body: str) -> list[TextIntegrityFinding]:
    """Detect abnormal line breaks (mid-sentence breaks, excessive blank lines).

    Legitimate breaks:
    - After sentence-ending punctuation
    - Before/after dialogue markers ("...")
    - Paragraph breaks

    Abnormal breaks:
    - Line break in middle of sentence (no punctuation)
    - Multiple consecutive blank lines (>2)
    """
    findings: list[TextIntegrityFinding] = []

    if not body:
        return findings

    lines = body.split('\n')

    for i, line in enumerate(lines[:-1]):
        stripped = line.strip()

        # Skip empty lines, headings, dividers
        if not stripped or _is_heading(stripped) or _is_scene_divider(stripped):
            continue

        # Check if line ends without sentence-ending punctuation
        if not _SENTENCE_END_RE.search(stripped):
            next_line = lines[i + 1].strip()

            # Skip if next line is empty, heading, or starts with dialogue/bracket
            if not next_line or _is_heading(next_line) or next_line[0] in '"\'"（【「':
                continue

            # Check if next line starts lowercase (strong signal of mid-sentence break)
            if next_line and next_line[0].islower() and next_line[0].isalpha():
                findings.append(TextIntegrityFinding(
                    check="abnormal_mid_sentence_break",
                    severity="warning",
                    message=f"Possible mid-sentence line break. Line {i}: 「{stripped[-30:]}」 → Line {i+1}: 「{next_line[:30]}」",
                    start=sum(len(l) + 1 for l in lines[:i]),
                    end=sum(len(l) + 1 for l in lines[:i+1])
                ))

    # Check for excessive blank lines (>2 consecutive)
    blank_run = 0
    for i, line in enumerate(lines):
        if not line.strip():
            blank_run += 1
            if blank_run > 2:
                findings.append(TextIntegrityFinding(
                    check="excessive_blank_lines",
                    severity="info",
                    message=f"Excessive blank lines ({blank_run} consecutive) around line {i}",
                    start=sum(len(l) + 1 for l in lines[:i-blank_run+1]),
                    end=sum(len(l) + 1 for l in lines[:i+1])
                ))
                blank_run = 0  # Reset after reporting
        else:
            blank_run = 0

    return findings


def _scan_body(body: str) -> list[TextIntegrityFinding]:
    findings: list[TextIntegrityFinding] = []
    if not body or not body.strip():
        return findings
    for m in _BLANK_LINE_RE.finditer(body):
        # The physical line immediately before the blank-line break. Only a
        # short fragment that is NOT a heading and does NOT end in sentence
        # punctuation looks like a word broken across the break.
        line_start = body.rfind("\n", 0, m.start()) + 1
        prev_line = body[line_start: m.start()].strip()
        if (not prev_line or _is_heading(prev_line) or _is_scene_divider(prev_line)
                or _is_chapter_end_marker(prev_line)
                or _SENTENCE_END_RE.search(prev_line)):
            continue
        if len(prev_line) <= _FRAGMENT_MAX:
            findings.append(TextIntegrityFinding(
                check="word_split",
                severity="error",
                message="疑似词内断裂：短片段被空行孤立",
                start=line_start, end=m.end(),
            ))
    for m in _DOUBLE_NEWLINE_WORD_RE.finditer(body):
        # A heading line, or a line ending in sentence punctuation, before a
        # paragraph break is normal — not an injection.
        if _SENTENCE_END_RE.search(body[:m.start() + 1].rstrip()):
            continue
        if _is_heading(_line_at(body, m.start())):
            continue
        findings.append(TextIntegrityFinding(
            check="newline_injection",
            severity="warning",
            message="疑似异常换行注入：词片段之间出现双换行",
            start=m.start(), end=m.end(),
        ))
    for m in _WORD_JOIN_RE.finditer(body):
        # spaces inside Chinese runs are suspicious, but only warn unless other
        # evidence exists. A heading line legitimately spaces its title, and a
        # chapter-end marker（第一章 完）/（未完待续）legitimately spaces inside the
        # bracket — neither is serialization word-splitting, so skip both.
        line = _line_at(body, m.start())
        if _is_heading(line) or _is_chapter_end_marker(line):
            continue
        findings.append(TextIntegrityFinding(
            check="whitespace_anomaly",
            severity="warning",
            message="疑似中文词间异常空白",
            start=m.start(), end=m.end(),
        ))
    findings.extend(_scan_language_drift(body))

    # Phase 1 Task 1.1.2: Integrate new detectors
    # Word-internal punctuation check (critical severity)
    findings.extend(check_word_internal_punctuation(body))

    # Abnormal line breaks check (warning severity)
    findings.extend(check_abnormal_line_breaks(body))

    return findings


def _scan_language_drift(body: str) -> list[TextIntegrityFinding]:
    findings: list[TextIntegrityFinding] = []
    for m in _ASCII_WORD_RE.finditer(body):
        line = _line_at(body, m.start())
        if _is_heading(line):
            continue
        findings.append(TextIntegrityFinding(
            check="language_drift",
            severity="warning",
            message="疑似英文语域漂移：正文中出现连续英文词块",
            start=m.start(), end=m.end(),
        ))
    return findings


def assess_text_integrity(artifact: dict, *, raw_text: Optional[str] = None) -> TextIntegrityReport:
    body = (artifact or {}).get("body", "") or ""
    findings = _scan_body(body)
    if not body.strip():
        return TextIntegrityReport(status="not_assessed", action="allow")

    reason_codes: list[str] = []
    evidence_spans: list[dict] = []
    severity = "low"
    action = "allow"
    status = "pass"

    if findings:
        reason_codes = sorted({f.check for f in findings})
        evidence_spans = [_span(body, f.start or 0, f.end or 0) for f in findings[:5]]
        if any(f.check == "word_split" for f in findings):
            severity = "critical"
            action = "block"
            status = "fail"
        elif any(f.check == "newline_injection" for f in findings):
            severity = "medium"
            action = "require_review"
            status = "review_required"
        elif any(f.check == "language_drift" for f in findings):
            severity = "medium"
            action = "require_review"
            status = "review_required"
        else:
            severity = "medium"
            action = "require_review"
            status = "review_required"

    for code, pattern in _GATING_PATTERNS.items():
        if pattern.search(body):
            reason_codes = sorted(set(reason_codes + [code]))
            if status == "pass":
                severity = "low"
                action = "allow"
                status = "pass"

    if raw_text is not None and raw_text != body:
        # if final differs from raw and the final trips the gate, attribute the
        # issue to finalize corruption for audit purposes.
        if status == "fail":
            reason_codes = sorted(set(reason_codes + ["finalize_corruption"]))
        elif status == "review_required":
            reason_codes = sorted(set(reason_codes + ["alignment_break"]))

    return TextIntegrityReport(
        status=status,
        reason_codes=reason_codes,
        evidence_spans=evidence_spans,
        severity=severity,
        action=action,
        findings=findings,
    )
