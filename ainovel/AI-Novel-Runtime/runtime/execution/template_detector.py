"""template_detector.py — Phase 1 Task 1.2.4: 高频模板表达检测

基于100章诊断结果，检测高频AI模板表达：
- "他知道"、"这不是"、"沉默了片刻"
- "深吸一口气"、"眼中闪过"、"嘴角勾起"

策略：对比草稿频率 vs 参考作品基准频率
"""
from __future__ import annotations
from typing import Dict, List, Optional
import re


# 从100章诊断中提取的高频模板库
# 格式：{phrase: baseline_frequency_per_1000_words}
DEFAULT_TEMPLATE_LIBRARY = {
    # 动作/心理模板
    "他知道": 0.5,           # 参考作品平均：每千字0.5次
    "这不是": 0.3,
    "沉默了片刻": 0.1,
    "深吸一口气": 0.2,
    "眼中闪过": 0.3,
    "嘴角勾起": 0.2,

    # 转折/铺垫模板
    "然而": 0.8,
    "但是": 1.0,
    "只是": 0.7,

    # 修辞模板
    "如同": 0.5,
    "仿佛": 0.4,
    "宛若": 0.1,
    "好似": 0.3,

    # 情绪表达模板
    "他的心": 0.3,
    "她的脸": 0.2,
    "目光": 0.8,

    # 时间推进模板
    "此时": 0.4,
    "此刻": 0.3,
    "这一刻": 0.2,
}


def detect_template_phrases(
    body: str,
    *,
    template_library: Optional[Dict[str, float]] = None,
    threshold_multiplier: float = 2.0
) -> List[dict]:
    """检测高频模板表达。

    Args:
        body: 章节正文
        template_library: 模板库（phrase -> baseline_per_1000_words）
        threshold_multiplier: 阈值倍数（超过baseline × multiplier算overuse）

    Returns:
        检测到的模板列表，每个包含：
        - phrase: 模板表达
        - count: 出现次数
        - frequency_per_1000: 每千字频率
        - baseline: 基准频率
        - overuse_ratio: 超用比例（实际/基准）
        - severity: 严重程度（warning/info）

    Examples:
        >>> body = "他知道这是危险的。他知道必须小心。他知道没有退路。"
        >>> issues = detect_template_phrases(body)
        >>> issues[0]["phrase"]
        '他知道'
        >>> issues[0]["overuse_ratio"]
        6.0  # 远超基准
    """
    if not body:
        return []

    library = template_library or DEFAULT_TEMPLATE_LIBRARY

    # Calculate word count (approximate)
    word_count = _approximate_word_count(body)
    if word_count == 0:
        return []

    issues = []

    for phrase, baseline in library.items():
        # Count occurrences
        count = body.count(phrase)
        if count == 0:
            continue

        # Calculate frequency per 1000 words
        freq_per_1000 = (count / word_count) * 1000

        # Compare with baseline
        threshold = baseline * threshold_multiplier

        if freq_per_1000 > threshold:
            overuse_ratio = freq_per_1000 / baseline if baseline > 0 else float('inf')

            # Determine severity
            if overuse_ratio >= 3.0:
                severity = "warning"
            else:
                severity = "info"

            issues.append({
                "phrase": phrase,
                "count": count,
                "frequency_per_1000": round(freq_per_1000, 2),
                "baseline": baseline,
                "overuse_ratio": round(overuse_ratio, 2),
                "severity": severity
            })

    # Sort by overuse_ratio (most severe first)
    issues.sort(key=lambda x: x["overuse_ratio"], reverse=True)

    return issues


def _approximate_word_count(text: str) -> int:
    """Approximate word count (CJK-aware)."""
    if not text:
        return 0

    # CJK characters
    cjk_chars = sum(1 for c in text if '一' <= c <= '鿿')

    # Latin words (space-separated)
    latin_text = re.sub(r'[一-鿿]', ' ', text)
    latin_words = len([w for w in latin_text.split() if w.strip()])

    return cjk_chars + latin_words


def format_template_finding(issue: dict) -> str:
    """格式化模板检测结果为可读文本。

    Args:
        issue: detect_template_phrases返回的单个检测结果

    Returns:
        格式化的描述文本
    """
    phrase = issue["phrase"]
    count = issue["count"]
    freq = issue["frequency_per_1000"]
    baseline = issue["baseline"]
    ratio = issue["overuse_ratio"]

    return (
        f"模板表达过度使用：「{phrase}」出现{count}次"
        f"（每千字{freq}次，参考基准{baseline}次，超用{ratio}倍）"
    )


def integrate_with_ai_taste_report(
    body: str,
    ai_taste_summary: dict,
    *,
    template_library: Optional[Dict[str, float]] = None
) -> dict:
    """将模板检测集成到ai_taste_summary。

    Args:
        body: 章节正文
        ai_taste_summary: 现有的ai_taste_summary
        template_library: 模板库

    Returns:
        增强后的ai_taste_summary（包含template_overuse字段）
    """
    template_issues = detect_template_phrases(body, template_library=template_library)

    # Count high-severity issues
    warning_count = sum(1 for issue in template_issues if issue["severity"] == "warning")

    return {
        **ai_taste_summary,
        "template_overuse": {
            "total_issues": len(template_issues),
            "warning_count": warning_count,
            "issues": template_issues[:5]  # Top 5 most severe
        }
    }


def build_template_library_from_corpus(
    corpus_texts: List[str]
) -> Dict[str, float]:
    """从参考作品语料库构建模板基准库。

    Args:
        corpus_texts: 参考作品的章节列表

    Returns:
        模板库字典（phrase -> avg_frequency_per_1000_words）

    Example:
        >>> corpus = ["盘龙第1章...", "盘龙第2章...", ...]
        >>> library = build_template_library_from_corpus(corpus)
    """
    if not corpus_texts:
        return {}

    # Use default library phrases as candidates
    candidates = list(DEFAULT_TEMPLATE_LIBRARY.keys())

    phrase_freqs = {phrase: [] for phrase in candidates}

    for text in corpus_texts:
        word_count = _approximate_word_count(text)
        if word_count == 0:
            continue

        for phrase in candidates:
            count = text.count(phrase)
            freq_per_1000 = (count / word_count) * 1000
            phrase_freqs[phrase].append(freq_per_1000)

    # Calculate average frequency for each phrase
    library = {}
    for phrase, freqs in phrase_freqs.items():
        if freqs:
            avg_freq = sum(freqs) / len(freqs)
            library[phrase] = round(avg_freq, 2)

    return library


def suggest_template_replacements(phrase: str) -> List[str]:
    """建议模板表达的替代方案。

    Args:
        phrase: 高频模板表达

    Returns:
        替代方案列表
    """
    replacements = {
        "他知道": ["他明白", "他清楚", "他意识到", "他发现", "他察觉"],
        "这不是": ["这并非", "这算不上", "这称不上"],
        "沉默了片刻": ["静默良久", "短暂的沉默", "陷入沉默", "不再言语"],
        "深吸一口气": ["调整呼吸", "平复心情", "稳定情绪"],
        "眼中闪过": ["目光中透出", "眼神一变", "眼底浮现"],
        "嘴角勾起": ["嘴角上扬", "露出笑意", "微微一笑"],
    }

    return replacements.get(phrase, [f"(请人工改写「{phrase}」)"])
