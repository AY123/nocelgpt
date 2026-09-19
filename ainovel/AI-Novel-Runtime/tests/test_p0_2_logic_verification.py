"""
P0-2 逻辑验证：检查代码中是否包含最终契约验证逻辑

这是一个轻量级的代码结构验证测试，确保 P0-2 修复已正确实现。
"""
import ast
import inspect
from pathlib import Path


def test_final_contract_validation_code_exists():
    """验证 loop.py 中包含最终契约验证的代码"""
    loop_file = Path(__file__).parent.parent / "runtime" / "serialize" / "loop.py"
    assert loop_file.exists(), "loop.py 文件不存在"

    code = loop_file.read_text(encoding="utf-8")

    # 检查关键代码片段
    assert "final_contract_validation" in code, "缺少 final_contract_validation 变量"
    assert "P0-2: Final Contract Validation" in code, "缺少 P0-2 注释"
    assert "draft_changed_after_revision" in code, "缺少变更检测逻辑"
    assert "final_after_all_modifications" in code, "缺少最终验证阶段标记"


def test_chapter_run_has_final_validation_field():
    """验证 ChapterRun 数据类包含 final_contract_validation 字段"""
    from runtime.serialize.loop import ChapterRun

    # 检查字段是否存在
    assert hasattr(ChapterRun, "__annotations__"), "ChapterRun 应该是 dataclass"
    annotations = ChapterRun.__annotations__
    assert "final_contract_validation" in annotations, "ChapterRun 缺少 final_contract_validation 字段"

    # 检查字段类型
    from typing import get_args, get_origin
    field_type = annotations["final_contract_validation"]
    assert get_origin(field_type) is type(None) or "Optional" in str(field_type), \
        "final_contract_validation 应该是 Optional 类型"


def test_chapter_run_to_dict_includes_final_validation():
    """验证 ChapterRun.to_dict() 包含 final_contract_validation"""
    from runtime.serialize.loop import ChapterRun, ChapterSpec

    # 创建一个测试实例
    spec = ChapterSpec(
        index=1,
        task_id="TASK-00001",
        event_id="EVT-001",
        seeds=["EVT-001"],
        goal="test goal"
    )

    run = ChapterRun(
        spec=spec,
        ok=True,
        stage="done",
        final_contract_validation={"test": "data"}
    )

    result = run.to_dict()
    assert "final_contract_validation" in result, "to_dict() 缺少 final_contract_validation"
    assert result["final_contract_validation"] == {"test": "data"}


def test_final_validation_placed_after_hygiene():
    """验证最终契约验证在卫生循环之后"""
    loop_file = Path(__file__).parent.parent / "runtime" / "serialize" / "loop.py"
    code = loop_file.read_text(encoding="utf-8")

    # 找到关键代码段的位置
    hygiene_pos = code.find("optional Prose Hygiene correction loop")
    final_validation_pos = code.find("P0-2: Final Contract Validation")
    state_projection_pos = code.find("project state as of this chapter's event")

    assert hygiene_pos > 0, "找不到卫生循环代码"
    assert final_validation_pos > 0, "找不到最终验证代码"
    assert state_projection_pos > 0, "找不到状态投影代码"

    # 验证顺序：卫生 -> 最终验证 -> 状态投影
    assert hygiene_pos < final_validation_pos < state_projection_pos, \
        "最终契约验证应该在卫生循环之后、状态投影之前"


def test_final_validation_checks_hash_change():
    """验证最终验证逻辑检查 hash 变化"""
    loop_file = Path(__file__).parent.parent / "runtime" / "serialize" / "loop.py"
    code = loop_file.read_text(encoding="utf-8")

    # 检查是否包含 hash 变化检测逻辑
    assert "revision_final_hash" in code, "缺少修订后 hash 记录"
    assert "current_hash != revision_final_hash" in code, "缺少 hash 变化比较"
    assert "draft_changed_after_revision" in code, "缺少变化标志"


def test_final_validation_conditional_execution():
    """验证最终验证只在草稿变化时执行"""
    loop_file = Path(__file__).parent.parent / "runtime" / "serialize" / "loop.py"
    code = loop_file.read_text(encoding="utf-8")

    # 提取最终验证代码块
    start = code.find("P0-2: Final Contract Validation")
    end = code.find("# --- project state as of this chapter's event", start)
    validation_block = code[start:end]

    # 验证条件检查
    assert "if draft_changed_after_revision:" in validation_block, \
        "最终验证应该只在草稿变化时执行"
    assert "check_candidate" in validation_block, \
        "最终验证应该调用 check_candidate"


def test_run_serial_accepts_final_validation_in_chapter_run():
    """验证 run_serial 创建 ChapterRun 时传入 final_contract_validation"""
    loop_file = Path(__file__).parent.parent / "runtime" / "serialize" / "loop.py"
    code = loop_file.read_text(encoding="utf-8")

    # 找到 ChapterRun 构造调用
    chapter_run_calls = []
    for i, line in enumerate(code.split("\n")):
        if "result.chapters.append(ChapterRun(" in line:
            # 找到这个调用的完整代码块（直到匹配的右括号）
            start = i
            chapter_run_calls.append(start)

    assert len(chapter_run_calls) > 0, "找不到 ChapterRun 构造调用"

    # 检查成功的 ChapterRun 调用（ok=True）
    lines = code.split("\n")
    for call_start in chapter_run_calls:
        # 向后查找直到找到完整的调用
        call_block = []
        for j in range(call_start, min(call_start + 30, len(lines))):
            call_block.append(lines[j])
            if "))" in lines[j]:
                break

        call_text = "\n".join(call_block)
        # P0-1: Changed from ok=True to ok=chapter_ok
        if ("ok=True" in call_text or "ok=chapter_ok" in call_text) and "stage=\"done\"" in call_text:
            # 这是成功的 ChapterRun，应该包含 final_contract_validation
            assert "final_contract_validation=" in call_text, \
                "成功的 ChapterRun 应该传入 final_contract_validation 参数"
            return

    raise AssertionError("找不到成功的 ChapterRun 调用")


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
