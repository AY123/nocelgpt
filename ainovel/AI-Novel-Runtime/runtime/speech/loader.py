"""loader.py — load & validate the authored Character Speech Profiles (ANES v2, roadmap §15).

The Speech Profile is an AUTHORED input, not a fact and not a derived artifact
(mirrors brain/loader.py exactly). It answers the ONE thing the §14 real-model
baseline proved no model fixes on its own: HOW each character talks — register,
vocabulary, sentence shape, verbal habits, taboos, thinking pattern, default
emotion. It lives at sources/character-speech-profiles.yaml. Consumers treat its
ABSENCE (or a fully-commented pristine template) as "no profiles authored yet"
and fall back to v6 behavior — exactly like load_brain returns None when no Brain
exists. This module only READS; it never writes facts (ADR-006) and never imports
a model (expression is authored, never generated here — guard #22).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from jsonschema import Draft202012Validator

# The Speech Profile schema is a Standard artifact contract. Resolve it relative
# to the Runtime repo's sibling Standard, matching brain/loader.py.
_SCHEMA_REL = ("contracts", "character-speech-profile.schema.json")


def speech_path(project_path: str | Path) -> Path:
    return Path(project_path) / "sources" / "character-speech-profiles.yaml"


def _schema_path(standard_root: Optional[str | Path]) -> Path:
    if standard_root is not None:
        return Path(standard_root).joinpath(*_SCHEMA_REL)
    # default: the sibling AI-Novel-Standard (parents[3] == repo root, as in brain)
    standard = Path(__file__).resolve().parents[3] / "AI-Novel-Standard"
    return standard.joinpath(*_SCHEMA_REL)


def validate_speech(profiles: dict, *, standard_root: Optional[str | Path] = None) -> List[str]:
    """Return a list of schema-validation error messages (empty == valid)."""
    schema = _schema_path(standard_root)
    validator = Draft202012Validator(
        json.loads(schema.read_text(encoding="utf-8")))
    errs = []
    for e in sorted(validator.iter_errors(profiles), key=lambda e: list(e.path)):
        loc = "/".join(str(p) for p in e.path) or "(root)"
        errs.append(f"{loc}: {e.message}")
    return errs


def load_speech(project_path: str | Path) -> Optional[dict]:
    """Return the authored Speech Profiles if any exist, else None.

    Absence is not an error: a project may have no profiles yet, and consumers
    fall back to v6 behavior (no language block injected). A fully-commented
    pristine template parses to None (yaml) and is treated exactly like absent,
    so `speech check` never false-fails a scaffolded project. Returns the parsed
    dict WITHOUT validating (call validate_speech to check it)."""
    path = speech_path(project_path)
    if not path.exists():
        return None
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def speech_profiles_by_id(profiles: Optional[dict]) -> Dict[str, dict]:
    """Index the authored profiles by character_id for O(1) lookup by the loop.
    Empty dict when absent/malformed — the caller degrades to no injection."""
    if not profiles:
        return {}
    out: Dict[str, dict] = {}
    for p in profiles.get("profiles") or []:
        cid = p.get("character_id")
        if isinstance(cid, str) and cid:
            out[cid] = p
    return out


_REGISTER_LABELS = {
    "crude": "粗俗", "colloquial": "口语", "neutral": "中性",
    "formal": "正式", "archaic": "古雅",
}
_LENGTH_LABELS = {
    "terse": "极短", "short": "短", "medium": "中等",
    "long": "长", "winding": "绵长",
}


def render_speech_profiles(profiles_for_leads: List[dict]) -> str:
    """Render the language blocks for the leads appearing in a chapter into the
    single string the v7 prompt's `speech_profiles` variable expects.
    Deterministic + bounded, mirroring render_character_runtime / brain_style_directive:
    same profiles => same block (stable field order, no time/randomness). This is
    the direct §14 remedy — it tells the model how these specific characters sound
    different so they stop writing in one voice.

    `profiles_for_leads` is the ordered list of profile dicts for the leads that
    appear in THIS chapter (the loop matches character_id against appearing leads).
    Empty => a sentinel note (mirroring render_character_runtime's empty case), so
    the v7 template's required variable is always bound and v7 degrades to a plain
    neutral voice rather than failing to render."""
    if not profiles_for_leads:
        return "（本章出场角色暂无语言画像，保持与语境一致的中性声音）"
    lines: List[str] = ["各角色语言画像（按人物区分声音，对白必须体现差异，不可同声）："]
    for p in profiles_for_leads:
        lines.append(f"  ◆ {p.get('name')}")
        voc = p.get("vocabulary") or {}
        reg = voc.get("register")
        if reg:
            lines.append(f"      语域：{_REGISTER_LABELS.get(reg, reg)}")
        sig = voc.get("signature_words") or []
        if sig:
            lines.append(f"      口头/标志词：{'、'.join(sig)}")
        avoids = voc.get("avoids") or []
        if avoids:
            lines.append(f"      忌用词：{'、'.join(avoids)}")
        sent = p.get("sentence") or {}
        if sent.get("length") or sent.get("style"):
            length = _LENGTH_LABELS.get(sent.get("length"), sent.get("length", ""))
            style = sent.get("style", "")
            desc = "，".join(x for x in (length and f"句长{length}", style) if x)
            lines.append(f"      句式：{desc}")
        habits = p.get("verbal_habits") or []
        if habits:
            lines.append(f"      语言习惯：{'；'.join(habits)}")
        taboo = p.get("taboo") or []
        if taboo:
            lines.append(f"      禁忌（防串味）：{'；'.join(taboo)}")
        if p.get("thinking_pattern"):
            lines.append(f"      思维模式：{p['thinking_pattern']}")
        if p.get("emotion_default"):
            lines.append(f"      情绪默认态：{p['emotion_default']}")
    return "\n".join(lines)
