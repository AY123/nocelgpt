"""m7.py — originality and platform red-line gate (ANES v2, M7).

This module composes the deterministic platform red-line gate with a deterministic
originality checker so publish-readiness can act on a single M7 result. The
originality checker now supports optional embedding-based retrieval (via a
stable hashed character n-gram embedding) plus chunk/sentence alignment, giving
us a stronger, portable similarity gate without external model dependencies.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher
import math
import re
from typing import Any, List, Optional, Sequence

from .redline import RedlineHit, RedlineRule, check_redlines, has_hard_hit, hits_to_dicts

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[。！？!?；;\n])")


@dataclass(frozen=True)
class SimilarityMatch:
    source_id: str
    source_type: str
    similarity: float
    excerpt: str = ""
    risk_type: str = "semantic_overlap"
    aligned_spans: list[dict[str, list[int]]] = field(default_factory=list)
    method: str = "window"

    def to_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "source_type": self.source_type,
            "similarity": self.similarity,
            "excerpt": self.excerpt,
            "risk_type": self.risk_type,
            "aligned_spans": self.aligned_spans,
            "method": self.method,
        }


@dataclass(frozen=True)
class M7Result:
    chapter_id: str
    recommendation: str                       # recommend | hold | block
    risk_level: str                           # L0 | L1 | L2 | L3
    redline_passed: bool
    redline_hits: List[dict] = field(default_factory=list)
    similarity: dict = field(default_factory=dict)
    rationale: str = ""
    authority: str = "human"
    gates_build: bool = True

    def to_dict(self) -> dict:
        return {
            "chapter_id": self.chapter_id,
            "authority": self.authority,
            "gates_build": self.gates_build,
            "recommendation": self.recommendation,
            "risk_level": self.risk_level,
            "redline_passed": self.redline_passed,
            "redline_hits": self.redline_hits,
            "similarity": self.similarity,
            "rationale": self.rationale,
        }


def _normalize_for_similarity(text: str) -> str:
    return "".join(ch.lower() for ch in text if not ch.isspace())


def _ngram_set(text: str, n: int = 5) -> set:
    """HASHED character n-gram set of the normalized text (a set of ints). Linear
    in len(text) — the building block that replaces the O(len²) SequenceMatcher
    scans so the gate stays cheap against FULL reference novels (M7 originality is
    default-on per chapter as of M1-B2; a quadratic scan over 4 whole novels hung
    the serial). Ints instead of substrings bound memory: a 13.5M-char corpus is
    ~450MB of ints vs ~1.3GB of 5-char strings."""
    t = _normalize_for_similarity(text)
    if len(t) < n:
        return {hash(t)} if t else set()
    return {hash(t[i:i + n]) for i in range(len(t) - n + 1)}


def _containment(sub_ngrams: set, super_ngrams: set) -> float:
    """Fraction of sub_ngrams that also appear in super_ngrams: |A∩B|/|A|.
    Answers "how much of THIS text is present in the reference" — the right
    originality signal (identical text => 1.0; disjoint => 0.0). O(|A|)."""
    if not sub_ngrams:
        return 0.0
    inter = len(sub_ngrams & super_ngrams)
    return round(inter / len(sub_ngrams), 4)


def _chunks(text: str, size: int = 80) -> list[tuple[int, int, str]]:
    out = []
    idx = 0
    while idx < len(text):
        end = min(len(text), idx + size)
        out.append((idx, end, text[idx:end]))
        idx = end
    return out


def _sentences(text: str) -> list[tuple[int, int, str]]:
    parts = _SENTENCE_SPLIT_RE.split(text)
    out = []
    offset = 0
    for part in parts:
        if not part:
            continue
        start = text.find(part, offset)
        if start < 0:
            start = offset
        end = start + len(part)
        out.append((start, end, part))
        offset = end
    return out if out else [(0, len(text), text)]


def _clamped_similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return round(SequenceMatcher(a=_normalize_for_similarity(a), b=_normalize_for_similarity(b)).ratio(), 4)


def _tokenize(text: str) -> list[str]:
    text = _normalize_for_similarity(text)
    if not text:
        return []
    ngrams = [text[i:i + 3] for i in range(max(1, len(text) - 2))]
    return ngrams or [text]


def _hash_embedding(text: str, dims: int = 64) -> list[float]:
    vec = [0.0] * dims
    tokens = _tokenize(text)
    if not tokens:
        return vec
    for tok in tokens:
        h = hash(tok)
        idx = abs(h) % dims
        sign = -1.0 if (h & 1) else 1.0
        vec[idx] += sign
    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0:
        return vec
    return [v / norm for v in vec]


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    return round(sum(x * y for x, y in zip(a, b)), 4)


# Windowed embedding retrieval (CJK false-positive fix). A whole-novel embedding
# is the book's MEAN character-trigram vector: at low dims it saturates toward the
# language mean (any Chinese chapter cosines ~0.99 against any Chinese novel — it
# measures "is this Chinese", not "is this similar"), AND it cannot detect a copied
# CHUNK (a 3.5k-char lift is diluted to noise against a 3.4M-char average). Both
# are fixed by comparing the body against same-SCALE reference windows at higher
# dims and taking the max. Empirically (5 original chapters × 4 full novels):
# windowed 2048-dim cosine sits at ~0.60 for original prose and ~0.98 for a
# verbatim chunk lift — a real separation the whole-novel 64-dim signal did not have.
_EMBED_DIMS = 2048
_EMBED_WINDOW = 4000
_EMBED_STEP = 4000


def _window_embeddings(text: str) -> list[list[float]]:
    """Embed a reference as a list of fixed-size window vectors (higher dims to
    avoid saturation). Short references collapse to a single window. Non-overlapping
    windows keep the per-reference index near-linear; verbatim chunk copies are
    caught by n-gram containment + verbatim spans, so the embedding signal only has
    to catch DISTRIBUTIONAL (paraphrase-scale) similarity, which needs no overlap."""
    if not text:
        return []
    if len(text) <= _EMBED_WINDOW:
        return [_hash_embedding(text, _EMBED_DIMS)]
    out: list[list[float]] = []
    i = 0
    while i + _EMBED_WINDOW <= len(text):
        out.append(_hash_embedding(text[i:i + _EMBED_WINDOW], _EMBED_DIMS))
        i += _EMBED_STEP
    # tail window so the final fragment is not dropped
    if i < len(text):
        out.append(_hash_embedding(text[-_EMBED_WINDOW:], _EMBED_DIMS))
    return out


def _windowed_max_cosine(body_emb: list[float], window_embs: list[list[float]]) -> float:
    """Max cosine of the body against any reference window — the closest local
    match, not the diluted whole-book average."""
    best = 0.0
    for we in window_embs:
        c = sum(x * y for x, y in zip(body_emb, we))
        if c > best:
            best = c
    return round(best, 4)


def _verbatim_spans(body: str, ref_text: str, *, min_len: int = 40,
                    max_spans: int = 5) -> list[dict[str, list[int]]]:
    """Find up to max_spans body windows that appear VERBATIM in the reference,
    as copy evidence. Uses str.find (Boyer-Moore-ish, near-linear) on fixed-size
    windows instead of the old O(body_chunks × ref_chunks) SequenceMatcher grid.
    Reports raw (un-normalized) offsets so spans point into the original body."""
    spans: list[dict[str, list[int]]] = []
    if not body or not ref_text:
        return spans
    # a chapter shorter than the default window still gets one span when fully
    # copied (a short verbatim reproduction is the strongest copy signal).
    win = min(min_len, len(body))
    step = win
    i = 0
    while i + win <= len(body) and len(spans) < max_spans:
        window = body[i:i + win]
        pos = ref_text.find(window)
        if pos >= 0:
            spans.append({"input_span": [i, i + win],
                          "source_span": [pos, pos + win]})
        i += step
    return spans


def _build_similarity_report(
    *,
    body: str,
    references: Sequence[dict],
    top_k: int = 3,
    review_threshold: float = 0.65,
    block_threshold: float = 0.8,
    embedding_weight: float = 0.6,
) -> dict:
    matches: list[SimilarityMatch] = []
    # Linear-cost engine (M1-B2 follow-up): the old path ran SequenceMatcher over
    # the WHOLE chapter × WHOLE novel plus nested chunk/sentence grids — O(len²)
    # per reference, which hung the serial once originality went default-on
    # against 4 full reference novels. n-gram containment is the same signal
    # (how much of this chapter is present in the reference) at O(len).
    body_ngrams = _ngram_set(body)
    body_emb = _hash_embedding(body, _EMBED_DIMS)
    ref_embeddings: list[float] = []
    ref_containments: list[float] = []
    any_verbatim = False
    for ref in references:
        ref_text = ref.get("text", "") or ""
        # Memoize the per-reference index (n-gram set + WINDOW embeddings) ON the
        # ref dict: references are constant across a run (loaded ONCE before the
        # serial loop), so a 3.4M-char novel is windowed+embedded once, not
        # re-indexed every chapter — the difference between ~10s/chapter and
        # <0.1s/chapter over 4 full novels. Old memoized indexes carried a single
        # whole-novel "emb"; key the new windowed index under "win_embs" so a stale
        # cache from before this fix is transparently rebuilt.
        idx = ref.get("_m7_index") if isinstance(ref, dict) else None
        if idx is None or "win_embs" not in idx:
            idx = {"ngrams": _ngram_set(ref_text),
                   "win_embs": _window_embeddings(ref_text)}
            if isinstance(ref, dict):
                ref["_m7_index"] = idx
        ref_ngrams = idx["ngrams"]
        containment = _containment(body_ngrams, ref_ngrams)
        embedding_similarity = _windowed_max_cosine(body_emb, idx["win_embs"])
        ref_embeddings.append(embedding_similarity)
        ref_containments.append(containment)
        # blend containment (verbatim/near-verbatim overlap) with the embedding
        # cosine (distributional similarity), same spirit as the prior max/blend.
        similarity = max(
            containment,
            embedding_similarity * embedding_weight + containment * (1 - embedding_weight),
        )
        if similarity <= 0:
            continue
        # verbatim copy evidence, bounded (near-linear str.find, not a grid)
        spans = _verbatim_spans(body, ref_text)
        if spans:
            any_verbatim = True
        # Label by the STRONGEST evidence. Verbatim spans and n-gram containment
        # are copy evidence (a real allegation); a bare embedding cosine is a
        # distributional signal that, in CJK, is genre noise (see _window_embeddings)
        # — it is recorded but must never be labeled as copy-grade overlap on its own.
        if spans or containment >= block_threshold:
            risk_type = "high_overlap"
            method = "ngram_containment"
        elif containment >= review_threshold:
            risk_type = "window_overlap"
            method = "ngram_containment"
        elif embedding_similarity >= review_threshold:
            risk_type = "embedding_overlap"
            method = "embedding"
        else:
            risk_type = "semantic_overlap"
            method = "ngram_containment"
        matches.append(SimilarityMatch(
            source_id=str(ref.get("source_id", "")),
            source_type=str(ref.get("source_type", "reference")),
            similarity=round(similarity, 4),
            excerpt=str(ref_text[:80]),
            risk_type=risk_type,
            aligned_spans=spans,
            method=method,
        ))
    matches.sort(key=lambda m: (-m.similarity, m.source_id))
    top_matches = [m.to_dict() for m in matches[:top_k]]
    top_similarity = top_matches[0]["similarity"] if top_matches else 0.0
    top_embedding_similarity = round(max(ref_embeddings) if ref_embeddings else 0.0, 4)
    top_containment = round(max(ref_containments) if ref_containments else 0.0, 4)
    # Risk level is driven by COPY EVIDENCE (verbatim spans / n-gram containment),
    # NOT by the embedding cosine alone. In CJK the whole-corpus embedding signal is
    # genre noise (see _window_embeddings): originally-authored chapters cosine ~0.6
    # against unrelated novels, so letting embedding reach block_threshold flagged
    # 5/5 clean chapters as L3 and flooded the ADR-009 approval queue with false
    # allegations. Embedding can now escalate to at most L2 (a human REVIEW hold) and
    # only when it is genuinely high; L3/block requires verbatim copy or containment
    # at/above block_threshold — a reproducible copy claim, not a distributional hunch.
    risk_level = "L0"
    if any_verbatim or top_containment >= block_threshold:
        risk_level = "L3"
    elif top_containment >= review_threshold or top_embedding_similarity >= block_threshold:
        risk_level = "L2"
    elif top_containment >= 0.45 or top_embedding_similarity >= review_threshold:
        risk_level = "L1"
    return {
        "overall_similarity": top_similarity,
        "risk_level": risk_level,
        "matches": top_matches,
        "suspicious_spans": [s for m in top_matches for s in m.get("aligned_spans", [])],
        "embedding_similarity": top_embedding_similarity,
        "containment": top_containment,
        "reference_count": len(references),
    }


def assess_m7(
    artifact: dict,
    *,
    chapter_id: str,
    references: Optional[Sequence[dict]] = None,
    redline_ruleset: Optional[Sequence[RedlineRule]] = None,
    review_threshold: float = 0.65,
    block_threshold: float = 0.8,
) -> M7Result:
    body = artifact.get("body", "") or ""
    redline_hits = check_redlines(artifact, ruleset=redline_ruleset)
    similarity = _build_similarity_report(
        body=body,
        references=references or (),
        review_threshold=review_threshold,
        block_threshold=block_threshold,
    )
    hard = has_hard_hit(redline_hits)
    sim_risk = similarity["risk_level"]
    if hard:
        recommendation = "block"
        risk_level = "L3"
        rationale = "命中平台硬红线，必须阻断。"
    elif sim_risk == "L3":
        recommendation = "block"
        risk_level = "L3"
        rationale = "原创性相似度过高，必须阻断。"
    elif sim_risk == "L2":
        recommendation = "hold"
        risk_level = "L2"
        rationale = "原创性风险中高，进入人工审批。"
    elif sim_risk == "L1":
        # L1 is a LOW advisory signal ("建议抽检"), not a copy allegation. With
        # originality default-on per chapter (M1-B2), mapping L1→hold flooded the
        # approval queue: same-genre prose scores L1 purely from shared vocabulary
        # against a multi-million-char corpus. L1 is recorded on the ChapterRun +
        # dashboard as advisory; only L2/L3 (genuine near-copy) enqueue a human
        # review. This matches L1's rationale and test_m7_recommends_when_clean.
        recommendation = "recommend"
        risk_level = "L1"
        rationale = "存在轻微相似风险（同题材词汇重叠），仅提示抽检，不入审批。"
    else:
        recommendation = "recommend"
        risk_level = "L0"
        rationale = "未命中硬红线，原创性风险可接受。"
    if redline_hits and not hard and recommendation == "recommend":
        rationale += " 存在软性敏感项，仅提示不阻断。"
    return M7Result(
        chapter_id=chapter_id,
        recommendation=recommendation,
        risk_level=risk_level,
        redline_passed=not hard,
        redline_hits=hits_to_dicts(redline_hits),
        similarity=similarity,
        rationale=rationale,
    )
