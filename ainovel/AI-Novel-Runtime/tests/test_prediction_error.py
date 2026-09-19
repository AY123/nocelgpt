"""
测试 A.5 最小读者数据准备
"""
import pytest
from runtime.signals.prediction_error import (
    PredictionError,
    ChapterPredictionReport,
    PredictionErrorReport,
    compare_predicted_vs_actual,
    build_prediction_error_report,
    generate_reader_signal_template,
)


def test_prediction_error_creation():
    """测试：创建预测误差"""
    error = PredictionError(
        metric="retention_rate",
        predicted=75.0,
        actual=80.0,
        error=5.0,
        error_rate=6.25
    )

    assert error.metric == "retention_rate"
    assert error.predicted == 75.0
    assert error.actual == 80.0
    assert error.error == 5.0
    assert error.error_rate == 6.25


def test_chapter_report_statistics():
    """测试：章节报告统计量计算"""
    report = ChapterPredictionReport(
        chapter_id="TASK-00001",
        chapter_index=1,
        collected_at="2026-08-20T10:00:00",
        confidence="high",
        source="起点"
    )

    report.errors.append(PredictionError("retention_rate", 75.0, 80.0, 5.0, 6.25))
    report.errors.append(PredictionError("drop_rate", 10.0, 8.0, -2.0, -25.0))

    report.calculate_statistics()

    # 平均绝对误差 = (5.0 + 2.0) / 2 = 3.5
    assert report.mean_absolute_error == 3.5

    # 平均误差率 = (6.25 + (-25.0)) / 2 = -9.375
    assert report.mean_error_rate == -9.375


def test_compare_no_prediction():
    """测试：没有预测值时的对比"""
    actual = {
        "chapter_id": "TASK-00001",
        "collected_at": "2026-08-20T10:00:00",
        "source": "起点",
        "confidence": {"level": "high"},
        "metrics": {
            "retention_rate": 80.0,
            "drop_rate": 5.0
        }
    }

    report = compare_predicted_vs_actual(
        predicted=None,
        actual=actual,
        chapter_id="TASK-00001",
        chapter_index=1
    )

    assert report.chapter_id == "TASK-00001"
    assert len(report.errors) == 0  # 没有预测值，无误差
    assert report.confidence == "high"
    assert report.source == "起点"


def test_compare_with_prediction():
    """测试：有预测值时的对比"""
    predicted = {
        "simulated_at": "2026-08-19T10:00:00",
        "aggregate": {
            "continue_rate": 0.75,  # 75%
            "dropout_risk": 0.10    # 10%
        }
    }

    actual = {
        "chapter_id": "TASK-00001",
        "collected_at": "2026-08-20T10:00:00",
        "source": "起点",
        "confidence": {"level": "medium"},
        "metrics": {
            "retention_rate": 80.0,  # 实际 80%
            "drop_rate": 8.0         # 实际 8%
        }
    }

    report = compare_predicted_vs_actual(
        predicted=predicted,
        actual=actual,
        chapter_id="TASK-00001",
        chapter_index=1
    )

    assert len(report.errors) == 2

    # 检查 retention_rate 误差
    retention_error = [e for e in report.errors if e.metric == "retention_rate"][0]
    assert retention_error.predicted == 75.0  # continue_rate * 100
    assert retention_error.actual == 80.0
    assert retention_error.error == 5.0  # 80 - 75

    # 检查 drop_rate 误差
    drop_error = [e for e in report.errors if e.metric == "drop_rate"][0]
    assert drop_error.predicted == 10.0  # dropout_risk * 100
    assert drop_error.actual == 8.0
    assert drop_error.error == -2.0  # 8 - 10


def test_global_report_statistics():
    """测试：全局报告统计量"""
    ch1 = ChapterPredictionReport(
        chapter_id="TASK-00001",
        chapter_index=1,
        collected_at="2026-08-20T10:00:00",
        confidence="high",
        source="起点"
    )
    ch1.errors.append(PredictionError("retention_rate", 75.0, 80.0, 5.0, 6.25))

    ch2 = ChapterPredictionReport(
        chapter_id="TASK-00002",
        chapter_index=2,
        collected_at="2026-08-20T11:00:00",
        confidence="medium",
        source="起点"
    )
    ch2.errors.append(PredictionError("retention_rate", 70.0, 75.0, 5.0, 6.67))

    report = build_prediction_error_report("novel-test", [ch1, ch2])

    assert report.total_chapters == 2
    assert report.chapters_with_signals == 2

    # 检查指标误差汇总
    assert "retention_rate" in report.metric_errors
    retention_stats = report.metric_errors["retention_rate"]
    assert retention_stats["count"] == 2
    assert retention_stats["mean_error"] == 5.0  # (5.0 + 5.0) / 2
    assert retention_stats["mean_absolute_error"] == 5.0

    # 检查置信度分布
    assert report.confidence_distribution["high"] == 1
    assert report.confidence_distribution["medium"] == 1


def test_generate_template():
    """测试：生成读者信号模板"""
    template = generate_reader_signal_template(
        chapter_id="TASK-00001",
        source="起点中文网",
        confidence_level="high"
    )

    assert template["kind"] == "reader_signal"
    assert template["version"] == "1.0"
    assert template["scope"] == "chapter"
    assert template["chapter_id"] == "TASK-00001"
    assert template["source"] == "起点中文网"
    assert "collected_at" in template
    assert "metrics" in template
    assert "confidence" in template
    assert template["confidence"]["level"] == "high"


def test_report_to_dict():
    """测试：报告序列化"""
    ch1 = ChapterPredictionReport(
        chapter_id="TASK-00001",
        chapter_index=1,
        collected_at="2026-08-20T10:00:00",
        confidence="high",
        source="起点"
    )
    ch1.errors.append(PredictionError("retention_rate", 75.0, 80.0, 5.0, 6.25))

    report = build_prediction_error_report("novel-test", [ch1])
    report_dict = report.to_dict()

    assert isinstance(report_dict, dict)
    assert "project_id" in report_dict
    assert "generated_at" in report_dict
    assert "chapters" in report_dict
    assert "metric_errors" in report_dict
    assert "confidence_distribution" in report_dict
    assert len(report_dict["chapters"]) == 1


def test_error_rate_calculation():
    """测试：误差率计算"""
    # 正误差
    error1 = PredictionError("retention_rate", 75.0, 80.0, 5.0, 6.25)
    assert error1.error_rate == 6.25  # (5.0 / 80.0) * 100

    # 负误差
    error2 = PredictionError("drop_rate", 10.0, 8.0, -2.0, -25.0)
    assert error2.error_rate == -25.0  # (-2.0 / 8.0) * 100


def test_no_errors_statistics():
    """测试：没有误差时的统计量"""
    report = ChapterPredictionReport(
        chapter_id="TASK-00001",
        chapter_index=1,
        collected_at="2026-08-20T10:00:00",
        confidence="high",
        source="起点"
    )

    report.calculate_statistics()

    assert report.mean_absolute_error is None
    assert report.mean_error_rate is None
