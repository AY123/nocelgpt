"""
genre_contract.py — 题材契约门禁验证器（P0-B）

与 serial_genre_drift 的区别：
- serial_genre_drift: 咨询性，检测题材漂移趋势（gating=False）
- genre_contract: 门禁性，阻止明显的题材违规（gating=True）

门禁规则：
1. 都市题材不能包含：修炼、境界、灵气、法宝、渡劫等玄幻元素
2. 玄幻题材不能包含：公司、股票、互联网等现代都市元素
3. 奇幻题材不能包含：现代科技、都市场景

使用场景：
- outline 生成后验证
- chapter 生成后验证
- build 流程中作为门禁
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class GenreViolation:
    """题材违规记录"""
    chapter_id: Optional[str]
    violation_type: str  # "forbidden_keyword" | "missing_required"
    keyword: str
    context: str  # 违规关键词的上下文
    severity: str  # "error" | "warning"


@dataclass
class GenreContractResult:
    """题材契约验证结果"""
    ok: bool
    declared_genre: str
    violations: List[GenreViolation]
    message: str


# 题材禁用关键词表
GENRE_FORBIDDEN_KEYWORDS = {
    "都市": [
        # 修炼体系
        "修炼", "境界", "突破境界", "炼气", "筑基", "金丹", "元婴", "化神",
        # 灵气/能量
        "灵气", "灵力", "真元", "法力", "灵根", "灵脉",
        # 法宝/道具
        "法宝", "灵器", "法器", "丹药", "灵丹", "灵药",
        # 神通/术法
        "神通", "法术", "咒语", "阵法", "禁制", "渡劫",
        # 奇幻生物
        "妖兽", "灵兽", "魔兽", "巨龙", "精灵族",
        # 异世界
        "异世界", "穿越时空", "异界", "位面",
    ],
    "玄幻": [
        # 现代商业
        "股票", "A股", "股市", "上市公司", "IPO", "风投", "创业公司",
        # 现代科技
        "互联网", "电商", "APP", "软件开发", "程序员", "代码",
        # 现代职场
        "996", "打工人", "社畜", "实习生", "简历", "面试",
    ],
    "奇幻": [
        # 现代科技
        "互联网", "电脑", "手机", "汽车", "飞机", "火车",
        # 现代都市
        "CBD", "写字楼", "地铁", "高铁", "高速公路",
    ],
}

# 题材必需元素（可选检查）
GENRE_REQUIRED_ELEMENTS = {
    "都市": ["现代", "城市"],  # 至少应该有现代城市背景
    "玄幻": ["修炼", "境界", "实力"],  # 玄幻应该有实力体系
}


def validate_genre_contract(
    declared_genre: str,
    content: str,
    *,
    chapter_id: Optional[str] = None,
    strict: bool = True,
) -> GenreContractResult:
    """
    验证内容是否符合题材契约

    Args:
        declared_genre: 声明的题材（如"都市"、"玄幻"）
        content: 要验证的文本内容（outline/chapter body）
        chapter_id: 章节ID（用于错误消息）
        strict: 严格模式（True=发现违规立即失败，False=记录警告）

    Returns:
        GenreContractResult: 验证结果
    """
    violations = []

    # 提取主题材（去除子类型）
    primary_genre = declared_genre.split()[0] if declared_genre else ""
    if primary_genre == "都市重生":
        primary_genre = "都市"

    # 检查禁用关键词
    forbidden = GENRE_FORBIDDEN_KEYWORDS.get(primary_genre, [])
    for keyword in forbidden:
        if keyword in content:
            # 提取上下文（关键词前后各30字符）
            idx = content.find(keyword)
            start = max(0, idx - 30)
            end = min(len(content), idx + len(keyword) + 30)
            context = content[start:end]

            violations.append(GenreViolation(
                chapter_id=chapter_id,
                violation_type="forbidden_keyword",
                keyword=keyword,
                context=context,
                severity="error" if strict else "warning"
            ))

    # 构造结果
    if violations:
        error_count = sum(1 for v in violations if v.severity == "error")
        warning_count = len(violations) - error_count

        if strict and error_count > 0:
            message = (
                f"题材契约验证失败：{declared_genre} 题材包含 {error_count} 处禁用元素。\n"
                f"违规关键词: {', '.join(set(v.keyword for v in violations[:5]))}"
            )
            if len(violations) > 5:
                message += f" 等共 {len(violations)} 处"

            return GenreContractResult(
                ok=False,
                declared_genre=declared_genre,
                violations=violations,
                message=message
            )
        else:
            message = (
                f"题材契约检查：发现 {warning_count} 处可疑元素，但未阻止生成。\n"
                f"建议检查: {', '.join(set(v.keyword for v in violations[:3]))}"
            )
            return GenreContractResult(
                ok=True,
                declared_genre=declared_genre,
                violations=violations,
                message=message
            )

    # 无违规
    return GenreContractResult(
        ok=True,
        declared_genre=declared_genre,
        violations=[],
        message=f"题材契约验证通过：{declared_genre} 题材无明显违规元素"
    )


def validate_outline_genre(outline: dict) -> GenreContractResult:
    """验证 outline 的题材契约"""
    genre = outline.get("genre", ["未知"])[0] if outline.get("genre") else "未知"

    # 收集所有文本内容
    content_parts = []

    # logline
    if "logline" in outline:
        content_parts.append(outline["logline"])

    # world summary
    if "world" in outline and "summary" in outline["world"]:
        content_parts.append(outline["world"]["summary"])

    # characters
    for char in outline.get("characters", []):
        if "arc" in char:
            content_parts.append(char["arc"])
        if "motivation" in char:
            content_parts.append(char["motivation"])

    content = "\n".join(content_parts)

    return validate_genre_contract(
        declared_genre=genre,
        content=content,
        strict=True
    )


def validate_chapter_genre(chapter_body: str, declared_genre: str, chapter_id: str) -> GenreContractResult:
    """验证 chapter 的题材契约"""
    return validate_genre_contract(
        declared_genre=declared_genre,
        content=chapter_body,
        chapter_id=chapter_id,
        strict=True
    )


class GenreContractViolationError(Exception):
    """题材契约违规异常"""
    def __init__(self, result: GenreContractResult):
        self.result = result
        super().__init__(result.message)
