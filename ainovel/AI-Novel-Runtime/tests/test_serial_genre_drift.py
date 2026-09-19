"""test_serial_genre_drift.py — cross-chapter genre-drift check (§4.3 退化梯度).

Pins the invariants of the fourth cross-chapter twin: it folds per-chapter
genre-discriminant-marker density into a TREND read (first third vs last third),
flags genre-less chapters and a never-established genre, stays EVALUATIVE and
never gates (ADR-003), and degrades cleanly on unknown genre / too few chapters.

The defect it exists to catch: the model's prior leans 玄幻, so an unconstrained
run drifts toward generic 升级流 — chapter 30 reads less like its declared
subgenre than chapter 3. Every single-chapter detector is blind to it because a
uniformly drifted book looks locally fine in every chapter.

Deterministic — no live model needed.
"""
from __future__ import annotations

import pytest

from runtime.execution.draft_review import AXIS_EVALUATIVE
from runtime.scene import check_serial_genre_drift, marker_density
from runtime.scene.serial_genre_drift import (GENRELESS_FLOOR,
                                              MIN_CHAPTER_CHARS,
                                              SERIAL_GENRE_DRIFT_REVIEWER_ID,
                                              TREND_MIN_CHAPTERS)

# Marker-dense 玄幻 prose vs marker-free generic prose. Both are padded well past
# MIN_CHAPTER_CHARS so neither is excluded as a stub.
_XUANHUAN = "他运转灵气冲击境界，宗门长老递来一枚丹药，修为再涨。" * 30
_GENERIC = "他握紧拳头一步踏出，对面的人脸色变了，最后他赢下这一场。" * 30


def _severities(report) -> list[str]:
    return [f.severity for f in report.findings]


def _messages(report) -> str:
    return " ".join(f.message for f in report.findings)


# --------------------------------------------------------------------------- #
# Discipline invariants                                                        #
# --------------------------------------------------------------------------- #
def test_report_is_evaluative_and_never_gates():
    report = check_serial_genre_drift([_XUANHUAN] * 9, "玄幻")
    assert report.axis == AXIS_EVALUATIVE
    assert report.gating is False
    assert report.reviewer == SERIAL_GENRE_DRIFT_REVIEWER_ID
    assert report.to_dict()["gating"] is False


def test_deterministic_same_input_same_findings():
    bodies = [_XUANHUAN] * 4 + [_GENERIC] * 5
    a = check_serial_genre_drift(bodies, "玄幻").to_dict()
    b = check_serial_genre_drift(bodies, "玄幻").to_dict()
    assert a == b


# --------------------------------------------------------------------------- #
# The drift signature                                                          #
# --------------------------------------------------------------------------- #
def test_drifting_book_warns():
    """Markers in the first third, gone by the last — the §4.3 signature."""
    bodies = [_XUANHUAN] * 3 + [_GENERIC] * 6
    report = check_serial_genre_drift(bodies, "玄幻")
    assert "warning" in _severities(report)
    assert "题材特征衰减" in _messages(report)


def test_stable_book_is_clean():
    report = check_serial_genre_drift([_XUANHUAN] * 9, "玄幻")
    assert _severities(report) == ["info"]
    assert "题材特征稳定" in _messages(report)


def test_rising_genre_density_is_not_a_drift_warning():
    """Drift is directional: growing INTO the genre must not warn."""
    bodies = [_GENERIC] * 3 + [_XUANHUAN] * 6
    report = check_serial_genre_drift(bodies, "玄幻")
    assert "题材特征衰减" not in _messages(report)


def test_genreless_chapters_are_named():
    bodies = [_XUANHUAN] * 6 + [_GENERIC] * 3
    report = check_serial_genre_drift(bodies, "玄幻")
    msg = _messages(report)
    assert "warning" in _severities(report)
    # The generic tail is chapters 7-9 (1-based), and they must be named.
    assert "第7章" in msg


def test_never_established_genre_reports_distinctly():
    """A book that never had the genre is a DIFFERENT defect from one that
    drifted away, so the message must distinguish them."""
    report = check_serial_genre_drift([_GENERIC] * 9, "玄幻")
    msg = _messages(report)
    assert "warning" in _severities(report)
    assert "自始未确立" in msg or "几乎不含" in msg
    assert "题材特征衰减" not in msg


# --------------------------------------------------------------------------- #
# Degrade paths — must never raise, never block                                #
# --------------------------------------------------------------------------- #
def test_unknown_genre_degrades_to_info():
    report = check_serial_genre_drift([_XUANHUAN] * 9, "完全没听过的类型XYZ")
    assert _severities(report) == ["info"]
    assert "无判别式词表" in _messages(report)


@pytest.mark.parametrize("genre", [None, "", "   "])
def test_missing_genre_degrades_to_info(genre):
    report = check_serial_genre_drift([_XUANHUAN] * 9, genre)
    assert _severities(report) == ["info"]
    assert report.gating is False


def test_too_few_chapters_degrades_to_info():
    report = check_serial_genre_drift([_XUANHUAN] * (TREND_MIN_CHAPTERS - 1), "玄幻")
    assert _severities(report) == ["info"]
    assert "不足" in _messages(report)


@pytest.mark.parametrize("bodies", [[], [""] * 9, None])
def test_empty_bodies_degrade_to_info(bodies):
    report = check_serial_genre_drift(bodies, "玄幻")
    assert _severities(report) == ["info"]
    assert report.gating is False


def test_short_stubs_are_excluded_from_the_series():
    """A 200-char stub's density swings on one word and would forge a fake
    trend, so stubs must not count toward the analyzable series."""
    stub = "他走了。"
    assert len(stub) < MIN_CHAPTER_CHARS
    report = check_serial_genre_drift([stub] * 9, "玄幻")
    assert "不足" in _messages(report)


# --------------------------------------------------------------------------- #
# marker_density                                                               #
# --------------------------------------------------------------------------- #
def test_marker_density_scales_per_1000_chars():
    body = "境界" * 10 + "啊" * 980   # 1000 chars, 10 marker hits
    assert marker_density(body, ["境界"]) == pytest.approx(10.0, abs=0.1)


def test_marker_density_empty_body_is_zero():
    assert marker_density("", ["境界"]) == 0.0
    assert marker_density(None, ["境界"]) == 0.0


def test_marker_density_no_markers_is_zero():
    assert marker_density(_GENERIC, ["境界", "灵气"]) == 0.0


def test_genreless_floor_is_below_real_marker_prose():
    """Guard the threshold's meaning: real genre prose must sit clearly above the
    floor, or the floor would fire on healthy chapters."""
    assert marker_density(_XUANHUAN, ["境界", "灵气", "宗门", "丹药", "修为"]) > GENRELESS_FLOOR


# --------------------------------------------------------------------------- #
# Subgenre markers                                                             #
# --------------------------------------------------------------------------- #
def test_detector_is_live_in_run_serial(tmp_path):
    """BUILT != LIVE guard. This project has repeatedly shipped a detector that
    was never called from a real production path, so importability proves nothing
    — drive the actual run_serial and assert the field is populated.

    Uses test_serial.py's own scaffold/outline helpers so the path exercised is
    the real one, not a hand-built stand-in.
    """
    from tests.test_serial import _scaffold_project, _run, _write_outline
    from runtime.outline.writer import load_project_outline

    _scaffold_project(tmp_path, n_events=3)
    _write_outline(tmp_path, [
        {"chapter_no": i, "goal": f"第{i}章目标", "reward_if_any": "实力突破"}
        for i in range(1, 4)
    ])
    outline = load_project_outline(tmp_path)
    assert outline is not None, "fixture outline must load, else the assert below is vacuous"
    outline["genre"] = ["玄幻"]

    result = _run(tmp_path, outline=outline)

    assert result.genre_drift is not None, (
        "genre_drift must be populated by run_serial — a detector that only "
        "exists in the module is the built-never-live defect this guards")
    assert result.genre_drift["gating"] is False
    assert result.genre_drift["reviewer"] == SERIAL_GENRE_DRIFT_REVIEWER_ID
    # It also has to survive the to_dict() the CLI/manifest consumes.
    assert "genre_drift" in result.to_dict()


def test_run_serial_unknown_genre_still_degrades_cleanly(tmp_path):
    """The live path with no genre must not raise and must not warn."""
    from tests.test_serial import _scaffold_project, _run

    _scaffold_project(tmp_path, n_events=3)
    result = _run(tmp_path)
    # No outline => no genre => either unset (too-few-bodies) or a clean info.
    if result.genre_drift is not None:
        assert result.genre_drift["gating"] is False
        assert all(f["severity"] == "info"
                   for f in result.genre_drift["findings"])


# --------------------------------------------------------------------------- #
# Authored markers — the primary instrument (validated on the real baseline)    #
# --------------------------------------------------------------------------- #
def test_authored_markers_take_priority_over_stock_table():
    """MEASURED regression. On the real 33ch baseline the stock 都市 table scored
    20 hits in ~177k chars and called 31/33 chapters genre-less, while the book's
    own coinages appeared ~1400 times with a rising density. A book's genre
    identity lives in ITS OWN vocabulary, so authored markers must win."""
    own = "他踏入梦墟，取出一枚梦晶，压住那道核心执念。" * 30
    # Contains zero stock 玄幻 words but heavy coinage use.
    report = check_serial_genre_drift(
        [own] * 9, "玄幻", authored_markers=["梦墟", "梦晶", "核心执念"])
    assert _severities(report) == ["info"]
    assert "作品自有术语" in _messages(report)
    # Without the authored markers the same prose looks genre-less.
    stock = check_serial_genre_drift([own] * 9, "玄幻")
    assert "warning" in _severities(stock)


def test_finding_names_which_vocabulary_was_measured():
    """A density number is unreadable unless the reader knows what was counted."""
    own = "他踏入梦墟，取出一枚梦晶。" * 40
    assert "作品自有术语" in _messages(
        check_serial_genre_drift([own] * 9, "玄幻", authored_markers=["梦墟", "梦晶"]))
    assert "通用词" in _messages(check_serial_genre_drift([_XUANHUAN] * 9, "玄幻"))


@pytest.mark.parametrize("empty", [None, [], ["", "  "]])
def test_empty_authored_markers_fall_back_to_stock(empty):
    report = check_serial_genre_drift([_XUANHUAN] * 9, "玄幻", authored_markers=empty)
    assert _severities(report) == ["info"]
    assert "通用词" in _messages(report)


def test_extract_authored_markers_from_real_shaped_sources():
    from runtime.genre_taxonomy import extract_authored_markers
    outline = {
        "world": {"summary": "现代都市之下隐藏着“梦墟”，一个混沌空间。",
                   "rules": ["每个梦境都有一颗“核心执念”"]},
        "core_hook": "他能通过破解梦中执念获取“梦晶”强化自身",
    }
    assert extract_authored_markers(outline) == ["梦墟", "核心执念", "梦晶"]


def test_extract_authored_markers_degrades_on_junk():
    from runtime.genre_taxonomy import extract_authored_markers
    assert extract_authored_markers() == []
    assert extract_authored_markers({}, None, "not a dict") == []
    assert extract_authored_markers({"world": {"summary": "没有任何引号术语"}}) == []


def test_extract_authored_markers_is_order_stable_and_deduped():
    from runtime.genre_taxonomy import extract_authored_markers
    # Terms must be >=2 chars: a single quoted character is almost always emphasis
    # or dialogue, not a coined term, and counting it would flood the density.
    src = {"core_hook": "“甲术”与“乙术”，再提“甲术”", "logline": "还有“丙术”"}
    assert extract_authored_markers(src) == ["甲术", "乙术", "丙术"]
    assert extract_authored_markers({"core_hook": "他说“好”"}) == []


# --------------------------------------------------------------------------- #
# drift vs never-established — the discriminator my first cut got wrong        #
# --------------------------------------------------------------------------- #
def test_strong_opening_then_fade_is_drift_not_never_established():
    """The bug this pins: a low median alone made a textbook drift case report as
    '自始未确立', which both mislabels it and suppresses the trend finding. LEVEL
    must also require the OPENING third to be weak."""
    report = check_serial_genre_drift([_XUANHUAN] * 3 + [_GENERIC] * 6, "玄幻")
    msg = _messages(report)
    assert "题材特征衰减" in msg
    assert "自始未确立" not in msg


def test_weak_from_the_start_is_never_established_not_drift():
    report = check_serial_genre_drift([_GENERIC] * 9, "玄幻")
    msg = _messages(report)
    assert "自始未确立" in msg
    assert "题材特征衰减" not in msg


def test_never_established_does_not_also_list_every_chapter():
    """The false-positive mode: 31/33 chapters individually accused. When the book
    never had the vocabulary, say that ONCE — don't name every chapter."""
    report = check_serial_genre_drift([_GENERIC] * 33, "玄幻")
    assert len(report.findings) == 1
    assert "第1章" not in _messages(report)


def test_outliers_are_relative_to_the_books_own_median():
    """With book-specific markers the absolute scale is meaningless (the real
    baseline ran 1.6–9.6/千字 on coinages vs 0.0–1.1 on stock words), so outliers
    are judged against the book's own median."""
    # Both padded past MIN_CHAPTER_CHARS or they get excluded as stubs.
    dense = "他踏入梦墟，取出梦晶。" * 60
    sparse = "他走在长街上，什么也没有发生，只是走着。" * 40   # no markers
    report = check_serial_genre_drift(
        [dense] * 8 + [sparse], "玄幻", authored_markers=["梦墟", "梦晶"])
    msg = _messages(report)
    assert "第9章" in msg
    assert "中位" in msg


def test_subgenre_markers_distinguish_from_degradation_target():
    """高武世界's markers are the social-recognition words, NOT 突破/修炼 which
    generic 玄幻 shares — otherwise density stays flat while the prose drifts and
    the detector is blind to the one thing it exists to catch."""
    # Both padded past MIN_CHAPTER_CHARS so neither is excluded as a stub.
    gaowu = "他在武者协会完成段位测评，评级提升后编制随之调整。" * 30
    generic_xuanhuan = "他突破修炼多年的瓶颈，体内力量奔涌不息。" * 30
    report = check_serial_genre_drift(
        [gaowu] * 3 + [generic_xuanhuan] * 6, "高武世界")
    assert "题材特征衰减" in _messages(report)
