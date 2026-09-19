from runtime.serialize.version_matrix import build_version_matrix


def test_version_matrix_has_all_dimensions():
    matrix = build_version_matrix()
    data = matrix.to_dict()

    assert data["kind"] == "version_matrix"
    assert data["comparison_only"] is True
    assert data["gating"] is False
    assert len(data["dimensions"]) == 5

    dims = {d["dimension"] for d in data["dimensions"]}
    assert dims == {"pipeline", "prompt", "schema", "model", "reviewer"}


def test_version_matrix_prompt_has_multiple_versions():
    matrix = build_version_matrix()
    prompt_dim = next(d for d in matrix.dimensions if d.dimension == "prompt")

    assert len(prompt_dim.available_versions) >= 12
    assert prompt_dim.current_version == "v12"
