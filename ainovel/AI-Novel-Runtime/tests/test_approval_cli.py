from __future__ import annotations

from runtime import cli
from runtime.approval import ApprovalQueue, create_approval_request, load_approval_queue


def _seed(project_path):
    queue = ApprovalQueue(project_path=project_path)
    queue.enqueue(create_approval_request(
        request_id="APR-PUB-00001", target_type="publish", target_id="TASK-1",
        action="confirm_publish", reason="chapter ready",
        requested_by={"module": "publishing.card"}))
    queue.enqueue(create_approval_request(
        request_id="APR-MINT-00001", target_type="mint", target_id="CAND-1",
        action="confirm_mint", reason="fact write"))


def test_cli_list_defaults_to_pending(tmp_path, capsys):
    _seed(tmp_path)
    rc = cli.main(["approval", "list", "--project", str(tmp_path)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "APR-PUB-00001" in out
    assert "APR-MINT-00001" in out


def test_cli_approve_flips_status_and_persists(tmp_path, capsys):
    _seed(tmp_path)
    rc = cli.main(["approval", "approve", "--project", str(tmp_path),
                   "--id", "APR-PUB-00001", "--by", "human", "--notes", "ok"])
    assert rc == 0
    capsys.readouterr()

    # the decided request drops out of the pending list
    rc = cli.main(["approval", "list", "--project", str(tmp_path)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "APR-PUB-00001" not in out
    assert "APR-MINT-00001" in out

    # and the decision survives on disk
    reloaded = load_approval_queue(tmp_path)
    assert reloaded.get_request("APR-PUB-00001").status == "approved"
    assert reloaded.records_for("APR-PUB-00001")[0].decision == "approved"


def test_cli_reject_records_rejection(tmp_path, capsys):
    _seed(tmp_path)
    rc = cli.main(["approval", "reject", "--project", str(tmp_path),
                   "--id", "APR-MINT-00001", "--by", "human"])
    assert rc == 0
    capsys.readouterr()
    reloaded = load_approval_queue(tmp_path)
    assert reloaded.get_request("APR-MINT-00001").status == "rejected"


def test_cli_re_deciding_terminal_request_returns_error(tmp_path, capsys):
    _seed(tmp_path)
    cli.main(["approval", "approve", "--project", str(tmp_path),
              "--id", "APR-PUB-00001", "--by", "human"])
    capsys.readouterr()
    rc = cli.main(["approval", "approve", "--project", str(tmp_path),
                   "--id", "APR-PUB-00001", "--by", "human"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "terminal state" in out


def test_cli_show_unknown_request_returns_error(tmp_path, capsys):
    _seed(tmp_path)
    rc = cli.main(["approval", "show", "--project", str(tmp_path), "--id", "APR-NOPE"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "not found" in out


def test_cli_stats_counts_by_status_and_target(tmp_path, capsys):
    _seed(tmp_path)
    cli.main(["approval", "approve", "--project", str(tmp_path),
              "--id", "APR-PUB-00001", "--by", "human"])
    capsys.readouterr()
    rc = cli.main(["approval", "stats", "--project", str(tmp_path), "--json"])
    out = capsys.readouterr().out
    assert rc == 0
    import json
    stats = json.loads(out)
    assert stats["total_requests"] == 2
    assert stats["by_status"] == {"approved": 1, "pending": 1}
    assert stats["by_target_type"] == {"mint": 1, "publish": 1}
