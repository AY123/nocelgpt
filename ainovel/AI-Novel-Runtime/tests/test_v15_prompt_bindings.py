"""
测试 v15 prompt 绑定：验证 chapter_contract 和 actual_entry_state

验证 binding.py 正确声明了 v15 需要的新变量。
"""
from pathlib import Path


def test_chapter_contract_binding_exists():
    """验证 binding.py 包含 chapter_contract 绑定逻辑"""
    binding_file = Path(__file__).parent.parent / "runtime" / "prompt" / "binding.py"
    assert binding_file.exists(), "binding.py 文件不存在"

    code = binding_file.read_text(encoding="utf-8")

    # 检查关键代码片段
    assert "chapter_contract" in code, "缺少 chapter_contract 变量"
    assert 'if extra.get("chapter_contract")' in code, "缺少 chapter_contract 条件检查"
    assert "Contract Gate, Phase 3 v15" in code, "缺少 Contract Gate 注释"
    assert 'binding["chapter_contract"]' in code, "缺少 chapter_contract 绑定"


def test_actual_entry_state_binding_exists():
    """验证 binding.py 包含 actual_entry_state 绑定逻辑"""
    binding_file = Path(__file__).parent.parent / "runtime" / "prompt" / "binding.py"
    code = binding_file.read_text(encoding="utf-8")

    # 检查关键代码片段
    assert "actual_entry_state" in code, "缺少 actual_entry_state 变量"
    assert 'if extra.get("actual_entry_state")' in code, "缺少 actual_entry_state 条件检查"
    assert "P0-3: Actual Exit Reflow" in code, "缺少 P0-3 注释"
    assert 'binding["actual_entry_state"]' in code, "缺少 actual_entry_state 绑定"


def test_binding_order_correct():
    """验证绑定顺序：genre_contract -> chapter_contract -> actual_entry_state"""
    binding_file = Path(__file__).parent.parent / "runtime" / "prompt" / "binding.py"
    code = binding_file.read_text(encoding="utf-8")

    genre_pos = code.find('if extra.get("genre_contract")')
    chapter_contract_pos = code.find('if extra.get("chapter_contract")')
    actual_entry_pos = code.find('if extra.get("actual_entry_state")')

    assert genre_pos > 0, "找不到 genre_contract"
    assert chapter_contract_pos > 0, "找不到 chapter_contract"
    assert actual_entry_pos > 0, "找不到 actual_entry_state"

    # 验证顺序
    assert genre_pos < chapter_contract_pos < actual_entry_pos, \
        "绑定顺序错误，应该是 genre_contract -> chapter_contract -> actual_entry_state"


def test_v15_chapter_uses_actual_entry_state():
    """验证 v15 chapter.py 使用 actual_entry_state"""
    chapter_file = Path(__file__).parent.parent / "runtime" / "prompts" / "v15" / "chapter.py"
    assert chapter_file.exists(), "v15/chapter.py 文件不存在"

    code = chapter_file.read_text(encoding="utf-8")

    # 检查 actual_entry_state 的使用
    assert "actual_entry_state" in code, "v15 chapter.py 缺少 actual_entry_state"
    assert "context.get('actual_entry_state'" in code, "缺少从 context 读取 actual_entry_state"
    assert "if actual_entry_state:" in code, "缺少 actual_entry_state 条件检查"


def test_binding_preserves_backward_compatibility():
    """验证绑定保持向后兼容性"""
    binding_file = Path(__file__).parent.parent / "runtime" / "prompt" / "binding.py"
    code = binding_file.read_text(encoding="utf-8")

    # 检查所有新绑定都使用 "ONLY when supplied" 模式（可能跨行）
    chapter_contract_block = code[code.find("chapter_contract"):code.find("actual_entry_state")]
    assert "ONLY when" in chapter_contract_block and "supplied" in chapter_contract_block, \
        "chapter_contract 未使用 'ONLY when supplied' 模式"

    # 扩大搜索范围以包含完整的 actual_entry_state 注释块
    actual_entry_start = code.find("actual_entry_state")
    actual_entry_block = code[actual_entry_start:actual_entry_start + 1000]
    assert "ONLY when" in actual_entry_block and "supplied" in actual_entry_block, \
        "actual_entry_state 未使用 'ONLY when supplied' 模式"


def test_binding_creates_prompt_variable():
    """验证绑定创建 PromptVariable 对象"""
    binding_file = Path(__file__).parent.parent / "runtime" / "prompt" / "binding.py"
    code = binding_file.read_text(encoding="utf-8")

    # 检查 PromptVariable 创建
    assert 'PromptVariable(\n            "chapter_contract"' in code or \
           'PromptVariable("chapter_contract"' in code, \
        "chapter_contract 未创建 PromptVariable"

    assert 'PromptVariable(\n            "actual_entry_state"' in code or \
           'PromptVariable("actual_entry_state"' in code, \
        "actual_entry_state 未创建 PromptVariable"


def test_v15_graceful_degradation():
    """验证 v15 在缺少变量时优雅降级"""
    chapter_file = Path(__file__).parent.parent / "runtime" / "prompts" / "v15" / "chapter.py"
    code = chapter_file.read_text(encoding="utf-8")

    # 检查默认值处理
    assert "context.get('actual_entry_state', '')" in code, \
        "actual_entry_state 缺少默认值（应该是空字符串）"

    # 检查条件渲染
    assert "if actual_entry_state:" in code, \
        "缺少 actual_entry_state 的条件渲染逻辑"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
