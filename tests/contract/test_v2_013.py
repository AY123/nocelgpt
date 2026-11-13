"""Actual two-Anchor loading, exact identities and immutable project bindings.

These tests verify configuration loading. They do not turn example labels,
world-mechanic declarations or strategy text into semantic policy execution.
"""

import json
import shutil
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest

from anovel.canon.identity import canonical_bytes
from anovel.genre.registry import GenreError, GenreRegistry, PackRef, Selection

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "specs/genres"
URBAN = "urban.business.realistic"
FANTASY = "fantasy.eastern.progression"
ANCHORS = (URBAN, FANTASY)


@pytest.fixture
def catalog(tmp_path):
    target = tmp_path / "genres"
    shutil.copytree(SOURCE, target)
    return target


def document(path):
    return json.loads(path.read_bytes())


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def entries(root):
    return document(root / "registry.yaml")["packs"]


def entry(root, anchor=URBAN):
    return next(value for value in entries(root) if value["id"] == anchor)


def ref(root, anchor=URBAN):
    row = entry(root, anchor)
    return PackRef(row["id"], row["version"], row["content_hash"])


def change_manifest(root, mutate, anchor=URBAN):
    """Keep a valid content pin so negative tests reach structural validation."""
    registry = document(root / "registry.yaml")
    row = next(value for value in registry["packs"] if value["id"] == anchor)
    path = root / row["path"]
    manifest = document(path)
    mutate(manifest)
    write(path, manifest)
    row["content_hash"] = sha256(canonical_bytes(manifest)).hexdigest()
    write(root / "registry.yaml", registry)
    return manifest


@pytest.mark.parametrize("anchor", ANCHORS)
def test_actual_anchor_loads_exact_version_content_profile_and_source_identity(anchor):
    before = {
        p.relative_to(SOURCE): p.read_bytes() for p in SOURCE.rglob("*") if p.is_file()
    }
    registry = GenreRegistry.from_directory(SOURCE)
    requested = ref(SOURCE, anchor)
    pack = registry.load(requested)
    row = entry(SOURCE, anchor)
    raw = (SOURCE / row["path"]).read_bytes()
    manifest = json.loads(raw)
    assert pack.ref == requested
    assert requested.content_hash == sha256(canonical_bytes(manifest)).hexdigest()
    assert pack.manifest_bytes == raw
    assert pack.canonical_manifest_bytes == canonical_bytes(manifest)
    assert pack.to_dict() == manifest
    assert pack.source_path == row["path"]
    assert Path(pack.catalog_path) == SOURCE.resolve() / "registry.yaml"
    assert pack.source_file_sha256 == sha256(raw).hexdigest()
    assert (
        pack.catalog_source_sha256
        == sha256((SOURCE / "registry.yaml").read_bytes()).hexdigest()
    )
    profile = dict(manifest["profile"], version=requested.version)
    assert pack.profile.anchor == anchor
    assert pack.profile.version == requested.version
    assert pack.profile.to_dict() == profile
    assert pack.profile.content_hash == sha256(canonical_bytes(profile)).hexdigest()
    assert pack.extensions == ()
    assert isinstance(pack.strategies, tuple) and pack.strategies
    assert isinstance(pack.rubric, tuple) and pack.rubric
    assert isinstance(pack.examples, tuple) and pack.examples
    assert isinstance(pack.consumers, tuple) and pack.consumers
    assert {
        p.relative_to(SOURCE): p.read_bytes() for p in SOURCE.rglob("*") if p.is_file()
    } == before


def test_catalog_has_only_the_two_frozen_anchors_and_distinct_profiles():
    registry = GenreRegistry.from_directory(SOURCE)
    assert isinstance(registry.packs, tuple)
    assert {pack.ref.id for pack in registry.packs} == set(ANCHORS)
    urban = registry.load(ref(SOURCE, URBAN))
    fantasy = registry.load(ref(SOURCE, FANTASY))
    assert urban.profile.reality_model != fantasy.profile.reality_model
    assert urban.profile.setting_model != fantasy.profile.setting_model
    assert urban.profile.world_mechanics != fantasy.profile.world_mechanics
    assert urban.profile.content_hash != fantasy.profile.content_hash


@pytest.mark.parametrize(
    "field,value",
    [("id", "missing.pack"), ("version", "999.0.0"), ("content_hash", "0" * 64)],
)
def test_load_requires_all_three_exact_reference_components(field, value):
    registry = GenreRegistry.from_directory(SOURCE)
    requested = ref(SOURCE)
    values = {
        "id": requested.id,
        "version": requested.version,
        "content_hash": requested.content_hash,
    }
    values[field] = value
    with pytest.raises(GenreError):
        registry.load(PackRef(**values))


@pytest.mark.parametrize(
    "field,value",
    [
        ("id", ""),
        ("id", True),
        ("version", ""),
        ("version", True),
        ("content_hash", "short"),
        ("content_hash", True),
    ],
)
def test_malformed_pack_reference_is_rejected(field, value):
    requested = ref(SOURCE)
    values = {
        "id": requested.id,
        "version": requested.version,
        "content_hash": requested.content_hash,
    }
    values[field] = value
    with pytest.raises(GenreError):
        PackRef(**values)


@pytest.mark.parametrize("field,value", [("id", FANTASY), ("version", "2.0.0")])
def test_manifest_identity_must_match_catalog_even_when_content_hash_is_updated(
    catalog, field, value
):
    change_manifest(catalog, lambda manifest: manifest.__setitem__(field, value))
    with pytest.raises(GenreError):
        GenreRegistry.from_directory(catalog)


def test_changed_manifest_without_updated_hash_is_not_trusted(catalog):
    path = catalog / entry(catalog)["path"]
    manifest = document(path)
    manifest["rubric"][0] += " changed"
    write(path, manifest)
    with pytest.raises(GenreError):
        GenreRegistry.from_directory(catalog)


@pytest.mark.parametrize(
    "extensions",
    [
        ["unknown.extension"],
        [{"namespace": "urban.business.realistic.fake", "version": "1.0.0"}],
    ],
)
def test_unimplemented_extension_cannot_be_enabled_by_manifest_declaration(
    catalog, extensions
):
    change_manifest(
        catalog, lambda manifest: manifest.__setitem__("extensions", extensions)
    )
    with pytest.raises(GenreError):
        GenreRegistry.from_directory(catalog)


@pytest.mark.parametrize(
    "change",
    [
        "unknown-field",
        "missing-profile",
        "profile-extra-field",
        "wrong-anchor",
        "mechanics-type",
        "strategy-purpose-type",
        "examples-type",
    ],
)
def test_closed_manifest_and_nested_contracts_reject_malformed_data(catalog, change):
    def mutate(manifest):
        if change == "unknown-field":
            manifest["default_pack"] = FANTASY
        elif change == "missing-profile":
            manifest.pop("profile")
        elif change == "profile-extra-field":
            manifest["profile"]["rebirth_default"] = True
        elif change == "wrong-anchor":
            manifest["profile"]["anchor"] = FANTASY
        elif change == "mechanics-type":
            manifest["profile"]["world_mechanics"] = "not-an-array"
        elif change == "strategy-purpose-type":
            manifest["strategies"][0]["purpose"] = False
        else:
            manifest["examples"] = {}

    change_manifest(catalog, mutate)
    with pytest.raises(GenreError):
        GenreRegistry.from_directory(catalog)


@pytest.mark.parametrize(
    "change",
    [
        "duplicate-ref",
        "unknown-field",
        "missing-packs",
        "wrong-version",
        "packs-not-array",
    ],
)
def test_catalog_contract_rejects_ambiguous_or_malformed_metadata(catalog, change):
    path = catalog / "registry.yaml"
    registry = document(path)
    if change == "duplicate-ref":
        registry["packs"].append(dict(registry["packs"][0]))
    elif change == "unknown-field":
        registry["fallback"] = URBAN
    elif change == "missing-packs":
        registry.pop("packs")
    elif change == "wrong-version":
        registry["schema_version"] = "999.0"
    else:
        registry["packs"] = {}
    write(path, registry)
    with pytest.raises(GenreError):
        GenreRegistry.from_directory(catalog)


@pytest.mark.parametrize(
    "raw",
    [
        b'{"schema_version":"1.0","schema_version":"1.0","packs":[]}',
        b'{"schema_version":NaN,"packs":[]}',
        b"[]",
        b"null",
        b"\xff",
        b'schema_version: "1.0"\npacks: []\n',
    ],
)
def test_catalog_accepts_only_strict_finite_duplicate_free_json_subset(catalog, raw):
    (catalog / "registry.yaml").write_bytes(raw)
    with pytest.raises(GenreError):
        GenreRegistry.from_directory(catalog)


@pytest.mark.parametrize("change", ["duplicate-key", "nonfinite", "invalid-utf8"])
def test_manifest_parser_rejects_invalid_source_bytes(catalog, change):
    path = catalog / entry(catalog)["path"]
    raw = path.read_bytes()
    if change == "duplicate-key":
        altered = b'{"schema_version":"1.0",' + raw.lstrip()[1:]
    elif change == "nonfinite":
        manifest = json.loads(raw)
        manifest["profile"]["setting_model"] = float("inf")
        altered = json.dumps(manifest).encode()
    else:
        altered = b"\xff"
    path.write_bytes(altered)
    with pytest.raises(GenreError):
        GenreRegistry.from_directory(catalog)


@pytest.mark.parametrize("path_kind", ["absolute", "parent-escape", "dot-parent"])
def test_manifest_source_path_cannot_escape_or_hide_path_components(
    catalog, tmp_path, path_kind
):
    path = catalog / "registry.yaml"
    registry = document(path)
    row = registry["packs"][0]
    original = catalog / row["path"]
    if path_kind == "absolute":
        row["path"] = str(original.resolve())
    elif path_kind == "parent-escape":
        outside = tmp_path / "outside.json"
        outside.write_bytes(original.read_bytes())
        row["path"] = "../outside.json"
    else:
        (catalog / "unused").mkdir()
        row["path"] = "unused/../" + row["path"]
    write(path, registry)
    with pytest.raises(GenreError):
        GenreRegistry.from_directory(catalog)


@pytest.mark.parametrize("kind", ["manifest", "parent-directory", "catalog", "root"])
def test_symlinked_catalog_sources_are_rejected(catalog, tmp_path, kind):
    target = catalog
    if kind == "root":
        target = tmp_path / "linked-root"
        target.symlink_to(catalog, target_is_directory=True)
    elif kind == "catalog":
        source = catalog / "registry.yaml"
        outside = tmp_path / "catalog.json"
        source.rename(outside)
        source.symlink_to(outside)
    elif kind == "manifest":
        source = catalog / entry(catalog)["path"]
        outside = tmp_path / "manifest.json"
        source.rename(outside)
        source.symlink_to(outside)
    else:
        source = catalog / entry(catalog)["path"]
        directory = source.parent
        outside = tmp_path / "manifest-directory"
        directory.rename(outside)
        directory.symlink_to(outside, target_is_directory=True)
    with pytest.raises(GenreError):
        GenreRegistry.from_directory(target)


def test_missing_catalog_or_manifest_is_a_failure_without_default_pack(
    catalog, tmp_path
):
    with pytest.raises(GenreError):
        GenreRegistry.from_directory(tmp_path / "missing")
    (catalog / entry(catalog)["path"]).unlink()
    with pytest.raises(GenreError):
        GenreRegistry.from_directory(catalog)


def test_project_binding_keeps_complete_global_source_and_distinct_project_scope(
    catalog,
):
    before = {
        p.relative_to(catalog): p.read_bytes()
        for p in catalog.rglob("*")
        if p.is_file()
    }
    registry = GenreRegistry.from_directory(catalog)
    requested = ref(catalog)
    first = registry.bind("book-one", requested)
    second = registry.bind("book-two", requested)
    assert first.project == "book-one" and second.project == "book-two"
    assert first.ref == second.ref == requested
    assert first.profile == second.profile == first.pack.profile
    assert first.pack.manifest_bytes == second.pack.manifest_bytes
    assert (
        first.pack.catalog_source_sha256
        == sha256((catalog / "registry.yaml").read_bytes()).hexdigest()
    )
    assert first.to_dict()["project"] == "book-one"
    assert second.to_dict()["project"] == "book-two"
    assert {
        p.relative_to(catalog): p.read_bytes()
        for p in catalog.rglob("*")
        if p.is_file()
    } == before


@pytest.mark.parametrize("project", ["", True, None])
def test_project_binding_requires_an_explicit_valid_project(project):
    registry = GenreRegistry.from_directory(SOURCE)
    with pytest.raises(GenreError):
        registry.bind(project, ref(SOURCE))


def test_binding_and_all_loaded_values_are_frozen_and_exports_are_independent(catalog):
    binding = GenreRegistry.from_directory(catalog).bind("book", ref(catalog))
    original = binding.pack.to_dict()
    for obj, name, value in [
        (binding, "project", "other"),
        (binding.ref, "version", "2.0.0"),
        (binding.profile, "anchor", FANTASY),
        (binding.pack.strategies[0], "purpose", "changed"),
        (binding.pack.examples[0], "text", "changed"),
    ]:
        with pytest.raises(AttributeError):
            setattr(obj, name, value)
    exported = binding.pack.to_dict()
    exported["profile"]["world_mechanics"].append("forged")
    exported["strategies"][0]["purpose"] = "forged"
    exported["examples"][0]["text"] = "forged"
    exported["rubric"].clear()
    binding_export = binding.to_dict()
    binding_export["project"] = "forged"
    assert binding.project == "book"
    assert binding.pack.to_dict() == original
    assert binding.profile.anchor == URBAN


@pytest.mark.parametrize("anchor", ANCHORS)
def test_exact_optional_strategy_match_keeps_the_original_binding(anchor):
    binding = GenreRegistry.from_directory(SOURCE).bind("book", ref(SOURCE, anchor))
    strategy = binding.pack.strategies[0]
    result = binding.select_strategy(strategy.id)
    assert result.status is Selection.MATCH
    assert result.binding is binding
    assert result.binding.ref == binding.ref
    assert result.strategy == strategy


@pytest.mark.parametrize("anchor", ANCHORS)
def test_optional_strategy_miss_keeps_explicit_pack_instead_of_first_neighbor(anchor):
    registry = GenreRegistry.from_directory(SOURCE)
    binding = registry.bind("book", ref(SOURCE, anchor))
    frozen = binding.to_dict()
    first = binding.pack.strategies[0]
    other = registry.load(ref(SOURCE, FANTASY if anchor == URBAN else URBAN))
    foreign_only = next(
        (
            s.id
            for s in other.strategies
            if s.id not in {x.id for x in binding.pack.strategies}
        ),
        None,
    )
    assert foreign_only is not None, (
        "Actual packs need distinct optional strategies for the cross-Pack control"
    )
    for query in [None, "not-a-strategy", first.id + ".nearby", foreign_only]:
        result = binding.select_strategy(query)
        assert result.status is Selection.NO_MATCH
        assert result.strategy is None
        assert result.binding is binding
        assert result.binding.ref == binding.ref
        assert result.binding.to_dict() == frozen


def test_binding_survives_directory_version_change_without_implicit_upgrade(catalog):
    registry = GenreRegistry.from_directory(catalog)
    old_ref = ref(catalog)
    binding = registry.bind("book", old_ref)
    snapshot = binding.to_dict()
    original_raw = binding.pack.manifest_bytes
    old_source = binding.pack.source_file_sha256
    old_catalog = binding.pack.catalog_source_sha256
    metadata = document(catalog / "registry.yaml")
    row = next(value for value in metadata["packs"] if value["id"] == URBAN)
    manifest_path = catalog / row["path"]
    updated = document(manifest_path)
    updated["version"] = "1.0.1"
    updated["strategies"][0]["purpose"] += " revision"
    write(manifest_path, updated)
    row["version"] = updated["version"]
    row["content_hash"] = sha256(canonical_bytes(updated)).hexdigest()
    write(catalog / "registry.yaml", metadata)
    changed_registry = GenreRegistry.from_directory(catalog)
    new_pack = changed_registry.load(ref(catalog))
    assert new_pack.ref.version == "1.0.1"
    assert new_pack.source_file_sha256 != old_source
    assert new_pack.catalog_source_sha256 != old_catalog
    assert binding.ref == old_ref
    assert binding.pack.manifest_bytes == original_raw
    assert binding.to_dict() == snapshot
    with pytest.raises(GenreError):
        changed_registry.load(old_ref)


@pytest.mark.parametrize("query", [True, 1, {}, ""])
def test_malformed_strategy_query_is_not_an_implicit_default(query):
    binding = GenreRegistry.from_directory(SOURCE).bind("book", ref(SOURCE))
    with pytest.raises(GenreError):
        binding.select_strategy(query)
    assert binding.select_strategy().status is Selection.NO_MATCH


def test_direct_registry_cannot_keep_mutable_or_duplicate_entries():
    registry = GenreRegistry.from_directory(SOURCE)
    for packs in [
        list(registry.packs),
        (),
        (registry.packs[0], registry.packs[0]),
        (None,),
    ]:
        with pytest.raises(GenreError):
            GenreRegistry(packs)


def test_retained_manifest_cannot_claim_a_different_catalog_source_path():
    pack = GenreRegistry.from_directory(SOURCE).load(ref(SOURCE))
    with pytest.raises(GenreError):
        replace(pack, source_path="unrelated/pack.json")


def test_selection_cannot_claim_an_unbound_foreign_strategy():
    registry = GenreRegistry.from_directory(SOURCE)
    binding = registry.bind("book", ref(SOURCE))
    foreign = registry.load(ref(SOURCE, FANTASY)).strategies[0]
    valid = binding.select_strategy(binding.pack.strategies[0].id)
    with pytest.raises(GenreError):
        replace(valid, strategy=foreign)
    with pytest.raises(GenreError):
        replace(valid, status=Selection.NO_MATCH)
