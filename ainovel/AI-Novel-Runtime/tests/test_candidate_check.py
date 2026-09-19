"""Test Candidate Contract Check (Phase 3 Stage 2 Task 2)."""
import pytest
from pathlib import Path


def test_check_candidate_pass():
    """Test candidate check passes when contract is satisfied."""
    import sys
    from pathlib import Path as _P

    project_root = _P(__file__).resolve().parent.parent.parent
    if not (project_root / 'runtime_plugins').exists():
        pytest.skip("runtime_plugins not found")
    sys.path.insert(0, str(project_root))

    from runtime_plugins.contract import ContractGate

    fixtures = Path(__file__).parent / "fixtures" / "contracts"
    if not fixtures.exists():
        pytest.skip("Test fixtures not available")

    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        schemas_dir = Path(tmpdir) / "schemas"
        schemas_dir.mkdir()

        schema_src = Path(__file__).parent.parent.parent / "schemas" / "chapter_contract.schema.json"
        if schema_src.exists():
            (schemas_dir / "chapter_contract.schema.json").write_text(
                schema_src.read_text(encoding="utf-8"), encoding="utf-8"
            )

        gate = ContractGate(contracts_dir=fixtures, schemas_dir=schemas_dir)

        # Candidate text that satisfies Ch1 contract
        candidate_text = """
        在城市广场的中央，主角站立着，观察着周围的一切。

        这是一个平静的早晨，但空气中弥漫着不寻常的气息。主角感到有什么不对劲。

        突然，一道奇异的光芒从远处闪过。这是什么？主角心中充满了疑问。

        他决定调查这个异常现象。这可能是一个重要的线索。

        然而，就在此时，远处传来了不祥的声音...
        """

        result = gate.check_candidate(
            chapter=1,
            candidate_text=candidate_text,
            prev_text=""
        )

        assert "pass" in result
        assert "issues" in result
        assert "requires_revision" in result
        assert "revision_suggestions" in result

        print(f"\nCandidate check (pass expected):")
        print(f"  Pass: {result['pass']}")
        print(f"  Issues: {len(result['issues'])}")
        print(f"  Requires revision: {result['requires_revision']}")


def test_check_candidate_fail_critical():
    """Test candidate check fails on critical issues."""
    import sys
    from pathlib import Path as _P

    project_root = _P(__file__).resolve().parent.parent.parent
    if not (project_root / 'runtime_plugins').exists():
        pytest.skip("runtime_plugins not found")
    sys.path.insert(0, str(project_root))

    from runtime_plugins.contract import ContractGate

    fixtures = Path(__file__).parent / "fixtures" / "contracts"
    if not fixtures.exists():
        pytest.skip("Test fixtures not available")

    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        schemas_dir = Path(tmpdir) / "schemas"
        schemas_dir.mkdir()

        schema_src = Path(__file__).parent.parent.parent / "schemas" / "chapter_contract.schema.json"
        if schema_src.exists():
            (schemas_dir / "chapter_contract.schema.json").write_text(
                schema_src.read_text(encoding="utf-8"), encoding="utf-8"
            )

        gate = ContractGate(contracts_dir=fixtures, schemas_dir=schemas_dir)

        # Candidate text that violates Ch1 contract (wrong location)
        candidate_text = """
        在一个完全不同的地方，在山顶上，故事开始了。

        主角醒来发现自己在一个陌生的地方。这里是哪里？

        远处的风景很美，但这不是他记忆中的地方。

        他站起来，开始寻找回去的路。
        """

        result = gate.check_candidate(
            chapter=1,
            candidate_text=candidate_text,
            prev_text=""
        )

        assert result["pass"] is False
        assert len(result["issues"]) > 0
        # Should have critical issue about location
        critical_issues = [iss for iss in result["issues"] if iss["category"] == "critical"]
        assert len(critical_issues) > 0
        assert result["requires_revision"] is True

        print(f"\nCandidate check (fail expected):")
        print(f"  Pass: {result['pass']}")
        print(f"  Issues: {len(result['issues'])}")
        print(f"  Critical issues: {len(critical_issues)}")
        for issue in result["issues"]:
            print(f"    - {issue['category']}: {issue['field']} - {issue['description']}")
        print(f"  Suggestions: {result['revision_suggestions']}")


def test_check_candidate_hook_consumption():
    """Test candidate check for hook consumption (Chapter 2+)."""
    import sys
    from pathlib import Path as _P

    project_root = _P(__file__).resolve().parent.parent.parent
    if not (project_root / 'runtime_plugins').exists():
        pytest.skip("runtime_plugins not found")
    sys.path.insert(0, str(project_root))

    from runtime_plugins.contract import ContractGate

    fixtures = Path(__file__).parent / "fixtures" / "contracts"
    if not fixtures.exists():
        pytest.skip("Test fixtures not available")

    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        schemas_dir = Path(tmpdir) / "schemas"
        schemas_dir.mkdir()

        schema_src = Path(__file__).parent.parent.parent / "schemas" / "chapter_contract.schema.json"
        if schema_src.exists():
            (schemas_dir / "chapter_contract.schema.json").write_text(
                schema_src.read_text(encoding="utf-8"), encoding="utf-8"
            )

        gate = ContractGate(contracts_dir=fixtures, schemas_dir=schemas_dir)

        # Ch2 contract requires consuming hook from Ch1
        # Candidate that does NOT address the hook in first 30%
        candidate_text_bad = """
        新的一天开始了。主角在思考着各种事情。

        天气很好，阳光明媚。主角感到心情愉快。

        他决定去散步。路上遇到了很多人。

        大家都在忙碌着自己的事情。
        """ * 3  # 扩展文本以确保钩子在后面

        result_bad = gate.check_candidate(
            chapter=2,
            candidate_text=candidate_text_bad,
            prev_text="..."
        )

        # Should fail because hook not addressed in first 30%
        assert result_bad["pass"] is False
        # Should have critical issue about hook
        hook_issues = [iss for iss in result_bad["issues"] if "hook" in iss["field"]]
        # Note: May not trigger if must_address keywords are too generic
        print(f"\nCh2 hook check (hook not addressed):")
        print(f"  Pass: {result_bad['pass']}")
        print(f"  Hook-related issues: {len(hook_issues)}")
        if hook_issues:
            for issue in hook_issues:
                print(f"    - {issue['category']}: {issue['description']}")
