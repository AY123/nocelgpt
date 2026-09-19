"""projection.py — the Long-Arc Plan as a projection (ANES v2, roadmap M3).

The outline authored at genesis carries the RAW MATERIAL of a long arc — a few
volumes (goal / oppressor / twist / settlement), a power-tier ladder, a conflict
ladder, a reward cadence — but only the first ~30 chapters are expanded, and
NONE of it is projected per-chapter. So chapter N (especially N > 30) generates
blind to its long-arc position: which volume it is in, how far to that volume's
climax, which power tier it should be approaching, whether a paywall is near.

The Long-Arc Plan fills that gap WITHOUT re-authoring anything. Like the Story
State (ADR-008), the schedule (P17), and the inventory (P19), it is a PROJECTION:

    long_arc@chapter_limit = fold(outline volumes + power_system + conflict_ladder
                                  + reward_loop)

It expands the authored volume/power/conflict skeleton FORWARD into per-chapter
long-arc coordinates every chapter's IR / objective / prompt can reference.

DISCIPLINE:
  - PURE + DETERMINISTIC: same outline + same chapter_limit => same plan (and the
    same content_hash). No LLM, no network, no randomness — the PlotArchitect LLM
    may ENRICH this later (enrich-never-replace), but the base is a pure fold.
  - ADVISORY, never gates (ADR-003): gating=False. It shapes generation, it never
    blocks a build.
  - READS the outline only; writes no facts (ADR-006).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

LONG_ARC_REVIEWER_ID = "long-arc-v1"

# Default long-arc horizon. The outline authors ~3 volumes + 30 expanded
# chapters; the plan projects a full commercial serial's first stretch.
DEFAULT_CHAPTER_LIMIT = 100


@dataclass(frozen=True)
class LongArcPlan:
    """A deterministic per-chapter long-arc projection folded from the outline.

    chapters[i] (0-based) is the long-arc coordinate of chapter i+1: its volume,
    position within that volume, distance to the volume climax, the power tier it
    should be approaching, and whether it sits on a paywall / milestone."""
    reviewer: str
    chapter_limit: int
    volumes: List[dict] = field(default_factory=list)      # expanded per-volume spans
    chapters: List[dict] = field(default_factory=list)     # per-chapter coordinates
    paywall_chapters: List[int] = field(default_factory=list)
    milestone_chapters: List[int] = field(default_factory=list)
    gating: bool = False                                   # ADR-003 — advisory

    def chapter(self, chapter_no: int) -> Optional[dict]:
        """The 1-based chapter_no's long-arc coordinate, or None if out of range."""
        if 1 <= chapter_no <= len(self.chapters):
            return self.chapters[chapter_no - 1]
        return None

    def to_dict(self) -> dict:
        return {
            "reviewer": self.reviewer,
            "gating": self.gating,
            "chapter_limit": self.chapter_limit,
            "volumes": self.volumes,
            "chapters": self.chapters,
            "paywall_chapters": self.paywall_chapters,
            "milestone_chapters": self.milestone_chapters,
        }


def _expand_volumes(volumes: List[dict], chapter_limit: int) -> List[dict]:
    """Spread the authored volumes evenly across chapter_limit and mark each
    volume's climax (its last chapter — where the twist/settlement lands) and its
    paywall (the chapter AFTER the climax, the premium volume-opener). Deterministic
    integer partition: no volume is empty, remainders go to the earliest volumes.

    With no authored volumes, degrades to a single implicit volume spanning the
    whole horizon so downstream never sees an empty structure."""
    n = len([v for v in volumes if isinstance(v, dict)])
    if n == 0 or chapter_limit < 1:
        return [{
            "id": "VOL-01", "title": "", "purpose": "", "goal": "",
            "oppressor": "", "twist": "", "settlement": "",
            "start_chapter": 1, "end_chapter": max(chapter_limit, 1),
            "climax_chapter": max(chapter_limit, 1), "paywall_chapter": None,
        }]
    base, extra = divmod(chapter_limit, n)
    out: List[dict] = []
    cursor = 1
    for i, v in enumerate([v for v in volumes if isinstance(v, dict)]):
        span = base + (1 if i < extra else 0)
        start = cursor
        end = cursor + span - 1
        cursor = end + 1
        # the volume climax is its final chapter; the paywall opens the NEXT
        # volume (so the last volume has no paywall — nothing follows it here).
        paywall = end + 1 if end < chapter_limit else None
        out.append({
            "id": v.get("id", f"VOL-{i+1:02d}"),
            "title": v.get("title", ""),
            "purpose": v.get("purpose", ""),
            "goal": v.get("goal", ""),
            "oppressor": v.get("oppressor", ""),
            "twist": v.get("twist", ""),
            "settlement": v.get("settlement", ""),
            "start_chapter": start,
            "end_chapter": end,
            "climax_chapter": end,
            "paywall_chapter": paywall,
        })
    return out


def _tier_labels(progression_system: dict) -> List[str]:
    """The progression-tier ladder as clean labels (the tier name before any
    parenthetical gloss), or [] when none authored.

    Supports both old "power_system" format and new "progression_system" with type."""
    tiers = progression_system.get("tiers") if isinstance(progression_system, dict) else None
    if not isinstance(tiers, list):
        return []
    out = []
    for t in tiers:
        if isinstance(t, str) and t.strip():
            # strip a "（…）" gloss so the label is the bare tier name
            label = t.split("（", 1)[0].split("(", 1)[0].strip()
            out.append(label or t.strip())
    return out


def _tier_for_position(tiers: List[str], chapter_no: int, chapter_limit: int) -> Optional[str]:
    """The power tier chapter_no should be APPROACHING: map the chapter's fractional
    progress through the horizon onto the tier ladder. Deterministic; None when no
    tiers are authored."""
    if not tiers:
        return None
    # fraction in [0,1); floor onto tier index, clamped to the last tier.
    frac = (chapter_no - 1) / max(chapter_limit, 1)
    idx = min(int(frac * len(tiers)), len(tiers) - 1)
    return tiers[idx]


def _volume_of(chapter_no: int, expanded: List[dict]) -> dict:
    """The expanded-volume record containing chapter_no (the last volume if past
    the end — a serial that overruns its authored volumes stays in the final one)."""
    for v in expanded:
        if v["start_chapter"] <= chapter_no <= v["end_chapter"]:
            return v
    return expanded[-1]


def project_long_arc(outline: Optional[dict], *,
                     chapter_limit: int = DEFAULT_CHAPTER_LIMIT,
                     reviewer_id: str = LONG_ARC_REVIEWER_ID) -> LongArcPlan:
    """Fold the outline's volumes + progression_system (or power_system) + conflict_ladder + reward_loop
    into a per-chapter long-arc projection. Pure/deterministic; advisory, never
    gates. A None/empty outline degrades to a single implicit volume with no power
    or conflict labels — the plan is always structurally complete, never an error.

    When an M5 reference abstraction is attached to the outline, the projection
    carries a few high-level reference-derived expectations so the long arc can
    mirror the reference's commercial rhythm without copying specifics."""
    o = outline or {}
    ref_abs = o.get("reference_abstraction") if isinstance(o.get("reference_abstraction"), dict) else None
    plot = o.get("plot") if isinstance(o.get("plot"), dict) else {}
    volumes = plot.get("volumes") if isinstance(plot.get("volumes"), list) else []

    # Support both old "power_system" and new "progression_system"
    progression = o.get("progression_system") or o.get("power_system")
    progression = progression if isinstance(progression, dict) else {}

    ladder = o.get("conflict_ladder") if isinstance(o.get("conflict_ladder"), list) else []
    reward = o.get("reward_loop") if isinstance(o.get("reward_loop"), dict) else {}

    limit = max(int(chapter_limit), 1)
    expanded = _expand_volumes(volumes, limit)
    tiers = _tier_labels(progression)
    cadence = reward.get("cadence_chapters")
    cadence = cadence if isinstance(cadence, int) and cadence >= 1 else None

    paywalls = sorted({v["paywall_chapter"] for v in expanded
                       if v["paywall_chapter"] is not None})
    # milestones: every volume climax, plus round-number reader checkpoints that
    # fall within the horizon (30/60/90/100 …) — the emotional/commercial beats.
    climaxes = {v["climax_chapter"] for v in expanded}
    rounds = {c for c in range(30, limit + 1, 30)} | {limit}
    milestones = sorted(climaxes | rounds)

    abstraction = ref_abs if isinstance(ref_abs, dict) else {}
    expected_cadence = None
    if abstraction:
        cadence_text = ((abstraction.get("commercial_cadence") or {}).get("mid_arc") or "")
        if cadence_text:
            expected_cadence = cadence_text

    chapters: List[dict] = []
    for ch in range(1, limit + 1):
        vol = _volume_of(ch, expanded)
        pos = ch - vol["start_chapter"] + 1
        vol_span = vol["end_chapter"] - vol["start_chapter"] + 1
        to_climax = vol["climax_chapter"] - ch
        next_ms = next((m for m in milestones if m > ch), None)
        # map the conflict ladder onto the chapter's volume index (rung per volume,
        # clamped) — the pressure source escalates volume by volume.
        vol_idx = next((i for i, v in enumerate(expanded) if v["id"] == vol["id"]), 0)
        rung = ladder[min(vol_idx, len(ladder) - 1)] if ladder else None
        chapters.append({
            "chapter_no": ch,
            "volume_id": vol["id"],
            "volume_title": vol["title"],
            "volume_goal": vol["goal"],
            "volume_oppressor": vol["oppressor"],
            "position_in_volume": pos,
            "volume_span": vol_span,
            "chapters_to_volume_climax": to_climax,
            "is_volume_climax": ch == vol["climax_chapter"],
            "is_paywall": ch in paywalls,
            "is_milestone": ch in set(milestones),
            "next_milestone": next_ms,
            "power_tier": _tier_for_position(tiers, ch, limit),
            "conflict_level": (rung.get("level") if isinstance(rung, dict) else None),
            "conflict_pressure": (rung.get("pressure_source") if isinstance(rung, dict) else None),
            "reward_cadence": cadence,
            "reference_core_promise": ((abstraction.get("market_positioning") or {}).get("core_promise")
                                        if abstraction else None),
            "reference_commercial_cadence": expected_cadence,
        })

    return LongArcPlan(
        reviewer=reviewer_id,
        chapter_limit=limit,
        volumes=expanded,
        chapters=chapters,
        paywall_chapters=paywalls,
        milestone_chapters=milestones,
    )
