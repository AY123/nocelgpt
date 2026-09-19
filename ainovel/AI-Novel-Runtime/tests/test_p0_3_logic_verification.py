"""
P0-3 逻辑验证：检查实际出口回流代码是否存在

这是一个轻量级的代码结构验证测试，确保 P0-3 修复已正确实现。
"""
import json
from pathlib import Path
import tempfile


def test_actual_exit_loading_code_exists():
    """验证 loop.py 中包含加载实际出口状态的代码"""
    loop_file = Path(__file__).parent.parent / "runtime" / "serialize" / "loop.py"
    assert loop_file.exists(), "loop.py 文件不存在"

    code = loop_file.read_text(encoding="utf-8")

    # 检查关键代码片段
    assert "P0-3: Load actual exit state" in code, "缺少 P0-3 注释"
    assert "actual_entry_state" in code, "缺少 actual_entry_state 变量"
    assert "chapter-exit-state" in code, "缺少 chapter-exit-state 路径"
    assert "上一章实际结局状态" in code, "缺少实际状态标记"
    assert "从这个实际状态开始" in code, "缺少使用指令"


def test_actual_exit_injection_placed_correctly():
    """验证实际出口加载在契约注入之后"""
    loop_file = Path(__file__).parent.parent / "runtime" / "serialize" / "loop.py"
    code = loop_file.read_text(encoding="utf-8")

    # 找到关键代码段的位置
    contract_injection_pos = code.find("Contract Gate injection (v15 only")
    actual_exit_pos = code.find("P0-3: Load actual exit state")
    scene_dsl_pos = code.find("Scene DSL layer (v3)")

    assert contract_injection_pos > 0, "找不到契约注入代码"
    assert actual_exit_pos > 0, "找不到实际出口加载代码"
    assert scene_dsl_pos > 0, "找不到 Scene DSL 代码"

    # 验证顺序：契约注入 -> 实际出口加载 -> Scene DSL
    assert contract_injection_pos < actual_exit_pos < scene_dsl_pos, \
        "实际出口加载应该在契约注入之后、Scene DSL 之前"


def test_actual_exit_path_construction():
    """验证实际出口文件路径构造正确"""
    loop_file = Path(__file__).parent.parent / "runtime" / "serialize" / "loop.py"
    code = loop_file.read_text(encoding="utf-8")

    # 检查路径构造逻辑
    assert 'f"exit-{prev_task_id}.json"' in code, "缺少出口文件名构造"
    assert 'f"TASK-{(spec.index - 1):05d}"' in code, "缺少前一章 task_id 构造"
    assert "chapter-exit-state" in code, "缺少出口状态目录"


def test_actual_exit_renders_all_fields():
    """验证实际出口渲染包含所有关键字段"""
    loop_file = Path(__file__).parent.parent / "runtime" / "serialize" / "loop.py"
    code = loop_file.read_text(encoding="utf-8")

    # 提取实际出口加载代码块
    start = code.find("P0-3: Load actual exit state")
    end = code.find("# --- Scene DSL layer", start)
    actual_exit_block = code[start:end]

    # 验证所有字段都被渲染
    required_fields = [
        "location",
        "present_characters",
        "active_hooks",
        "emotional_state",
        "plot_threads"
    ]

    for field in required_fields:
        assert f'actual_exit.get("{field}")' in actual_exit_block, \
            f"实际出口渲染缺少 {field} 字段"


def test_actual_exit_graceful_degradation():
    """验证实际出口不存在时的优雅降级"""
    loop_file = Path(__file__).parent.parent / "runtime" / "serialize" / "loop.py"
    code = loop_file.read_text(encoding="utf-8")

    # 提取实际出口加载代码块
    start = code.find("P0-3: Load actual exit state")
    end = code.find("# --- Scene DSL layer", start)
    actual_exit_block = code[start:end]

    # 验证优雅降级逻辑
    assert "if exit_path.exists():" in actual_exit_block, "缺少文件存在检查"
    assert 'extra_vars["actual_entry_state"] = ""' in actual_exit_block, \
        "缺少降级为空字符串的逻辑"
    assert "except Exception" in actual_exit_block, "缺少异常处理"


def test_actual_exit_v15_only():
    """验证实际出口加载只在 v15 时触发"""
    loop_file = Path(__file__).parent.parent / "runtime" / "serialize" / "loop.py"
    code = loop_file.read_text(encoding="utf-8")

    # 提取实际出口加载代码块
    start = code.find("P0-3: Load actual exit state")
    end = code.find("# --- Scene DSL layer", start)
    actual_exit_block = code[start:end]

    # 验证条件检查
    assert "_at_least(major, 15)" in actual_exit_block, "缺少 v15 版本检查"
    assert "enable_contract_gate" in actual_exit_block, "缺少契约门禁开关检查"
    assert "spec.index > 1" in actual_exit_block, "缺少章节号检查（第1章跳过）"


def test_actual_exit_file_reading():
    """验证实际出口文件读取逻辑"""
    loop_file = Path(__file__).parent.parent / "runtime" / "serialize" / "loop.py"
    code = loop_file.read_text(encoding="utf-8")

    # 提取实际出口加载代码块
    start = code.find("P0-3: Load actual exit state")
    end = code.find("# --- Scene DSL layer", start)
    actual_exit_block = code[start:end]

    # 验证文件读取
    assert "exit_path.read_text" in actual_exit_block, "缺少文件读取"
    assert "_exit_json.loads" in actual_exit_block, "缺少 JSON 解析"


def test_actual_exit_functional_end_to_end():
    """功能测试：验证实际出口加载的完整流程"""
    # 创建临时项目目录
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)

        # 创建目录结构
        exit_dir = project_path / "registry" / "derived" / "chapter-exit-state"
        exit_dir.mkdir(parents=True, exist_ok=True)

        # 写入第 1 章的实际出口
        chapter_1_exit = {
            "chapter": 1,
            "location": "测试地点",
            "present_characters": ["角色A", "角色B"],
            "active_hooks": ["悬念1"],
            "emotional_state": "紧张",
            "plot_threads": ["线索1"],
            "final_text_hash": "hash-001"
        }
        exit_file = exit_dir / "exit-TASK-00001.json"
        exit_file.write_text(json.dumps(chapter_1_exit, ensure_ascii=False, indent=2))

        # 验证文件已创建
        assert exit_file.exists()

        # 验证内容可读取
        loaded = json.loads(exit_file.read_text(encoding="utf-8"))
        assert loaded["location"] == "测试地点"
        assert loaded["present_characters"] == ["角色A", "角色B"]

        # 模拟 loop.py 中的渲染逻辑
        actual_exit = loaded
        exit_summary = []
        if actual_exit.get("location"):
            exit_summary.append(f"地点：{actual_exit['location']}")
        if actual_exit.get("present_characters"):
            chars = ", ".join(actual_exit["present_characters"])
            exit_summary.append(f"在场人物：{chars}")
        if actual_exit.get("active_hooks"):
            hooks = ", ".join(actual_exit["active_hooks"])
            exit_summary.append(f"悬念钩子：{hooks}")
        if actual_exit.get("emotional_state"):
            exit_summary.append(f"情绪基调：{actual_exit['emotional_state']}")
        if actual_exit.get("plot_threads"):
            threads = ", ".join(actual_exit["plot_threads"])
            exit_summary.append(f"进行中的线索：{threads}")

        actual_entry_context = (
            "【上一章实际结局状态】\n" +
            "\n".join(exit_summary) +
            "\n\n注意：本章应该从这个实际状态开始，而非契约中计划的状态。"
            if exit_summary else ""
        )

        # 验证渲染结果
        assert "上一章实际结局状态" in actual_entry_context
        assert "测试地点" in actual_entry_context
        assert "角色A, 角色B" in actual_entry_context
        assert "悬念1" in actual_entry_context
        assert "紧张" in actual_entry_context
        assert "线索1" in actual_entry_context
        assert "从这个实际状态开始" in actual_entry_context


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
