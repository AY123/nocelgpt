"""test_golden_three_contract.py — generation-side 黄金三章 contract (规范 §7).

The gap this closes: the commercial funnel is
点击 × 前三章留存 × 免费追读 × 付费转化 × 长期稳定, and this project had ~30 modules
for the last two terms but NOTHING on the generation side for 前三章留存. There was
no `chapter_no <= 3` branch anywhere in generation — chapter 1 and chapter 17 were
written under identical instructions despite having different commercial jobs.
`serialize/golden_three.py` only PACKAGES produced chapters for review.

Pins:
  - each of ch1/ch2/ch3 gets its OWN contract, reaching the real prompt;
  - ch4+ gets nothing, so the long-serial path stays byte-identical;
  - the contract text carries NO 章号 token — it must not itself trip the v13
    anti-meta-leak rule if the model echoes it;
  - it shapes generation and gates nothing (ADR-003).
"""
from __future__ import annotations

import re

import pytest

from runtime.execution.meta_reference import check_meta_reference
from runtime.golden_three_contract import (OPENING_HOOK_CHARS,
                                           golden_three_directive,
                                           is_golden_three)

_CHAPTER_NO_RE = re.compile(r"第 ?[0-9一二三四五六七八九十]+ ?章")


# --------------------------------------------------------------------------- #
# The directive itself                                                         #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("chapter_no", [1, 2, 3])
def test_first_three_chapters_each_get_a_distinct_contract(chapter_no):
    d = golden_three_directive(chapter_no)
    assert d and "黄金三章" in d
    assert is_golden_three(chapter_no)


def test_the_three_contracts_are_all_different():
    """Same instructions for all three would defeat the point — their commercial
    jobs differ (hold / prove the mechanism / show the payoff)."""
    got = {golden_three_directive(n) for n in (1, 2, 3)}
    assert len(got) == 3


def test_chapter_one_carries_the_300_char_rule():
    """§7's highest-leverage rule: a reader not held by the opening never reaches
    anything else this project builds."""
    d = golden_three_directive(1)
    assert str(OPENING_HOOK_CHARS) in d
    assert "旧生活无法继续" in d


def test_chapter_two_requires_benefit_and_cost_together():
    d = golden_three_directive(2)
    assert "代价" in d and "机会并不免费" in d


def test_chapter_three_forbids_winning_by_coincidence():
    d = golden_three_directive(3)
    assert "巧合" in d
    assert "前十章" in d


@pytest.mark.parametrize("chapter_no", [4, 5, 17, 100, 0, -1])
def test_chapters_outside_the_first_three_get_nothing(chapter_no):
    """The load-bearing non-breaking invariant: "" => nothing appended => the whole
    long-serial path renders byte-identically to before this module existed."""
    assert golden_three_directive(chapter_no) == ""
    assert not is_golden_three(chapter_no)


@pytest.mark.parametrize("junk", [None, True, False, "1", 3.0, [1]])
def test_non_int_input_degrades_and_never_raises(junk):
    """bool is rejected explicitly: True == 1 in Python and would otherwise
    silently render the chapter-1 contract."""
    assert golden_three_directive(junk) == ""


# --------------------------------------------------------------------------- #
# It must not fight the v13 anti-meta-leak rule                                #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("chapter_no", [1, 2, 3])
def test_contract_text_contains_no_chapter_number_token(chapter_no):
    """A real defect found while wiring this: the first draft said 「打开第 2 章」,
    and v13 forbids chapter numbers in the body. An instruction the model may copy
    verbatim must not itself contain what the body is forbidden to contain."""
    assert not _CHAPTER_NO_RE.search(golden_three_directive(chapter_no))


@pytest.mark.parametrize("chapter_no", [1, 2, 3])
def test_echoing_the_contract_does_not_trip_meta_reference(chapter_no):
    report = check_meta_reference({"body": golden_three_directive(chapter_no)}).to_dict()
    assert all(f["severity"] == "info" for f in report["findings"]), report["findings"]


# --------------------------------------------------------------------------- #
# BUILT != LIVE — proven by spying on what the model actually receives          #
# --------------------------------------------------------------------------- #
def test_contract_reaches_the_real_prompt_per_chapter(tmp_path):
    """Spy on the model to read the ACTUAL prompt string.

    Asserting the text appears in the persisted draft would be weak evidence: the
    DeterministicModel echoes its prompt into the body, so a body hit does not by
    itself prove the prompt carried it for the right reason. Capturing the prompt
    at the model boundary is direct.
    """
    from tests.test_serial import _scaffold_project, _run, _write_outline
    from runtime.outline.writer import load_project_outline
    from runtime.execution.model import DeterministicModel

    seen: list[str] = []

    class Spy(DeterministicModel):
        model_id = "spy-golden-three"

        def generate(self, prompt):
            seen.append(prompt)
            return super().generate(prompt)

    _scaffold_project(tmp_path, n_events=4)
    _write_outline(tmp_path, [{"chapter_no": i, "goal": f"第{i}章目标"}
                              for i in (1, 2, 3, 4)])
    result = _run(tmp_path, outline=load_project_outline(tmp_path),
                  prompt_version="10.0.0", model=Spy())

    assert result.produced == 4 and len(seen) == 4
    assert "开篇章（建立）" in seen[0]
    assert f"前 {OPENING_HOOK_CHARS} 字内" in seen[0]
    assert "验证章" in seen[1]
    assert "兑现章" in seen[2]
    # ch4 must be untouched — no golden-three text at all.
    assert "黄金三章" not in seen[3]


def test_chapter_four_prompt_is_unchanged_by_this_feature(tmp_path):
    """Byte-identity for the long-serial path, at the prompt level."""
    from tests.test_serial import _scaffold_project, _run, _write_outline
    from runtime.outline.writer import load_project_outline
    from runtime.execution.model import DeterministicModel
    from runtime.golden_three_contract import _CONTRACTS

    def prompts_for(patch: bool) -> list[str]:
        seen: list[str] = []

        class Spy(DeterministicModel):
            model_id = "spy-g3-ab"

            def generate(self, prompt):
                seen.append(prompt)
                return super().generate(prompt)

        root = tmp_path / ("on" if patch else "off")
        root.mkdir()
        _scaffold_project(root, n_events=4)
        _write_outline(root, [{"chapter_no": i, "goal": f"第{i}章目标"}
                              for i in (1, 2, 3, 4)])
        _run(root, outline=load_project_outline(root),
             prompt_version="10.0.0", model=Spy())
        return seen

    with_feature = prompts_for(True)
    saved = dict(_CONTRACTS)
    try:
        _CONTRACTS.clear()          # simulate the pre-feature world
        without_feature = prompts_for(False)
    finally:
        _CONTRACTS.update(saved)

    # ch4 (index 3) must match exactly; ch1-3 must differ.
    assert with_feature[3] == without_feature[3]
    for i in (0, 1, 2):
        assert with_feature[i] != without_feature[i]


def test_execute_package_accepts_chapter_no_and_defaults_to_none():
    """Other callers (cli.py / refine.py) pass nothing, so the default must be
    None => no contract => their behavior is unchanged."""
    import inspect
    from runtime.execution.run import execute_package
    sig = inspect.signature(execute_package)
    assert sig.parameters["chapter_no"].default is None
