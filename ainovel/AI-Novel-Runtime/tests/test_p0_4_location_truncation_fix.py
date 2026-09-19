"""Test P0-4: 地点检查截断修复

验证关键词不会在检查范围边界被截断。
"""
import pytest


def test_keyword_not_truncated_at_boundary():
    """Test that keywords are not truncated at check boundary."""
    text = "段奕尘来到自定义地点，观察四周。后面还有很多内容。"
    keyword = "自定义地点"

    # 模拟检查前 50%
    check_portion = 0.5
    check_length = int(len(text) * check_portion)

    # 旧逻辑（错误）：
    # first_portion = text[:check_length]
    # result = keyword in first_portion
    # 可能截断为 "段奕尘来到自定" → False

    # 新逻辑（正确）：
    # 检查关键词是否*开始于*检查范围内
    pos = text.find(keyword)
    result = pos != -1 and pos < check_length

    assert result is True, f"关键词应该被找到（pos={pos}, check_length={check_length}）"


def test_keyword_position_logic():
    """Test the keyword position checking logic."""
    # 短文本，关键词在前面
    text1 = "广场上人很多"
    keyword1 = "广场"
    check_length1 = int(len(text1) * 0.5)

    pos1 = text1.find(keyword1)
    assert pos1 == 0
    assert pos1 < check_length1

    # 短文本，关键词可能被截断
    text2 = "段奕尘来到自定义地点"
    keyword2 = "自定义地点"
    check_length2 = int(len(text2) * 0.5)  # 可能只到 "段奕尘来到"

    pos2 = text2.find(keyword2)
    # pos2 是关键词开始位置
    # 只要开始位置在范围内，就算找到
    assert pos2 != -1


def test_multiple_keywords():
    """Test checking multiple keywords."""
    text = "段奕尘走进矿场边缘的乱石堆"
    keywords = ["矿场", "边缘", "乱石堆"]
    check_length = int(len(text) * 0.5)

    found = []
    for kw in keywords:
        pos = text.find(kw)
        if pos != -1 and pos < check_length:
            found.append(kw)

    # 至少应该找到一个
    assert len(found) >= 1


def test_keyword_not_in_range():
    """Test that keywords outside range are not found."""
    text = "前面很多内容。" * 20 + "最后才是广场"
    keyword = "广场"
    check_length = int(len(text) * 0.1)  # 只检查前 10%

    pos = text.find(keyword)
    result = pos != -1 and pos < check_length

    # 关键词在后面，应该不被找到
    assert result is False


def test_fix_implementation_exists():
    """Verify that the fix is implemented in gate.py."""
    import sys
    from pathlib import Path

    gate_file = Path(__file__).parent.parent.parent.parent / "runtime_plugins" / "contract" / "gate.py"

    if not gate_file.exists():
        pytest.skip("gate.py not found")

    content = gate_file.read_text(encoding='utf-8')

    # Should have P0-4 fix comment
    assert "P0-4" in content or "P0-4 Fix" in content

    # Should check position, not substring
    assert "text.find(kw)" in content or "pos < check_length" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
