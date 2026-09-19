#!/usr/bin/env python3
"""regenerate_chapters_34_100.py — 用标准 run_serial 重新生成 Chapter 34-100

执行方式：
  cd AI-Novel-Runtime
  PYTHONPATH=. python3 scripts/regenerate_chapters_34_100.py
"""
import sys
from pathlib import Path

# 添加 runtime 到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime.serialize.loop import run_serial
from runtime.execution.llm_model import LLMExecutionModel
from runtime.llm.factory import create_llm_client


def main():
    print("=== 重新生成 Chapter 34-100 ===")
    print("使用标准 run_serial，强制启用完整事实循环\n")

    # 配置路径
    project_root = Path(__file__).parent.parent.parent
    novel_dir = project_root / "novel-lingse"
    standard_root = project_root / "AI-Novel-Standard"
    schema_dir = standard_root / "phase-1" / "generated" / "json-schema"
    out_dir = novel_dir / "registry" / "derived"

    # 检查前置条件
    if not novel_dir.exists():
        raise FileNotFoundError(f"Novel directory not found: {novel_dir}")
    if not standard_root.exists():
        raise FileNotFoundError(f"Standard not found: {standard_root}")

    # 验证 Chapter 1-33 存在
    chapter_run_dir = novel_dir / "registry" / "derived" / "chapter-run"
    for i in range(1, 34):
        run_path = chapter_run_dir / f"run-TASK-{i:05d}.json"
        if not run_path.exists():
            raise FileNotFoundError(f"Chapter {i} missing: {run_path}")

    print("✓ 前置条件检查通过")
    print(f"  Novel: {novel_dir}")
    print(f"  Standard: {standard_root}")
    print(f"  Schema: {schema_dir}")

    # 创建 LLM 客户端（使用 Claude 中转）
    print(f"\n配置 LLM...")
    model = LLMExecutionModel(
        provider="claude",
        model_id="claude-opus-5",
        temperature=0.7,
        replay_dir=str(novel_dir / "registry" / "derived" / "serial-replay-regeneration")
    )
    print(f"  ✓ Provider: claude")
    print(f"  ✓ Model: claude-opus-5")

    # 创建 W12 模型（事实提取）
    w12_model = LLMExecutionModel(
        provider="claude",
        model_id="claude-sonnet-4",  # 事实提取用 sonnet 节省成本
        temperature=0.0,
        replay_dir=str(novel_dir / "registry" / "derived" / "serial-replay-w12")
    )
    print(f"  ✓ W12 Model: claude-sonnet-4")

    # 运行 serial
    print(f"\n开始生成 Chapter 34-100（共 67 章）...")
    print(f"预计时间: 3-6 小时")
    print(f"预计成本: $30-50\n")

    try:
        result = run_serial(
            project_path=str(novel_dir),
            standard_root=str(standard_root),
            schema_dir=str(schema_dir),
            out_dir=str(out_dir),
            model=model,
            start_chapter=34,           # 从 Chapter 34 开始
            max_chapters=67,            # 生成 67 章（34-100）
            prompt_version="14.0.0",    # 使用 v14（v15 需要 contract）
            w12_extract=True,           # 强制启用事实提取
            w12_model=w12_model,
            commercial_rounds=2,        # 商业优化轮次
            hygiene_rounds=2,           # 卫生检查轮次
            max_depth=2,                # 最大依赖深度
            enable_contract_gate=False,  # 禁用 contract gate
            enable_final_quality_review=False,  # 禁用最终质量评审
        )

        # 输出结果
        print(f"\n=== 生成完成 ===")
        print(f"总章节: {len(result.chapters)}")
        print(f"成功: {sum(1 for c in result.chapters if c.ok)}")
        print(f"失败: {sum(1 for c in result.chapters if not c.ok)}")

        # 成本统计
        if result.llm_cost:
            cost_data = result.llm_cost
            if isinstance(cost_data, dict):
                print(f"总成本: ¥{cost_data.get('total_cost', 0):.2f} {cost_data.get('currency', 'CNY')}")
            else:
                print(f"总成本: {cost_data}")

        if result.llm_usage:
            usage_data = result.llm_usage
            if isinstance(usage_data, dict):
                print(f"总 tokens: input={usage_data.get('input', 0):,}, output={usage_data.get('output', 0):,}")
            else:
                print(f"总 tokens: {usage_data}")

        # 检查事实增长
        import json
        events_dir = novel_dir / "registry" / "facts" / "events"
        events = sorted(events_dir.glob("EVT-*.yaml"))
        print(f"\nEvents 数量: {len(events)} 个")

        # 检查 state_hash 是否递增
        state_hashes = set()
        for c in result.chapters:
            if hasattr(c, 'state_hash'):
                state_hashes.add(c.state_hash)

        print(f"唯一 state_hash: {len(state_hashes)} 个")

        if len(state_hashes) > 1:
            print(f"✅ state_hash 正在递增（事实循环恢复）")
        else:
            print(f"⚠ state_hash 仍然冻结")

    except Exception as e:
        print(f"\n❌ 生成失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
