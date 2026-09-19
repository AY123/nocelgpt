"""
Enhanced Hook Evaluator - 升级章末钩子评估 (P1-2)

扩展现有的hook_check.py，区分钩子类型和质量，检测重复、假悬念、连续同类钩子。
"""
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum


class HookType(Enum):
    """钩子类型"""
    NEW_INFO = "new_info"  # 新信息差
    NEW_THREAT = "new_threat"  # 新威胁
    IDENTITY_REVEAL = "identity_reveal"  # 身份揭示
    DECISION_SUSPEND = "decision_suspend"  # 决策悬停
    REWARD_PREVIEW = "reward_preview"  # 爽点前置
    EMOTION_BREAK = "emotion_break"  # 情感破裂
    RULE_REVERSE = "rule_reverse"  # 规则反转
    GOAL_UPGRADE = "goal_upgrade"  # 目标升级
    COUNTDOWN = "countdown"  # 倒计时
    PAYWALL = "paywall"  # 付费断点
    NONE = "none"  # 无明确钩子


@dataclass
class HookQuality:
    """钩子质量评估"""
    hook_type: HookType
    strength: str  # "strong" | "medium" | "weak"

    # 问题标记
    is_repetition: bool = False  # 是否重复本章目标
    is_fake_suspense: bool = False  # 是否假悬念
    is_delay: bool = False  # 是否延迟兑现

    # 上下文
    text_snippet: str = ""  # 钩子文本片段
    position_in_chapter: float = 0.0  # 在章节中的位置(0-1)

    # 建议
    suggestions: List[str] = None

    def __post_init__(self):
        if self.suggestions is None:
            self.suggestions = []


class EnhancedHookEvaluator:
    """
    增强的章末钩子评估器

    在现有hook_check基础上，增加：
    1. 钩子类型分类
    2. 钩子质量评估
    3. 重复/假悬念检测
    4. 跨章节同类钩子检测
    """

    def __init__(self):
        # 钩子类型特征关键词
        self.hook_patterns = {
            HookType.NEW_INFO: [
                "原来", "竟然", "没想到", "发现", "看到", "听到", "得知",
                "turns out", "discovered", "revealed", "noticed",
            ],
            HookType.NEW_THREAT: [
                "危险", "威胁", "追来", "盯上", "找到", "包围", "陷阱",
                "danger", "threat", "approaching", "surrounded", "trap",
            ],
            HookType.IDENTITY_REVEAL: [
                "真实身份", "其实是", "背后", "隐藏", "秘密",
                "true identity", "actually", "behind", "hidden", "secret",
            ],
            HookType.DECISION_SUSPEND: [
                "该不该", "如何", "怎么办", "选择", "决定",
                "should", "how to", "what to do", "choice", "decision",
            ],
            HookType.REWARD_PREVIEW: [
                "即将", "马上", "下一步", "终于可以", "快要",
                "about to", "soon", "next", "finally can", "almost",
            ],
            HookType.COUNTDOWN: [
                "只剩", "还有", "仅剩", "时间不多", "天内", "小时内", "分钟内",
                "only", "remaining", "running out", "days left", "hours left",
            ],
        }

    def evaluate_hook(
        self,
        chapter_body: str,
        ending_text: str,
        chapter_objective: Optional[Dict[str, Any]] = None,
        previous_hooks: Optional[List[HookType]] = None,
    ) -> HookQuality:
        """
        评估章末钩子质量

        Args:
            chapter_body: 完整章节正文
            ending_text: 章末文本（最后200-500字）
            chapter_objective: 章节目标（用于检测重复）
            previous_hooks: 最近几章的钩子类型（用于检测同类重复）

        Returns:
            HookQuality 评估结果
        """
        # 1. 识别钩子类型
        hook_type = self._identify_hook_type(ending_text)

        # 2. 评估强度
        strength = self._assess_strength(ending_text, hook_type)

        # 3. 检测问题
        is_repetition = self._check_repetition(ending_text, chapter_body, chapter_objective)
        is_fake_suspense = self._check_fake_suspense(ending_text, hook_type)
        is_delay = self._check_延迟兑现(ending_text)

        # 4. 生成建议
        suggestions = self._generate_suggestions(
            hook_type, strength, is_repetition, is_fake_suspense, previous_hooks
        )

        return HookQuality(
            hook_type=hook_type,
            strength=strength,
            is_repetition=is_repetition,
            is_fake_suspense=is_fake_suspense,
            is_delay=is_delay,
            text_snippet=ending_text[-200:],
            position_in_chapter=len(ending_text) / len(chapter_body) if chapter_body else 1.0,
            suggestions=suggestions,
        )

    def _identify_hook_type(self, ending_text: str) -> HookType:
        """识别钩子类型"""
        # 统计每种类型的匹配数
        type_scores = {}

        for hook_type, patterns in self.hook_patterns.items():
            score = sum(1 for pattern in patterns if pattern in ending_text)
            if score > 0:
                type_scores[hook_type] = score

        if not type_scores:
            return HookType.NONE

        # 返回匹配最多的类型
        return max(type_scores, key=type_scores.get)

    def _assess_strength(self, ending_text: str, hook_type: HookType) -> str:
        """评估钩子强度"""
        if hook_type == HookType.NONE:
            return "weak"

        # 简单规则：包含感叹号/问号 → strong
        if "！" in ending_text or "!" in ending_text:
            return "strong"
        if "？" in ending_text or "?" in ending_text:
            return "strong"

        # 包含"但是"、"然而" → medium（有转折）
        if any(word in ending_text for word in ["但", "然而", "可是", "but", "however"]):
            return "medium"

        # 其他 → weak
        return "weak"

    def _check_repetition(
        self,
        ending_text: str,
        chapter_body: str,
        chapter_objective: Optional[Dict] = None
    ) -> bool:
        """检测是否重复本章目标（没有新信息）"""
        if not chapter_objective:
            return False

        # 提取目标关键词
        objective_text = chapter_objective.get("reader_question", "")
        if not objective_text:
            return False

        # 提取目标中的核心词汇（去掉疑问词）
        # 例如："他能否救出妹妹" → "救出妹妹"
        core_words = objective_text
        for q_word in ["能否", "是否", "会不会", "能不能", "如何", "怎么", "为什么"]:
            core_words = core_words.replace(q_word, "")
        core_words = core_words.strip()

        # 检查：核心词在结尾出现，但没有新信息标记
        has_objective_words = core_words[:4] in ending_text if len(core_words) >= 4 else False

        # 新信息标记词
        new_info_markers = ["新", "发现", "原来", "竟然", "没想到", "却", "但是", "然而"]
        has_new_info = any(marker in ending_text for marker in new_info_markers)

        # 如果有目标词但没有新信息 → 重复
        return has_objective_words and not has_new_info

    def _check_fake_suspense(self, ending_text: str, hook_type: HookType) -> bool:
        """检测假悬念（提出问题但答案显而易见）"""
        # 简单规则：疑问句但紧接着就给出答案
        if "？" in ending_text or "?" in ending_text:
            # 检查问号后是否有明确答案
            parts = ending_text.split("？") if "？" in ending_text else ending_text.split("?")
            if len(parts) > 1 and len(parts[1]) > 10:
                # 问号后还有内容 → 可能是自问自答
                return True

        return False

    def _check_延迟兑现(self, ending_text: str) -> bool:
        """检测延迟兑现（承诺下章兑现但模糊）"""
        delay_markers = ["下次", "以后", "将来", "有机会", "next time", "later", "someday"]
        return any(marker in ending_text for marker in delay_markers)

    def _generate_suggestions(
        self,
        hook_type: HookType,
        strength: str,
        is_repetition: bool,
        is_fake_suspense: bool,
        previous_hooks: Optional[List[HookType]] = None,
    ) -> List[str]:
        """生成改进建议"""
        suggestions = []

        if hook_type == HookType.NONE:
            suggestions.append("增加明确的章末钩子：新信息、新威胁或决策悬停")

        if strength == "weak":
            suggestions.append("增强钩子力度：使用更强的冲突或信息差")

        if is_repetition:
            suggestions.append("避免重复本章目标，引入新的问题或视角")

        if is_fake_suspense:
            suggestions.append("避免自问自答式假悬念，保留真实的未知")

        # 检测连续同类钩子
        if previous_hooks and len(previous_hooks) >= 2:
            if all(h == hook_type for h in previous_hooks[-2:]):
                suggestions.append(f"连续使用相同类型钩子({hook_type.value})，考虑变换钩子类型")

        return suggestions

    def check_serial_hook_variety(
        self,
        chapter_hooks: List[HookQuality],
        window_size: int = 5,
    ) -> Dict[str, Any]:
        """
        检查跨章节钩子多样性

        Args:
            chapter_hooks: 多个章节的钩子评估结果
            window_size: 检查窗口大小

        Returns:
            多样性报告
        """
        if len(chapter_hooks) < window_size:
            return {"sufficient_data": False}

        # 统计最近N章的钩子类型分布
        recent_types = [h.hook_type for h in chapter_hooks[-window_size:]]
        type_counts = {}
        for t in recent_types:
            type_counts[t] = type_counts.get(t, 0) + 1

        # 计算多样性（使用Shannon熵或简单的唯一类型数）
        unique_types = len(type_counts)
        diversity_score = unique_types / window_size

        # 检测连续重复
        consecutive_same = 1
        for i in range(1, len(recent_types)):
            if recent_types[i] == recent_types[i-1]:
                consecutive_same += 1
            else:
                break

        return {
            "sufficient_data": True,
            "window_size": window_size,
            "unique_types": unique_types,
            "diversity_score": diversity_score,
            "type_distribution": {t.value: c for t, c in type_counts.items()},
            "consecutive_same": consecutive_same,
            "monotonous": (consecutive_same >= 3 or unique_types <= 2),
            "warnings": self._diversity_warnings(unique_types, consecutive_same, window_size),
        }

    def _diversity_warnings(
        self,
        unique_types: int,
        consecutive_same: int,
        window_size: int,
    ) -> List[str]:
        """生成多样性警告"""
        warnings = []

        if unique_types <= 2:
            warnings.append(f"最近{window_size}章钩子类型单一（仅{unique_types}种），读者易产生疲劳")

        if consecutive_same >= 3:
            warnings.append(f"连续{consecutive_same}章使用相同钩子类型，建议变换")

        return warnings
