"""Read-only, exact-identity GenrePack loading for the two frozen Anchors.

JSON is the supported YAML subset. Manifests are inert configuration, never
plugins, Canon writes, semantic fact approval or production certification.
"""

from __future__ import annotations

import json
import re
from base64 import b64decode, b64encode
from binascii import Error as Base64Error
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import cast

from anovel.canon.identity import canonical_bytes
from anovel.domain.identity import EntityId
from anovel.genre.extensions.contracts import (
    BUSINESS_NAMESPACE,
    BUSINESS_SCHEMA_HASH,
    BUSINESS_SCHEMA_ID,
    BUSINESS_VERSION,
)

ANCHORS = frozenset({"urban.business.realistic", "fantasy.eastern.progression"})
EXAMPLE_KINDS = frozenset({"LEGAL", "POLLUTION", "QUOTATION", "UNCERTAIN"})


class GenreError(ValueError):
    """Invalid, missing, unsupported or mismatched genre configuration."""


def _text(value: object, field: str) -> str:
    if type(value) is not str or not value.strip():
        raise GenreError(f"{field} must be a nonempty string")
    return value


def _digest(value: object) -> str:
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise GenreError("expected a lowercase SHA256 digest")
    return value


def _version(value: object) -> str:
    text = _text(value, "version")
    if re.fullmatch(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", text) is None:
        raise GenreError("Pack versions must be exact major.minor.patch")
    return text


def _record(value: object, keys: set[str], field: str) -> dict[str, object]:
    if type(value) is not dict or set(value) != keys:
        raise GenreError(f"{field} has missing or unknown fields")
    return cast(dict[str, object], value)


def _array(value: object, field: str) -> list[object]:
    if type(value) is not list:
        raise GenreError(f"{field} must be an array")
    return cast(list[object], value)


def _strings(value: object, field: str) -> tuple[str, ...]:
    items = tuple(_text(item, field) for item in _array(value, field))
    if len(items) != len(set(items)):
        raise GenreError(f"{field} contains duplicate entries")
    return items


def _unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise GenreError("duplicate JSON key")
        result[key] = value
    return result


def _constant(_value: str) -> object:
    raise GenreError("non-finite JSON is not supported")


def _document(raw: bytes) -> object:
    try:
        result: object = json.loads(
            raw.decode("utf-8"), object_pairs_hook=_unique, parse_constant=_constant
        )
        canonical_bytes(result)
        return result
    except (UnicodeError, ValueError, RecursionError) as error:
        raise GenreError("invalid strict JSON genre document") from error


def _file(root: Path, relative: str) -> Path:
    path = PurePosixPath(relative)
    if (
        not relative
        or path.is_absolute()
        or str(path) != relative
        or any(part in {".", ".."} for part in path.parts)
        or "\\" in relative
        or ":" in relative
    ):
        raise GenreError("genre paths must remain relative to the catalog")
    current = root
    for component in path.parts:
        current = current / component
        if current.is_symlink():
            raise GenreError("genre paths cannot use symlinks")
    if not current.is_file() or not current.resolve().is_relative_to(root):
        raise GenreError("genre source is missing or outside the catalog")
    return current


@dataclass(frozen=True, slots=True)
class PackRef:
    id: str
    version: str
    content_hash: str

    def __post_init__(self) -> None:
        _text(self.id, "Pack ID")
        _version(self.version)
        _digest(self.content_hash)

    def to_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "version": self.version,
            "content_hash": self.content_hash,
        }


@dataclass(frozen=True, slots=True)
class GenreProfile:
    anchor: str
    version: str
    reality_model: str
    setting_model: str
    world_mechanics: tuple[str, ...]
    forbidden_mechanics: tuple[str, ...]

    def __post_init__(self) -> None:
        if _text(self.anchor, "Anchor") not in ANCHORS:
            raise GenreError("unsupported Anchor")
        _version(self.version)
        _text(self.reality_model, "reality model")
        _text(self.setting_model, "setting model")
        for values in (self.world_mechanics, self.forbidden_mechanics):
            if type(values) is not tuple or any(
                type(v) is not str or not v.strip() for v in values
            ):
                raise GenreError("profile mechanics must be immutable strings")
            if len(values) != len(set(values)):
                raise GenreError("duplicate profile mechanics")

    def to_dict(self) -> dict[str, object]:
        return {
            "anchor": self.anchor,
            "version": self.version,
            "reality_model": self.reality_model,
            "setting_model": self.setting_model,
            "world_mechanics": list(self.world_mechanics),
            "forbidden_mechanics": list(self.forbidden_mechanics),
        }

    def _manifest(self) -> dict[str, object]:
        result = self.to_dict()
        result.pop("version")
        return result

    @property
    def content_hash(self) -> str:
        return sha256(canonical_bytes(self.to_dict())).hexdigest()


@dataclass(frozen=True, slots=True)
class NarrativeStrategy:
    id: str
    purpose: str

    def __post_init__(self) -> None:
        _text(self.id, "strategy ID")
        _text(self.purpose, "strategy purpose")

    def to_dict(self) -> dict[str, str]:
        return {"id": self.id, "purpose": self.purpose}


@dataclass(frozen=True, slots=True)
class PackExample:
    id: str
    kind: str
    text: str

    def __post_init__(self) -> None:
        _text(self.id, "example ID")
        if type(self.kind) is not str or self.kind not in EXAMPLE_KINDS:
            raise GenreError("unsupported example kind")
        _text(self.text, "example text")

    def to_dict(self) -> dict[str, str]:
        return {"id": self.id, "kind": self.kind, "text": self.text}


@dataclass(frozen=True, slots=True)
class ExtensionRef:
    namespace: str
    version: str
    schema_id: str
    schema_hash: str

    def __post_init__(self) -> None:
        if (self.namespace, self.version, self.schema_id, self.schema_hash) != (
            BUSINESS_NAMESPACE,
            BUSINESS_VERSION,
            BUSINESS_SCHEMA_ID,
            BUSINESS_SCHEMA_HASH,
        ) or any(
            type(v) is not str
            for v in (self.namespace, self.version, self.schema_id, self.schema_hash)
        ):
            raise GenreError("extension has no exact compiled registration")

    def to_dict(self) -> dict[str, str]:
        return {
            "namespace": self.namespace,
            "version": self.version,
            "schema_id": self.schema_id,
            "schema_hash": self.schema_hash,
        }

    @classmethod
    def from_dict(cls, value: object) -> ExtensionRef:
        row = _record(
            value, {"namespace", "version", "schema_id", "schema_hash"}, "extension"
        )
        return cls(
            *(
                _text(row[k], k)
                for k in ("namespace", "version", "schema_id", "schema_hash")
            )
        )


@dataclass(frozen=True, slots=True)
class GenrePack:
    ref: PackRef
    profile: GenreProfile
    extensions: tuple[ExtensionRef, ...]
    strategies: tuple[NarrativeStrategy, ...]
    rubric: tuple[str, ...]
    examples: tuple[PackExample, ...]
    consumers: tuple[str, ...]
    source_path: str
    catalog_path: str
    source_file_sha256: str
    catalog_source_sha256: str
    manifest_bytes: bytes
    canonical_manifest_bytes: bytes
    catalog_bytes: bytes

    def __post_init__(self) -> None:
        if type(self.ref) is not PackRef or type(self.profile) is not GenreProfile:
            raise GenreError("Pack needs exact ref and profile types")
        if (
            self.ref.id != self.profile.anchor
            or self.ref.version != self.profile.version
        ):
            raise GenreError("Pack and Profile identities differ")
        if (
            type(self.extensions) is not tuple
            or any(type(item) is not ExtensionRef for item in self.extensions)
            or len({item.namespace for item in self.extensions}) != len(self.extensions)
            or (self.extensions and self.ref.id != "urban.business.realistic")
        ):
            raise GenreError(
                "Pack has an unknown, duplicated or cross-Anchor extension"
            )
        for values, kind in (
            (self.strategies, NarrativeStrategy),
            (self.examples, PackExample),
        ):
            if type(values) is not tuple or any(type(v) is not kind for v in values):
                raise GenreError("Pack metadata must use exact immutable values")
            if len({v.id for v in values}) != len(values):
                raise GenreError("duplicate strategy or example ID")
        for texts in (self.rubric, self.consumers):
            if (
                type(texts) is not tuple
                or not texts
                or any(type(v) is not str or not v.strip() for v in texts)
            ):
                raise GenreError(
                    "Pack rubric/consumers need immutable nonempty strings"
                )
        for raw in (
            self.manifest_bytes,
            self.canonical_manifest_bytes,
            self.catalog_bytes,
        ):
            if type(raw) is not bytes or not raw:
                raise GenreError("source bytes must be complete and immutable")
        if (
            sha256(self.manifest_bytes).hexdigest() != _digest(self.source_file_sha256)
            or sha256(self.catalog_bytes).hexdigest()
            != _digest(self.catalog_source_sha256)
            or sha256(self.canonical_manifest_bytes).hexdigest()
            != self.ref.content_hash
            or canonical_bytes(_document(self.manifest_bytes))
            != self.canonical_manifest_bytes
            or canonical_bytes(self.to_dict()) != self.canonical_manifest_bytes
        ):
            raise GenreError("Pack bytes, content and source identities differ")
        _text(self.source_path, "source path")
        _text(self.catalog_path, "catalog path")
        catalog = _record(
            _document(self.catalog_bytes), {"schema_version", "packs"}, "catalog"
        )
        expected = {**self.ref.to_dict(), "path": self.source_path}
        matches = [row for row in _array(catalog["packs"], "packs") if row == expected]
        if catalog["schema_version"] != "1.0" or len(matches) != 1:
            raise GenreError("Pack source is not uniquely declared in its catalog")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "id": self.ref.id,
            "version": self.ref.version,
            "profile": self.profile._manifest(),
            "extensions": [item.to_dict() for item in self.extensions],
            "strategies": [s.to_dict() for s in self.strategies],
            "rubric": list(self.rubric),
            "examples": [e.to_dict() for e in self.examples],
            "consumers": list(self.consumers),
        }


class Selection(str, Enum):
    MATCH = "MATCH"
    NO_MATCH = "NO_MATCH"


@dataclass(frozen=True, slots=True)
class ProjectGenreBinding:
    project: str
    pack: GenrePack

    def __post_init__(self) -> None:
        try:
            EntityId(self.project, "genre-binding")
        except ValueError as error:
            raise GenreError("invalid project scope") from error
        if (
            type(self.project) is not str
            or not self.project.strip()
            or type(self.pack) is not GenrePack
        ):
            raise GenreError("binding needs exact project and Pack")

    @property
    def ref(self) -> PackRef:
        return self.pack.ref

    @property
    def profile(self) -> GenreProfile:
        return self.pack.profile

    def select_strategy(self, exact_id: str | None = None) -> StrategySelection:
        if exact_id is not None:
            _text(exact_id, "strategy query")
        strategy = next((s for s in self.pack.strategies if s.id == exact_id), None)
        return StrategySelection(
            Selection.MATCH if strategy else Selection.NO_MATCH, self, strategy
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "project": self.project,
            "pack_ref": self.ref.to_dict(),
            "profile": self.profile.to_dict(),
            "manifest": self.pack.to_dict(),
            "source_path": self.pack.source_path,
            "catalog_path": self.pack.catalog_path,
            "source_file_sha256": self.pack.source_file_sha256,
            "catalog_source_sha256": self.pack.catalog_source_sha256,
            "manifest_base64": b64encode(self.pack.manifest_bytes).decode("ascii"),
            "canonical_manifest_base64": b64encode(
                self.pack.canonical_manifest_bytes
            ).decode("ascii"),
            "catalog_base64": b64encode(self.pack.catalog_bytes).decode("ascii"),
        }

    @classmethod
    def from_dict(cls, value: object) -> ProjectGenreBinding:
        """Restore retained bytes offline; never select from the current catalog."""
        row = _record(
            value,
            {
                "project",
                "pack_ref",
                "profile",
                "manifest",
                "source_path",
                "catalog_path",
                "source_file_sha256",
                "catalog_source_sha256",
                "manifest_base64",
                "canonical_manifest_base64",
                "catalog_base64",
            },
            "project genre binding",
        )
        ref = _record(row["pack_ref"], {"id", "version", "content_hash"}, "Pack ref")

        def raw(field: str) -> bytes:
            encoded = _text(row[field], field)
            try:
                decoded = b64decode(encoded, validate=True)
            except (ValueError, Base64Error) as error:
                raise GenreError("invalid retained genre bytes") from error
            if b64encode(decoded).decode("ascii") != encoded:
                raise GenreError("noncanonical retained genre bytes")
            return decoded

        pack = _load_pack(
            PackRef(
                _text(ref["id"], "Pack ID"),
                _text(ref["version"], "version"),
                _text(ref["content_hash"], "hash"),
            ),
            raw("manifest_base64"),
            _text(row["source_path"], "source path"),
            _text(row["catalog_path"], "catalog path"),
            raw("catalog_base64"),
        )
        result = cls(_text(row["project"], "project"), pack)
        if result.to_dict() != row:
            raise GenreError("retained genre identities or source bytes differ")
        return result


@dataclass(frozen=True, slots=True)
class StrategySelection:
    status: Selection
    binding: ProjectGenreBinding
    strategy: NarrativeStrategy | None

    def __post_init__(self) -> None:
        if (
            type(self.status) is not Selection
            or type(self.binding) is not ProjectGenreBinding
        ):
            raise GenreError("selection requires exact status and project binding")
        if self.status is Selection.NO_MATCH:
            if self.strategy is not None:
                raise GenreError("no-match selection cannot contain a strategy")
        elif (
            type(self.strategy) is not NarrativeStrategy
            or self.strategy not in self.binding.pack.strategies
        ):
            raise GenreError("selected strategy must belong to the bound Pack")


@dataclass(frozen=True, slots=True)
class GenreRegistry:
    packs: tuple[GenrePack, ...]

    def __post_init__(self) -> None:
        if (
            type(self.packs) is not tuple
            or not self.packs
            or any(type(p) is not GenrePack for p in self.packs)
        ):
            raise GenreError("registry requires an immutable nonempty Pack tuple")
        identities = [(p.ref.id, p.ref.version) for p in self.packs]
        if len(identities) != len(set(identities)):
            raise GenreError("registry contains duplicate Pack identities")

    @classmethod
    def from_directory(cls, directory: Path | str) -> GenreRegistry:
        root = Path(directory).absolute()
        if any(p.is_symlink() for p in (root, *root.parents)) or not root.is_dir():
            raise GenreError("catalog root must be a real directory without symlinks")
        root = root.resolve()
        catalog_file = _file(root, "registry.yaml")
        try:
            catalog_raw = catalog_file.read_bytes()
            catalog = _record(
                _document(catalog_raw), {"schema_version", "packs"}, "catalog"
            )
            if catalog["schema_version"] != "1.0":
                raise GenreError("unsupported catalog schema")
            packs = []
            seen: set[tuple[str, str]] = set()
            for item in _array(catalog["packs"], "packs"):
                row = _record(
                    item, {"id", "version", "content_hash", "path"}, "catalog Pack"
                )
                ref = PackRef(
                    _text(row["id"], "Pack ID"),
                    _version(row["version"]),
                    _digest(row["content_hash"]),
                )
                if ref.id not in ANCHORS or (ref.id, ref.version) in seen:
                    raise GenreError("unknown or duplicate Pack identity")
                seen.add((ref.id, ref.version))
                relative = _text(row["path"], "manifest path")
                raw = _file(root, relative).read_bytes()
                packs.append(
                    _load_pack(ref, raw, relative, str(catalog_file), catalog_raw)
                )
            if not packs:
                raise GenreError("catalog must contain an explicit Pack")
            return cls(tuple(packs))
        except OSError as error:
            raise GenreError("genre source cannot be read") from error

    def load(self, ref: PackRef) -> GenrePack:
        if type(ref) is not PackRef:
            raise GenreError("an exact complete PackRef is required")
        pack = next(
            (
                p
                for p in self.packs
                if (p.ref.id, p.ref.version) == (ref.id, ref.version)
            ),
            None,
        )
        if pack is None or pack.ref != ref:
            raise GenreError("Pack ID, version or hash is missing/mismatched")
        return pack

    def bind(self, project: str, ref: PackRef) -> ProjectGenreBinding:
        return ProjectGenreBinding(project, self.load(ref))


def _load_pack(
    ref: PackRef, raw: bytes, relative: str, catalog_path: str, catalog_raw: bytes
) -> GenrePack:
    manifest = _record(
        _document(raw),
        {
            "schema_version",
            "id",
            "version",
            "profile",
            "extensions",
            "strategies",
            "rubric",
            "examples",
            "consumers",
        },
        "Pack manifest",
    )
    canonical = canonical_bytes(manifest)
    if (
        manifest["schema_version"] != "1.0"
        or manifest["id"] != ref.id
        or manifest["version"] != ref.version
        or sha256(canonical).hexdigest() != ref.content_hash
    ):
        raise GenreError("manifest identity does not match catalog")
    p = _record(
        manifest["profile"],
        {
            "anchor",
            "reality_model",
            "setting_model",
            "world_mechanics",
            "forbidden_mechanics",
        },
        "Profile",
    )
    profile = GenreProfile(
        _text(p["anchor"], "Anchor"),
        ref.version,
        _text(p["reality_model"], "reality model"),
        _text(p["setting_model"], "setting model"),
        _strings(p["world_mechanics"], "world mechanics"),
        _strings(p["forbidden_mechanics"], "forbidden mechanics"),
    )
    strategies = []
    for value in _array(manifest["strategies"], "strategies"):
        s = _record(value, {"id", "purpose"}, "strategy")
        strategies.append(
            NarrativeStrategy(
                _text(s["id"], "strategy ID"), _text(s["purpose"], "strategy purpose")
            )
        )
    examples = []
    for value in _array(manifest["examples"], "examples"):
        e = _record(value, {"id", "kind", "text"}, "example")
        examples.append(
            PackExample(
                _text(e["id"], "example ID"),
                _text(e["kind"], "example kind"),
                _text(e["text"], "example text"),
            )
        )
    return GenrePack(
        ref,
        profile,
        tuple(
            ExtensionRef.from_dict(item)
            for item in _array(manifest["extensions"], "extensions")
        ),
        tuple(strategies),
        _strings(manifest["rubric"], "rubric"),
        tuple(examples),
        _strings(manifest["consumers"], "consumers"),
        relative,
        catalog_path,
        sha256(raw).hexdigest(),
        sha256(catalog_raw).hexdigest(),
        raw,
        canonical,
        catalog_raw,
    )
