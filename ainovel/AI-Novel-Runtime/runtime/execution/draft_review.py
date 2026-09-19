"""draft_review.py — evaluative QA hook for a ChapterDraft (ANES v2, ADR-003).

This is the EVALUATIVE counterpart to draft_qa.py. ADR-003: only deterministic
checks may gate a build. Voice, pacing, theme, fidelity-to-facts — these are
judgments, not pass/fail facts, so they live HERE and are ADVISORY ONLY. A
review finding can NEVER block the execution loop (it mirrors validator's
AXIS_TREND for the build gate).

A real LLM-judge reviewer plugs in behind the DraftReviewer protocol later (per
ROADMAP: "no consumer = stub"); until then `placeholder_reviewer` returns a
structurally-valid, empty advisory report so the loop, the envelope, and the
consumers are all wired and provable now.

The review report rides in the Runtime envelope (execution.envelope), NOT inside
the contract artifact — the frozen Standard schema seals `produced_by`, so an
evaluative block has no schema-legal slot in the draft itself.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Protocol, Set

AXIS_EVALUATIVE = "evaluative"   # advisory only; never gates (ADR-003)

# Severities are advisory labels, not gate signals. Even "error" does not block.
SEVERITIES = ("info", "warning", "error")


@dataclass(frozen=True)
class ReviewFinding:
    check: str          # e.g. "voice", "pacing", "fact-fidelity"
    severity: str       # one of SEVERITIES (advisory)
    message: str

    def __str__(self) -> str:
        return f"[{self.severity}] review/{self.check}: {self.message}"


@dataclass(frozen=True)
class ReviewReport:
    reviewer: str                       # id of the reviewer that produced this
    axis: str = AXIS_EVALUATIVE         # always evaluative — structural invariant
    gating: bool = False                # always False — structural invariant
    findings: List[ReviewFinding] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "reviewer": self.reviewer,
            "axis": self.axis,
            "gating": self.gating,
            "findings": [
                {"check": f.check, "severity": f.severity, "message": f.message}
                for f in self.findings
            ],
        }


class DraftReviewer(Protocol):
    """A reviewer judges a finished draft against its source package and returns
    an ADVISORY report. It is given the inner contract artifact and the Task
    Package it was derived from. It must not mutate either."""

    reviewer_id: str

    def review(self, artifact: dict, package: dict,
               grounding: dict | None = None) -> ReviewReport:
        """`grounding` (Phase 4.2, optional) carries the Chapter IR's payoff_target
        so a quality judge can score promise_delivery against the STATED promise.
        Reviewers that don't consume it must still accept it (and ignore it)."""
        ...


class PlaceholderReviewer:
    """No-op evaluative reviewer. Produces a structurally-valid empty report so
    the hook is wired end-to-end. Replace with an LLM-judge reviewer that emits
    voice/pacing/fact-fidelity findings — the loop and envelope already carry it.
    """

    reviewer_id = "placeholder-reviewer-v1"

    def review(self, artifact: dict, package: dict,
               grounding: dict | None = None) -> ReviewReport:
        # Deliberately emits no findings yet. A single info note records that the
        # evaluative axis ran and was (trivially) clean, so audits can tell
        # "reviewed, nothing flagged" apart from "never reviewed".
        return ReviewReport(
            reviewer=self.reviewer_id,
            findings=[ReviewFinding(
                check="placeholder",
                severity="info",
                message="evaluative QA hook ran; no judge wired yet (ADR-003 advisory axis)",
            )],
        )


def placeholder_reviewer() -> PlaceholderReviewer:
    return PlaceholderReviewer()


# Multi-word proper-noun phrase: 2+ Capitalized tokens, lowercase connectors
# (of/the/and/...) allowed between them. Targets invented org/place names like
# "Order of the Severed Chain" while ignoring sentence-initial single words.
# [^\S\n] is "whitespace but not newline" so a phrase never spans a line break
# (which would glue a heading's last word onto the next paragraph's first).
_PROPER_NOUN_RE = re.compile(
    r"\b[A-Z][a-z]+(?:[^\S\n]+(?:of|the|and|de|von)[^\S\n]+|[^\S\n]+)"
    r"(?:[A-Z][a-z]+(?:[^\S\n]+(?:of|the|and|de|von)[^\S\n]+)?)+\b"
)

# Function words that, when capitalized at the START of a sentence, masquerade as
# a proper-noun head ("The Order", "And Vael", "Her Grace"). They cannot LEAD a
# real proper-noun phrase, so a match starting with one is trimmed of its head.
_LEADING_STOPWORDS = frozenset({
    "the", "a", "an", "and", "but", "or", "so", "yet", "for", "nor",
    "her", "his", "its", "their", "our", "my", "your", "this", "that",
    "these", "those", "then", "when", "where", "while", "if", "as",
    "he", "she", "it", "they", "we", "you", "i", "to", "of", "in", "on",
    "at", "by", "from", "with", "no", "not", "now", "what", "who",
})


def _trim_leading_stopword(phrase: str) -> str:
    """Drop a leading function word ('The Order' -> 'Order'). Returns '' if what
    remains is a single token (no longer a multi-word proper noun)."""
    tokens = phrase.split()
    while tokens and tokens[0].lower() in _LEADING_STOPWORDS:
        tokens = tokens[1:]
    return " ".join(tokens) if len(tokens) >= 2 else ""


def _known_names(package: dict) -> Set[str]:
    """Every canonical name + alias the package's facts carry, lowercased."""
    names: Set[str] = set()
    for records in package.get("context", {}).values():
        for rec in records:
            if rec.get("name"):
                names.add(rec["name"].lower())
            for alias in rec.get("aliases", []) or []:
                names.add(alias.lower())
    return names


class UnanchoredEntityReviewer:
    """Evaluative reviewer (ADR-003, advisory) that flags proper-noun phrases in
    the prose that have NO matching fact in the source package — i.e. entities
    the model invented (a faction, place, order) that are not yet anchored in the
    registry (ADR-006). Findings are WARNINGS and never gate.

    This is the first real consumer of the DraftReviewer seam. It exists because
    a live model coined 'Order of the Severed Chain' with no FAC anchor, and FAC
    is a reserved-but-undeployed type code (catalog has no Faction entity), so the
    name cannot be minted without changing the frozen Standard. The detector
    surfaces such drift for an author/curator to triage, rather than letting an
    unanchored entity pass silently."""

    reviewer_id = "unanchored-entity-reviewer-v1"

    def review(self, artifact: dict, package: dict,
               grounding: dict | None = None) -> ReviewReport:
        known = _known_names(package)
        body = artifact.get("body", "")
        seen: Set[str] = set()
        findings: List[ReviewFinding] = []
        for match in _PROPER_NOUN_RE.findall(body):
            phrase = _trim_leading_stopword(match.strip())
            if not phrase:
                continue
            low = phrase.lower()
            if low in seen:
                continue
            seen.add(low)
            # anchored if the phrase matches (or is contained by) any known name
            if any(low == k or low in k or k in low for k in known):
                continue
            findings.append(ReviewFinding(
                check="unanchored-entity",
                severity="warning",
                message=(f"{phrase!r} reads as a proper noun but has no fact "
                         f"anchor in the package; mint it or mark provisional "
                         f"(ADR-006)"),
            ))
        if not findings:
            findings.append(ReviewFinding(
                check="unanchored-entity",
                severity="info",
                message="no unanchored proper nouns detected",
            ))
        return ReviewReport(reviewer=self.reviewer_id, findings=findings)


def unanchored_entity_reviewer() -> UnanchoredEntityReviewer:
    return UnanchoredEntityReviewer()
