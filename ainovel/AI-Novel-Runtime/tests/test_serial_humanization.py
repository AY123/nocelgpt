from __future__ import annotations

from runtime.scene import check_serial_openings
from runtime.scene.serial_humanization import (
    _opening_prefix,
    _longest_repeat_run,
    _largest_cluster,
)


def _findings(report):
    return report.to_dict()["findings"]


def _warnings(report):
    return [f for f in _findings(report) if f["severity"] == "warning"]


def _infos(report):
    return [f for f in _findings(report) if f["severity"] == "info"]


def test_opening_prefix_skips_heading_and_takes_first_sentence():
    body = "# 第一章 余梦\n\n周洛铭睁开眼的时候，天花板上那道裂缝还在。\n\n和昨天一样。"
    # heading skipped, first PROSE sentence's leading 6 chars, whitespace removed
    assert _opening_prefix(body) == "周洛铭睁开眼"


def test_opening_prefix_empty_body():
    assert _opening_prefix("") == ""
    assert _opening_prefix("# 只有标题\n\n") == ""


def test_the_real_baseline_pattern_is_flagged():
    """RUN-00018: three consecutive chapters opening with 周洛铭睁开眼 — the exact
    cross-chapter tell the single-chapter detector could not see."""
    bodies = [
        "# 第一章 余梦\n\n周洛铭睁开眼的时候，天花板上那道裂缝还在。",
        "# 第二章 潜梦\n\n周洛铭睁开眼，看见一片灰雾。",
        "# 第3章\n\n周洛铭睁开眼时，林墨渊正站在他面前三步之外。",
    ]
    report = check_serial_openings(bodies)
    warns = _warnings(report)
    assert warns, "expected a warning for 3x repeated opening"
    assert "周洛铭睁开眼" in warns[0]["message"]
    assert report.to_dict()["gating"] is False
    assert report.to_dict()["axis"] == "evaluative"


def test_diverse_openings_pass_clean():
    bodies = [
        "# 一\n\n周洛铭睁开眼，天花板裂缝还在。",
        "# 二\n\n“你终于来了。”林墨渊靠在门框上。",
        "# 三\n\n雨下了整整一夜，梦墟的边界开始崩塌。",
    ]
    report = check_serial_openings(bodies)
    assert _warnings(report) == []
    infos = [f for f in _findings(report) if f["severity"] == "info"]
    assert any("开篇多样" in f["message"] for f in infos)


def test_too_few_chapters_degrades_to_info():
    report = check_serial_openings(["# 一\n\n只有一章的正文。"])
    findings = _findings(report)
    assert len(findings) == 1
    assert findings[0]["severity"] == "info"


def test_scattered_cluster_flagged_even_when_not_consecutive():
    # same opening on ch1, ch3, ch5 (not a consecutive run) still reads templated
    bodies = [
        "# 1\n\n周洛铭睁开眼，第一次。",
        "# 2\n\n林墨渊冷笑一声。",
        "# 3\n\n周洛铭睁开眼，第二次。",
        "# 4\n\n雨停了。",
        "# 5\n\n周洛铭睁开眼，第三次。",
    ]
    report = check_serial_openings(bodies)
    warns = _warnings(report)
    assert warns
    assert "周洛铭睁开眼" in warns[0]["message"]


def test_consecutive_run_not_double_reported_as_cluster():
    # 3 consecutive identical openings: should produce exactly ONE warning
    # (the run), not also a duplicate cluster warning for the same prefix.
    bodies = [
        "# 1\n\n周洛铭睁开眼，一。",
        "# 2\n\n周洛铭睁开眼，二。",
        "# 3\n\n周洛铭睁开眼，三。",
    ]
    report = check_serial_openings(bodies)
    assert len(_warnings(report)) == 1


def test_two_consecutive_openings_are_an_info_nudge_not_a_warning():
    """The near-miss the real v8 A/B arm exposed: ch3+ch4 both open "周洛铭睁开眼",
    2 consecutive — below the run-of-3 warning, but now surfaced at info so the
    detector's sensitivity matches the v9 prevention constraint."""
    bodies = [
        "# 1\n\n夜雨冲刷着铁皮屋顶。",
        "# 2\n\n凌晨三点，他坐在床边。",
        "# 3\n\n周洛铭睁开眼。",
        "# 4\n\n周洛铭睁开眼的时候，水渍还在。",
        "# 5\n\n他直到凌晨才回到出租屋。",
    ]
    report = check_serial_openings(bodies)
    assert _warnings(report) == []                      # not a warning
    nudges = [f for f in _infos(report) if "周洛铭睁开眼" in f["message"]]
    assert nudges, "expected an info nudge for the 2-consecutive near-miss"
    assert "换一种入场方式" in nudges[0]["message"]


def test_diverse_five_chapter_run_stays_clean():
    """The v9 arm shape: 5 distinct openings => no warning, no nudge, just the
    clean 'diverse' info note."""
    bodies = [
        "# 1\n\n旧城区下水道的铁腥味灌进鼻腔。",
        "# 2\n\n他的指尖还残留着粘稠的触感。",
        "# 3\n\n他坐在书桌前，盯着手机。",
        "# 4\n\n「出不来。」铁灰色舱壁合拢。",
        "# 5\n\n他没有等电梯。",
    ]
    report = check_serial_openings(bodies)
    assert _warnings(report) == []
    assert any("开篇多样" in f["message"] for f in _infos(report))


def test_longest_repeat_run_helper():
    assert _longest_repeat_run(["周洛铭睁开", "周洛铭睁开", "周洛铭睁开"]) == (3, "周洛铭睁开")
    assert _longest_repeat_run(["a", "b", "a"])[0] == 1
    assert _longest_repeat_run(["", "", ""])[0] == 1   # empty never forms a run


def test_largest_cluster_helper():
    n, pref = _largest_cluster(["x", "y", "x", "x", "z"])
    assert (n, pref) == (3, "x")
    assert _largest_cluster(["", ""]) == (0, "")


# --- prevention side: render_recent_openings -------------------------------

def test_render_recent_openings_lists_prior_chapters():
    from runtime.scene import render_recent_openings
    bodies = [
        "# 一\n\n周洛铭睁开眼，天花板裂缝还在。",
        "# 二\n\n周洛铭睁开眼，看见灰雾。",
    ]
    out = render_recent_openings(bodies)
    assert "周洛铭睁开眼" in out
    assert "必须与它们明显不同" in out
    # both prior openings surfaced
    assert out.count("近章开篇") == 2


def test_render_recent_openings_empty_is_a_stable_sentinel():
    from runtime.scene import render_recent_openings
    out = render_recent_openings([])
    assert out  # non-empty so the v9 slot always binds
    assert "开篇" in out


def test_render_recent_openings_windows_to_last_k():
    from runtime.scene import render_recent_openings
    bodies = [f"# 第{i}章\n\n开篇第{i}句，各不相同的入场。" for i in range(1, 8)]
    out = render_recent_openings(bodies, window=3)
    # only the last 3 openings appear
    assert out.count("近章开篇") == 3
    assert "开篇第7句" in out and "开篇第5句" in out
    assert "开篇第4句" not in out
