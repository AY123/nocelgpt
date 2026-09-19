from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class ModelProfile:
    model_id: str
    provider: str
    observed_strengths: tuple[str, ...] = ()
    observed_failure_modes: tuple[str, ...] = ()
    preferred_prompt_versions: tuple[str, ...] = ()
    preferred_constraint_packs: tuple[str, ...] = ()
    notes: str = ""


@dataclass(frozen=True)
class ConstraintPack:
    pack_id: str
    model_ids: tuple[str, ...]
    prompt_versions: tuple[str, ...]
    directives: tuple[str, ...] = ()
    notes: str = ""


@dataclass(frozen=True)
class RoutingDecision:
    model_id: str
    provider: str | None
    prompt_version: str
    constraint_pack_id: str | None
    rationale: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


DEFAULT_MODEL_PROFILES: dict[str, ModelProfile] = {
    "gpt-5.4": ModelProfile(
        model_id="gpt-5.4",
        provider="openai",
        observed_strengths=("length control", "dialogue balance", "stable craft constraints"),
        observed_failure_modes=("model-specific AI tell constraints can fall flat",),
        preferred_prompt_versions=("13",),
        preferred_constraint_packs=("gpt-v13",),
        notes="Observed from chapter-level prompt experiments; use model-specific constraint routing.",
    ),
    "deepseek-chat": ModelProfile(
        model_id="deepseek-chat",
        provider="deepseek",
        observed_strengths=("low-cost long runs", "strict constraint obedience"),
        observed_failure_modes=("dash-aside and ai-tell artifacts", "AI味 and em-dash leakage"),
        preferred_prompt_versions=("13",),
        preferred_constraint_packs=("deepseek-v13",),
        notes="Known model-specific artifacts should be countered with dedicated constraint packs.",
    ),
}

DEFAULT_CONSTRAINT_PACKS: dict[str, ConstraintPack] = {
    "gpt-v13": ConstraintPack(
        pack_id="gpt-v13",
        model_ids=("gpt-5.4",),
        prompt_versions=("13",),
        directives=(
            "prioritize length control and dialogue share",
            "apply the v13 generation-side meta-reference guard alongside existing craft constraints",
        ),
    ),
    "deepseek-v13": ConstraintPack(
        pack_id="deepseek-v13",
        model_ids=("deepseek-chat",),
        prompt_versions=("13",),
        directives=(
            "suppress dash-aside and em-dash leakage",
            "tighten AI-tell, opening variety, and meta-reference leak prevention",
        ),
    ),
}


def _coerce_prompt_major(prompt_version: str | None) -> str | None:
    if not prompt_version:
        return None
    return str(prompt_version).split(".", 1)[0]


def route_generation(
    *,
    model_id: str,
    provider: str | None = None,
    task_type: str | None = None,
    target_style: str | None = None,
    known_failure_mode: str | None = None,
    prompt_version: str | None = None,
    model_profiles: Mapping[str, ModelProfile] | None = None,
    constraint_packs: Mapping[str, ConstraintPack] | None = None,
) -> RoutingDecision:
    profiles = model_profiles or DEFAULT_MODEL_PROFILES
    packs = constraint_packs or DEFAULT_CONSTRAINT_PACKS
    profile = profiles.get(model_id)

    chosen_prompt_major = _coerce_prompt_major(prompt_version)
    chosen_pack_id = None

    if profile is not None:
        for candidate in profile.preferred_constraint_packs:
            pack = packs.get(candidate)
            if pack and model_id in pack.model_ids:
                chosen_pack_id = pack.pack_id
                if chosen_prompt_major is None and pack.prompt_versions:
                    chosen_prompt_major = pack.prompt_versions[0]
                break
        if (chosen_prompt_major is None or chosen_prompt_major == "1") and profile.preferred_prompt_versions:
            chosen_prompt_major = profile.preferred_prompt_versions[0]

    if chosen_pack_id is None:
        for pack in packs.values():
            if model_id in pack.model_ids:
                chosen_pack_id = pack.pack_id
                if chosen_prompt_major is None and pack.prompt_versions:
                    chosen_prompt_major = pack.prompt_versions[0]
                break

    if chosen_prompt_major is None:
        chosen_prompt_major = _coerce_prompt_major(prompt_version) or "12"

    failure_pack_map = {
        "dash-aside": "deepseek-v13",
        "em-dash": "deepseek-v13",
        "ai-tell": "deepseek-v13",
        "opening variety": "deepseek-v13",
        "length": "gpt-v13",
        "dialogue": "gpt-v13",
    }
    if known_failure_mode:
        failure_key = known_failure_mode.lower()
        for needle, pack_id in failure_pack_map.items():
            if needle in failure_key and pack_id in packs:
                chosen_pack_id = pack_id
                if packs[pack_id].prompt_versions:
                    chosen_prompt_major = packs[pack_id].prompt_versions[0]
                break

    rationale_bits = []
    if profile is not None:
        rationale_bits.append(f"matched profile {profile.model_id}")
    if task_type:
        rationale_bits.append(f"task={task_type}")
    if target_style:
        rationale_bits.append(f"style={target_style}")
    if known_failure_mode:
        rationale_bits.append(f"failure={known_failure_mode}")
    if chosen_pack_id:
        rationale_bits.append(f"constraint_pack={chosen_pack_id}")

    directives: tuple[str, ...] = ()
    if chosen_pack_id and chosen_pack_id in packs:
        directives = packs[chosen_pack_id].directives

    return RoutingDecision(
        model_id=model_id,
        provider=provider,
        prompt_version=f"{chosen_prompt_major}.0.0",
        constraint_pack_id=chosen_pack_id,
        rationale="; ".join(rationale_bits),
        metadata={
            "task_type": task_type,
            "target_style": target_style,
            "known_failure_mode": known_failure_mode,
            "profile_found": profile is not None,
            "constraint_directives": list(directives),
            "failure_pack_map": failure_pack_map,
        },
    )
