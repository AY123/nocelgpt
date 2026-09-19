from __future__ import annotations

from runtime.serialize.quality_rubric import (
    RUBRIC_DIMENSIONS,
    RUBRIC_FILENAME,
    RUBRIC_ID,
    RUBRIC_VERSION,
    build_quality_rubric,
    render_quality_rubric_yaml,
)


def test_quality_rubric_shape():
    rubric = build_quality_rubric().to_dict()

    assert rubric["id"] == RUBRIC_ID
    assert rubric["kind"] == "quality_rubric"
    assert rubric["version"] == RUBRIC_VERSION
    assert rubric["scoring_scale"] == "0-100"
    assert rubric["review_policy"]["blocking"] is False
    assert len(rubric["dimensions"]) == len(RUBRIC_DIMENSIONS)
    assert {dim["id"] for dim in rubric["dimensions"]} == {dim["id"] for dim in RUBRIC_DIMENSIONS}


def test_quality_rubric_yaml_contains_expected_sections():
    yaml_text = render_quality_rubric_yaml()

    assert f'id: "{RUBRIC_ID}"' in yaml_text
    assert f'version: "{RUBRIC_VERSION}"' in yaml_text
    assert "dimensions:" in yaml_text
    assert "review_policy:" in yaml_text
    assert RUBRIC_FILENAME.endswith(".yaml")
