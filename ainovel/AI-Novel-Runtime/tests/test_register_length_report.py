from __future__ import annotations

from runtime.serialize.register_length_report import (
    measure_register, measure_length, build_register_length_report,
)


def test_measure_register_clean_chinese_body():
    reg = measure_register("周洛铭推开门，走进了空无一人的病房。")
    assert reg["clean"] is True
    assert reg["latin_blocks"] == 0
    assert reg["latin_ratio"] == 0.0
    assert reg["cjk_chars"] > 0


def test_measure_register_flags_latin_leak():
    reg = measure_register("他打开了 system 面板，屏幕亮起。")
    assert reg["clean"] is False
    assert reg["latin_blocks"] == 1
    assert reg["latin_ratio"] > 0.0


def test_measure_length_in_band_uses_role_band():
    # opening band is 0.8–1.6 of target; 3000·0.8=2400, ·1.6=4800
    body = "字" * 3000
    m = measure_length(body, target=3000, role="opening")
    assert m["in_band"] is True
    assert m["band_low_chars"] == 2400 and m["band_high_chars"] == 4800

    short = "字" * 1000
    ms = measure_length(short, target=3000, role="opening")
    assert ms["below_band"] is True and ms["in_band"] is False


def test_build_report_folds_register_length_gate():
    chapters = [
        {"index": 1, "task_id": "TASK-00001", "role": "opening",
         "integrity_status": "pass", "body": "字" * 3000},
        {"index": 2, "task_id": "TASK-00002", "role": "advance",
         "integrity_status": "pass", "body": "字" * 2500},
        {"index": 3, "task_id": "TASK-00003", "role": "advance",
         "integrity_status": "review_required",
         "body": "字" * 2000 + " system overflow"},
    ]
    rep = build_register_length_report(
        baseline_id="LBR-TEST", chapters=chapters, target_wordcount=3000)

    assert rep["chapter_count"] == 3
    # register: ch1/ch2 clean, ch3 has a latin leak
    assert rep["register_summary"]["clean_chapters"] == 2
    assert rep["register_summary"]["total_latin_blocks"] == 2  # "system","overflow"
    # length: all three within their role bands
    assert rep["length_summary"]["in_band_rate"] == 1.0
    assert rep["length_summary"]["stdev_chars"] >= 0.0
    # gate: 2 of 3 pass
    assert rep["gate_summary"]["integrity_pass"] == 2
    assert rep["gating"] is False


def test_build_report_length_spread_converges():
    # tight spread => low stdev (收敛 signal the report exists to show)
    chapters = [{"index": i, "task_id": f"TASK-{i:05d}", "role": "advance",
                 "integrity_status": "pass", "body": "字" * (2900 + i * 20)}
                for i in range(1, 4)]
    rep = build_register_length_report(
        baseline_id="LBR-TIGHT", chapters=chapters, target_wordcount=3000)
    assert rep["length_summary"]["stdev_chars"] < 50
