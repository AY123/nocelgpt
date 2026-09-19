"""
A.5 最小读者数据准备

创建真实读者数据导入模板和预测误差报告框架。

设计原则（P5.6 roadmap）：
- comparison_only = True（相对比较，不作为绝对分数）
- gating = False（永不阻断，ADR-003）
- calibrates = False（本阶段只对比，不校准模型）
- HONEST correspondence（只比较可比指标）

架构：
1. 数据导入模板：sources/reader-signals/*.yaml
2. 预测误差报告：比较 predicted vs real
3. 可视化：误差趋势、置信区间
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Dict
from datetime import datetime


@dataclass
class PredictionError:
    """单个指标的预测误差"""
    metric: str                 # retention_rate / drop_rate / reward_count
    predicted: float            # 预测值
    actual: float               # 真实值
    error: float                # 误差（actual - predicted）
    error_rate: Optional[float] # 误差率（error / actual）

    def to_dict(self) -> dict:
        return {
            "metric": self.metric,
            "predicted": self.predicted,
            "actual": self.actual,
            "error": self.error,
            "error_rate": self.error_rate
        }


@dataclass
class ChapterPredictionReport:
    """单章预测误差报告"""
    chapter_id: str
    chapter_index: Optional[int]
    collected_at: str            # 数据收集时间
    confidence: str              # low / medium / high
    source: str                  # 数据来源平台

    predicted_at: Optional[str] = None  # 预测时间（可能没有预测）

    errors: List[PredictionError] = field(default_factory=list)

    # 统计
    mean_absolute_error: Optional[float] = None
    mean_error_rate: Optional[float] = None

    def calculate_statistics(self):
        """计算统计量"""
        if not self.errors:
            return

        # 平均绝对误差
        abs_errors = [abs(e.error) for e in self.errors]
        self.mean_absolute_error = sum(abs_errors) / len(abs_errors)

        # 平均误差率
        error_rates = [e.error_rate for e in self.errors if e.error_rate is not None]
        if error_rates:
            self.mean_error_rate = sum(error_rates) / len(error_rates)

    def to_dict(self) -> dict:
        return {
            "chapter_id": self.chapter_id,
            "chapter_index": self.chapter_index,
            "predicted_at": self.predicted_at,
            "collected_at": self.collected_at,
            "confidence": self.confidence,
            "source": self.source,
            "errors": [e.to_dict() for e in self.errors],
            "mean_absolute_error": self.mean_absolute_error,
            "mean_error_rate": self.mean_error_rate
        }


@dataclass
class PredictionErrorReport:
    """预测误差总报告"""
    project_id: str
    generated_at: str

    chapters: List[ChapterPredictionReport] = field(default_factory=list)

    # 全局统计
    total_chapters: int = 0
    chapters_with_signals: int = 0

    # 误差汇总（按指标）
    metric_errors: Dict[str, Dict] = field(default_factory=dict)

    # 置信度分布
    confidence_distribution: Dict[str, int] = field(default_factory=dict)

    def calculate_global_statistics(self):
        """计算全局统计"""
        self.total_chapters = len(self.chapters)
        self.chapters_with_signals = len([c for c in self.chapters if c.errors])

        # 按指标汇总误差
        metric_data = {}
        for chapter in self.chapters:
            for error in chapter.errors:
                if error.metric not in metric_data:
                    metric_data[error.metric] = {
                        "errors": [],
                        "error_rates": []
                    }
                metric_data[error.metric]["errors"].append(error.error)
                if error.error_rate is not None:
                    metric_data[error.metric]["error_rates"].append(error.error_rate)

        # 计算每个指标的统计量
        for metric, data in metric_data.items():
            errors = data["errors"]
            error_rates = data["error_rates"]

            self.metric_errors[metric] = {
                "count": len(errors),
                "mean_error": sum(errors) / len(errors) if errors else 0,
                "mean_absolute_error": sum(abs(e) for e in errors) / len(errors) if errors else 0,
                "mean_error_rate": sum(error_rates) / len(error_rates) if error_rates else None,
                "max_error": max(errors) if errors else 0,
                "min_error": min(errors) if errors else 0
            }

        # 置信度分布
        self.confidence_distribution = {}
        for chapter in self.chapters:
            conf = chapter.confidence
            self.confidence_distribution[conf] = self.confidence_distribution.get(conf, 0) + 1

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "generated_at": self.generated_at,
            "total_chapters": self.total_chapters,
            "chapters_with_signals": self.chapters_with_signals,
            "chapters": [c.to_dict() for c in self.chapters],
            "metric_errors": self.metric_errors,
            "confidence_distribution": self.confidence_distribution
        }


def build_prediction_error_report(
    project_id: str,
    chapter_reports: List[ChapterPredictionReport]
) -> PredictionErrorReport:
    """
    构建预测误差总报告

    Args:
        project_id: 项目 ID
        chapter_reports: 章节报告列表

    Returns:
        PredictionErrorReport
    """
    report = PredictionErrorReport(
        project_id=project_id,
        generated_at=datetime.now().isoformat(),
        chapters=chapter_reports
    )

    # 计算每章的统计量
    for chapter in report.chapters:
        chapter.calculate_statistics()

    # 计算全局统计
    report.calculate_global_statistics()

    return report


def compare_predicted_vs_actual(
    predicted: Optional[Dict],
    actual: Dict,
    chapter_id: str,
    chapter_index: Optional[int] = None
) -> ChapterPredictionReport:
    """
    比较预测值与实际值

    Args:
        predicted: 预测的 reader_simulation（可能为 None）
        actual: 真实的 reader_signal
        chapter_id: 章节 ID
        chapter_index: 章节索引

    Returns:
        ChapterPredictionReport
    """
    report = ChapterPredictionReport(
        chapter_id=chapter_id,
        chapter_index=chapter_index,
        collected_at=actual.get("collected_at", ""),
        confidence=actual.get("confidence", {}).get("level", "unknown"),
        source=actual.get("source", "unknown")
    )

    if predicted is None:
        # 没有预测值，只记录真实值
        return report

    # 提取预测时间
    report.predicted_at = predicted.get("simulated_at")

    # 比较可比指标
    actual_metrics = actual.get("metrics", {})
    predicted_aggregate = predicted.get("aggregate", {})

    # 1. retention_rate ↔ continue_rate
    if "retention_rate" in actual_metrics and "continue_rate" in predicted_aggregate:
        actual_val = actual_metrics["retention_rate"]
        pred_val = predicted_aggregate["continue_rate"] * 100  # 转为百分比

        error = actual_val - pred_val
        error_rate = (error / actual_val * 100) if actual_val != 0 else None

        report.errors.append(PredictionError(
            metric="retention_rate",
            predicted=pred_val,
            actual=actual_val,
            error=error,
            error_rate=error_rate
        ))

    # 2. drop_rate（如果有）
    if "drop_rate" in actual_metrics and "dropout_risk" in predicted_aggregate:
        actual_val = actual_metrics["drop_rate"]
        pred_val = predicted_aggregate["dropout_risk"] * 100  # 转为百分比

        error = actual_val - pred_val
        error_rate = (error / actual_val * 100) if actual_val != 0 else None

        report.errors.append(PredictionError(
            metric="drop_rate",
            predicted=pred_val,
            actual=actual_val,
            error=error,
            error_rate=error_rate
        ))

    # 3. reward_count（如果有）
    if "reward_count" in actual_metrics:
        actual_val = actual_metrics["reward_count"]

        # 预测中可能有 pay_interest 或其他指标
        pred_val = predicted_aggregate.get("pay_interest", 0) * 100  # 转为百分比

        # 对于计数类指标，误差率不太适用
        error = actual_val - pred_val

        report.errors.append(PredictionError(
            metric="reward_count",
            predicted=pred_val,
            actual=actual_val,
            error=error,
            error_rate=None  # 计数类不计算误差率
        ))

    return report


def generate_reader_signal_template(
    chapter_id: str = "TASK-00001",
    source: str = "起点中文网",
    confidence_level: str = "medium"
) -> Dict:
    """
    生成读者信号导入模板

    Args:
        chapter_id: 章节 ID
        source: 数据来源平台
        confidence_level: 置信度级别

    Returns:
        符合 reader-signal.schema.json 的模板
    """
    return {
        "kind": "reader_signal",
        "version": "1.0",
        "scope": "chapter",
        "chapter_id": chapter_id,
        "source": source,
        "collected_at": datetime.now().isoformat(),
        "metrics": {
            "subscription_count": 0,        # TODO: 填入真实订阅数
            "first_day_subscriptions": 0,   # TODO: 填入首订数
            "retention_rate": 0.0,          # TODO: 填入追读率（%）
            "drop_rate": 0.0,               # TODO: 填入掉粉率（%）
            "reward_count": 0,              # TODO: 填入打赏数
            "monthly_votes": 0,             # TODO: 填入月票数
            "collection_count": 0           # TODO: 填入收藏数
        },
        "confidence": {
            "level": confidence_level,      # low / medium / high
            "sample_size": 0,               # TODO: 填入样本数
            "is_estimated": False           # TODO: 是否估算值
        },
        "provenance": {
            "note": "手动导入的真实数据",
            "imported_by": "operator"       # TODO: 填入操作员名称
        }
    }
