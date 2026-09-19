#!/usr/bin/env python3
"""
P0 修复生产试运行脚本

小规模试运行（2-3 章），验证 P0-2 和 P0-3 修复在真实环境中的效果。

用途：
1. 验证 final_contract_validation 是否被正确填充
2. 验证 actual_entry_state 是否影响生成
3. 验证契约闭环完整性

使用方法：
    python3 scripts/p0_production_trial.py --chapters 3 [--dry-run]
"""
import argparse
import json
import sys
import tempfile
from pathlib import Path
from datetime import datetime


def create_trial_project(root: Path, chapters: int = 3):
    """创建试运行项目结构"""
    print(f"📦 创建试运行项目: {root}")

    # 创建基础目录
    facts = root / "registry" / "facts"
    meta = root / "registry" / "_meta"
    meta.mkdir(parents=True, exist_ok=True)

    # 写入元数据
    (meta / "registry-version").write_text("1\n", encoding="utf-8")
    (meta / "standard.pin").write_text("2.0.0\n", encoding="utf-8")

    # 创建时间线
    import yaml
    timeline_dir = facts / "timelines"
    timeline_dir.mkdir(parents=True, exist_ok=True)
    timeline = {
        "id": "TML-00001",
        "name": "主线试运行",
        "status": "active",
        "fact_version": 1,
        "kind": "main"
    }
    (timeline_dir / "TML-00001.yaml").write_text(
        yaml.safe_dump(timeline, allow_unicode=True, sort_keys=False),
        encoding="utf-8"
    )

    # 创建角色
    char_dir = facts / "characters"
    char_dir.mkdir(parents=True, exist_ok=True)
    characters = [
        {"id": "CHR-00001", "name": "主角", "status": "active", "fact_version": 1},
        {"id": "CHR-00002", "name": "配角A", "status": "active", "fact_version": 1},
    ]
    for char in characters:
        (char_dir / f"{char['id']}.yaml").write_text(
            yaml.safe_dump(char, allow_unicode=True, sort_keys=False),
            encoding="utf-8"
        )

    # 创建事件
    event_dir = facts / "events"
    event_dir.mkdir(parents=True, exist_ok=True)
    for i in range(1, chapters + 1):
        event = {
            "id": f"EVT-{i:05d}",
            "name": f"试运行事件{i}",
            "status": "active",
            "fact_version": 1,
            "timeline": "TML-00001",
            "sequence_index": i,
            "participants": ["CHR-00001"],
            "causes": [f"EVT-{i-1:05d}"] if i > 1 else [],
        }
        (event_dir / f"EVT-{i:05d}.yaml").write_text(
            yaml.safe_dump(event, allow_unicode=True, sort_keys=False),
            encoding="utf-8"
        )

    print(f"  ✅ 创建了 {chapters} 个事件")


def copy_contracts(dest_dir: Path, chapters: int = 3):
    """复制契约 fixtures"""
    print(f"📋 复制契约文件")

    fixtures = Path(__file__).parent.parent / "tests" / "fixtures" / "contracts"
    if not fixtures.exists():
        print(f"  ⚠️  契约 fixtures 不存在: {fixtures}")
        return False

    dest_dir.mkdir(parents=True, exist_ok=True)

    for i in range(1, min(chapters + 1, 4)):  # fixtures 最多有 3 章
        src = fixtures / f"chapter_{i:03d}_contract.json"
        if src.exists():
            dst = dest_dir / f"chapter_{i:03d}_contract.json"
            dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"  ✅ 复制契约: chapter_{i:03d}")
        else:
            print(f"  ⚠️  契约文件不存在: {src}")
            return False

    return True


def setup_schemas(dest_dir: Path):
    """设置 schema 文件"""
    print(f"📐 设置 schema 文件")

    schema_src = Path(__file__).parent.parent / "schemas" / "chapter_contract.schema.json"
    if not schema_src.exists():
        print(f"  ⚠️  Schema 文件不存在: {schema_src}")
        return False

    dest_dir.mkdir(parents=True, exist_ok=True)
    (dest_dir / "chapter_contract.schema.json").write_text(
        schema_src.read_text(encoding="utf-8"), encoding="utf-8"
    )
    print(f"  ✅ 设置 chapter_contract.schema.json")
    return True


def analyze_results(run_manifest_path: Path, output_dir: Path):
    """分析运行结果"""
    print("\n" + "="*60)
    print("📊 P0 修复验证结果分析")
    print("="*60)

    if not run_manifest_path.exists():
        print("⚠️  运行清单文件不存在")
        return

    manifest = json.loads(run_manifest_path.read_text(encoding="utf-8"))

    # 基本统计
    print(f"\n📈 基本统计:")
    print(f"  总章节: {len(manifest.get('chapters', []))}")
    print(f"  成功: {manifest.get('produced', 0)}")
    print(f"  跳过: {manifest.get('skipped', 0)}")

    # P0-2 验证
    print(f"\n🔍 P0-2 最终契约验证:")
    final_validation_count = 0
    final_validation_failures = 0

    for ch in manifest.get('chapters', []):
        if ch.get('final_contract_validation'):
            final_validation_count += 1
            if ch['final_contract_validation'].get('requires_revision'):
                final_validation_failures += 1
                print(f"  ⚠️  第 {ch['spec']['index']} 章: 最终验证发现 {ch['final_contract_validation'].get('critical_issues', 0)} 个关键问题")

    if final_validation_count > 0:
        print(f"  ✅ {final_validation_count} 章有最终契约验证记录")
        if final_validation_failures > 0:
            print(f"  ⚠️  {final_validation_failures} 章最终验证失败")
        else:
            print(f"  ✅ 所有章节最终验证通过")
    else:
        print(f"  ⚠️  没有章节有最终契约验证记录（可能未触发）")

    # P0-3 验证
    print(f"\n🔗 P0-3 实际出口回流:")
    exit_state_dir = output_dir.parent / "registry" / "derived" / "chapter-exit-state"

    if exit_state_dir.exists():
        exit_files = list(exit_state_dir.glob("exit-*.json"))
        print(f"  ✅ 提取了 {len(exit_files)} 个实际出口状态")

        for exit_file in sorted(exit_files)[:3]:  # 显示前 3 个
            exit_data = json.loads(exit_file.read_text(encoding="utf-8"))
            chapter = exit_data.get('chapter', '?')
            location = exit_data.get('location', 'N/A')
            print(f"    - 第 {chapter} 章: {location}")
    else:
        print(f"  ⚠️  未找到实际出口状态文件")

    # 契约偏差
    deviation_dir = output_dir.parent / "registry" / "derived" / "contract-deviation"
    if deviation_dir.exists():
        dev_files = list(deviation_dir.glob("dev-*.json"))
        if dev_files:
            print(f"\n📉 契约偏差:")
            print(f"  📊 记录了 {len(dev_files)} 个偏差报告")

    print("\n" + "="*60)


def run_trial(project_path: Path, chapters: int, dry_run: bool = False):
    """运行试运行"""
    print(f"\n🚀 开始 {chapters} 章试运行")
    print(f"   项目路径: {project_path}")
    print(f"   模式: {'DRY RUN (模拟)' if dry_run else 'REAL RUN (真实 LLM)'}")
    print()

    if dry_run:
        print("⚠️  DRY RUN 模式: 使用 mock，不调用真实 LLM")
        print()
        # TODO: 实现 dry-run 模式
        return None

    # 导入 run_serial
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from runtime.serialize.loop import run_serial

    # 准备参数
    contracts_dir = project_path / "contracts"
    schemas_dir = project_path / "schemas"
    out_dir = project_path / "out"
    standard_root = project_path / "standard"  # 可以为空

    # 运行
    print("⏳ 运行中...")
    try:
        result = run_serial(
            project_path=project_path,
            standard_root=standard_root,
            schema_dir=schemas_dir,
            out_dir=out_dir,
            model="mock-model",  # TODO: 使用真实模型
            reviewer="mock-reviewer",
            prompt_version="15.0.0",
            enable_contract_gate=True,
            contracts_dir=contracts_dir,
            strict_contract_mode=False,
            max_chapters=chapters,
        )

        print(f"\n✅ 运行完成")
        print(f"   生成: {result.produced} 章")
        print(f"   跳过: {result.skipped} 章")

        return result

    except Exception as e:
        print(f"\n❌ 运行失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    parser = argparse.ArgumentParser(description="P0 修复生产试运行")
    parser.add_argument("--chapters", type=int, default=3, help="运行章节数 (默认: 3)")
    parser.add_argument("--dry-run", action="store_true", help="模拟运行，不调用真实 LLM")
    parser.add_argument("--project-dir", type=str, help="使用现有项目目录（而非临时目录）")
    parser.add_argument("--analyze-only", type=str, help="仅分析指定的运行清单文件")

    args = parser.parse_args()

    # 仅分析模式
    if args.analyze_only:
        manifest_path = Path(args.analyze_only)
        if not manifest_path.exists():
            print(f"❌ 文件不存在: {manifest_path}")
            return 1

        output_dir = manifest_path.parent
        analyze_results(manifest_path, output_dir)
        return 0

    # 创建或使用项目目录
    if args.project_dir:
        project_path = Path(args.project_dir)
        project_path.mkdir(parents=True, exist_ok=True)
        print(f"📁 使用项目目录: {project_path}")
    else:
        tmpdir = tempfile.mkdtemp(prefix="p0-trial-")
        project_path = Path(tmpdir)
        print(f"📁 创建临时项目: {project_path}")

    try:
        # 设置项目
        create_trial_project(project_path, args.chapters)

        contracts_dir = project_path / "contracts"
        if not copy_contracts(contracts_dir, args.chapters):
            return 1

        schemas_dir = project_path / "schemas"
        if not setup_schemas(schemas_dir):
            return 1

        print(f"\n✅ 项目设置完成")

        # 运行试运行
        result = run_trial(project_path, args.chapters, args.dry_run)

        if result:
            # 分析结果
            manifest_path = project_path / "out" / "run-manifest.json"
            if manifest_path.exists():
                analyze_results(manifest_path, project_path / "out")
            else:
                print(f"\n⚠️  未找到运行清单: {manifest_path}")

        print(f"\n📂 项目目录: {project_path}")
        print(f"   保留以供检查")

        return 0 if result else 1

    except KeyboardInterrupt:
        print(f"\n⚠️  用户中断")
        return 130
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
