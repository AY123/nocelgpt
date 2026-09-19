import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from runtime.corpus import build_snapshot, query_analysis_books
from runtime.narrative_mining import (
    BookProfileError,
    DeterministicBookProfileAnalyzer,
    load_profile,
    write_profile,
)


ROOT = Path(__file__).parent / "fixtures" / "corpus-xuanhuan-10"


def _schema():
    path = Path(__file__).resolve().parents[2] / "AI-Novel-Standard" / "contracts" / "book-narrative-profile.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _snapshot():
    return build_snapshot(**json.loads((ROOT / "snapshot-input.json").read_text(encoding="utf-8")))


def test_builds_schema_valid_profiles_for_all_canonical_fixture_books():
    snapshot = _snapshot()
    analyzer = DeterministicBookProfileAnalyzer()
    profiles = []
    for book in query_analysis_books(snapshot):
        text = (ROOT / book["relative_path"]).read_text(encoding="utf-8")
        profile = analyzer.analyze(book, text, snapshot=snapshot)
        Draft202012Validator(_schema()).validate(profile)
        profiles.append(profile)
    assert len(profiles) == 7
    assert {profile["corpus_snapshot_id"] for profile in profiles} == {snapshot["id"]}
    assert {profile["corpus_manifest_hash"] for profile in profiles} == {snapshot["manifest_hash"]}


def test_profile_is_abstract_low_confidence_and_contains_no_source_prose():
    snapshot = _snapshot()
    book = query_analysis_books(snapshot)[0]
    text = (ROOT / book["relative_path"]).read_text(encoding="utf-8")
    profile = DeterministicBookProfileAnalyzer().analyze(book, text, snapshot=snapshot)
    rendered = json.dumps(profile, ensure_ascii=False)
    assert profile["analysis"]["method"] == "deterministic"
    assert profile["confidence"]["level"] == "low"
    assert "古井石壁" not in rendered
    assert "第一章" not in rendered
    assert "text" not in _schema()["properties"]
    assert "excerpt" not in _schema()["properties"]


def test_profile_detects_bounded_and_unbounded_progression_differently():
    snapshot = _snapshot()
    books = {book["id"]: book for book in query_analysis_books(snapshot)}
    analyzer = DeterministicBookProfileAnalyzer()
    bounded = analyzer.analyze(books["CBK-00000001"], (ROOT / books["CBK-00000001"]["relative_path"]).read_text(encoding="utf-8"), snapshot=snapshot)
    unbounded = analyzer.analyze(books["CBK-00000007"], (ROOT / books["CBK-00000007"]["relative_path"]).read_text(encoding="utf-8"), snapshot=snapshot)
    assert bounded["progression"]["limitations"]
    assert "unbounded_power_growth" not in bounded["sustainability"]["mid_stage_risks"]
    assert unbounded["progression"]["limitations"] == []
    assert "unbounded_power_growth" in unbounded["sustainability"]["mid_stage_risks"]


def test_rejects_book_outside_bound_snapshot():
    snapshot = _snapshot()
    alien = dict(query_analysis_books(snapshot)[0], id="CBK-99999999")
    with pytest.raises(BookProfileError, match="not a member"):
        DeterministicBookProfileAnalyzer().analyze(alien, "第一章\n合成文本", snapshot=snapshot)


def test_profile_write_load_is_snapshot_scoped(tmp_path):
    snapshot = _snapshot()
    book = query_analysis_books(snapshot)[0]
    text = (ROOT / book["relative_path"]).read_text(encoding="utf-8")
    profile = DeterministicBookProfileAnalyzer().analyze(book, text, snapshot=snapshot)
    rel = write_profile(tmp_path, profile)
    assert rel == f"profiles/{snapshot['id']}/{profile['id']}.json"
    assert load_profile(tmp_path, snapshot["id"], profile["id"]) == profile
    with pytest.raises(BookProfileError, match="unable to load"):
        load_profile(tmp_path, "CORPUS-OTHER", profile["id"])
