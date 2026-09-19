from __future__ import annotations

from runtime.cli import main
import pytest


def test_cli_w12_help_mentions_default_draft_and_confirm(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["candidates", "w12", "--help"])
    out = capsys.readouterr().out
    assert exc.value.code == 0
    assert "Default draft source: registry/derived/drafts" in out
    assert "--confirm" in out
    assert "Default draft source: registry/derived/drafts" in out
