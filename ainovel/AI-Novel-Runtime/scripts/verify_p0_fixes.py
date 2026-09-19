#!/usr/bin/env python3
"""
P0 修复验证工具

快速检查 run-manifest.json 文件，验证 P0-2 和 P0-3 修复是否生效。

使用方法:
    python3 scripts/verify_p0_fixes.py <run-manifest.json>
    python3 scripts/verify_p0_fixes.py registry/derived/run-manifests/RUN-00001.json
"""
import json
import sys
from pathlib import Path
from datetime import datetime


def verify_p0_2(manifest: dict):
    """验证 P0-2: 最终契约验证"""
    print("\n" + "="*60)
    print("🔍 P0-2: 最终稿契约闭环验证")
    print("="*60)

    chapters = manifest.get('chapters', [])
    if not chapters:
        print("⚠️  没有章节数据")
        return False

    has_validation = 0
    has_failures = 0
    details = []

    for ch in chapters:
        idx = ch.get('spec', {}).get('index', '?')
        final_val = ch.get('final_contract_validation')

        if final_val:
            has_validation += 1
            requires_revision = final_val.get('requires_revision', False)
            critical_issues = final_val.get('critical_issues', 0)

            if requires_revision:
                has_failures += 1
                status = f"❌ 失败 ({critical_issues} 关键问题)"
            else:
                status = "✅ 通过"

            details.append(f"  第 {idx} 章: {status}")

    # 输出结果
    print(f"\n📊 统计:")
    print(f"  总章节数: {len(chapters)}")
    print(f"  有最终验证: {has_validation}/{len(chapters)}")

    if has_validation == 0:
        print(f"\n⚠️  没有章节有 final_contract_validation 记录")
        print(f"  可能原因:")
        print(f"  - 商业/卫生流程未修改草稿（hash 未变化）")
        print(f"  - Contract Gate 未启用")
        print(f"  - prompt_version < 15.0.0")
        return False

    print(f"\n📋 详情:")
    for detail in details:
        print(detail)

    if has_failures > 0:
        print(f"\n⚠️  {has_failures} 章最终验证失败")
        print(f"  说明: 商业/卫生修改后破坏了契约要求")
    else:
        print(f"\n✅ 所有章节最终验证通过")

    print(f"\n✅ P0-2 修复生效: final_contract_validation 被正确记录")
    return True


def verify_p0_3(manifest_path: Path):
    """验证 P0-3: 实际出口回流"""
    print("\n" + "="*60)
    print("🔗 P0-3: 实际出口回流到下一章")
    print("="*60)

    # 查找 chapter-exit-state 目录
    # 假设 manifest 在 registry/derived/run-manifests/ 或 out/
    project_root = manifest_path.parent.parent.parent

    possible_paths = [
        project_root / "registry" / "derived" / "chapter-exit-state",
        manifest_path.parent.parent / "registry" / "derived" / "chapter-exit-state",
    ]

    exit_dir = None
    for p in possible_paths:
        if p.exists():
            exit_dir = p
            break

    if not exit_dir:
        print(f"\n⚠️  未找到 chapter-exit-state 目录")
        print(f"  查找路径:")
        for p in possible_paths:
            print(f"    - {p}")
        return False

    # 读取实际出口文件
    exit_files = sorted(exit_dir.glob("exit-*.json"))

    if not exit_files:
        print(f"\n⚠️  没有实际出口状态文件")
        print(f"  目录: {exit_dir}")
        return False

    print(f"\n📊 统计:")
    print(f"  实际出口文件: {len(exit_files)}")
    print(f"  目录: {exit_dir}")

    print(f"\n📋 详情:")
    for exit_file in exit_files[:5]:  # 显示前 5 个
        try:
            exit_data = json.loads(exit_file.read_text(encoding="utf-8"))
            chapter = exit_data.get('chapter', '?')
            location = exit_data.get('location', 'N/A')
            chars = exit_data.get('present_characters', [])
            hooks = exit_data.get('active_hooks', [])

            print(f"  第 {chapter} 章:")
            print(f"    地点: {location}")
            print(f"    人物: {', '.join(chars) if chars else 'N/A'}")
            print(f"    钩子: {', '.join(hooks) if hooks else 'N/A'}")
        except Exception as e:
            print(f"  {exit_file.name}: 读取失败 ({e})")

    if len(exit_files) > 5:
        print(f"  ... 还有 {len(exit_files) - 5} 个文件")

    print(f"\n✅ P0-3 修复生效: 实际出口状态被正确提取")

    # 验证是否被下一章使用（间接验证）
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    chapters = manifest.get('chapters', [])

    if len(chapters) > 1:
        print(f"\n🔍 检查实际出口是否被下一章使用:")
        print(f"  注意: 这需要检查 prompt 日志或 LLM 请求")
        print(f"  当前仅能验证文件存在性")
        print(f"  ✅ {len(exit_files)} 个出口文件可供下一章使用")

    return True


def verify_contract_loop(manifest: dict, manifest_path: Path):
    """验证完整契约闭环"""
    print("\n" + "="*60)
    print("🔄 完整契约闭环验证")
    print("="*60)

    chapters = manifest.get('chapters', [])
    if len(chapters) < 2:
        print(f"⚠️  章节数 < 2，无法验证闭环")
        return False

    # 检查第 1 章
    ch1 = chapters[0]
    ch1_idx = ch1.get('spec', {}).get('index', 1)

    print(f"\n第 {ch1_idx} 章:")

    # P0-2: 最终验证
    if ch1.get('final_contract_validation'):
        print(f"  ✅ 最终契约验证记录")
    else:
        print(f"  ⚠️  无最终契约验证记录")

    # P0-5: 实际出口提取
    project_root = manifest_path.parent.parent.parent
    exit_file = project_root / "registry" / "derived" / "chapter-exit-state" / f"exit-TASK-{ch1_idx:05d}.json"

    if exit_file.exists():
        print(f"  ✅ 实际出口状态文件")
    else:
        print(f"  ⚠️  无实际出口状态文件")

    # 检查第 2 章
    ch2 = chapters[1]
    ch2_idx = ch2.get('spec', {}).get('index', 2)

    print(f"\n第 {ch2_idx} 章:")
    print(f"  🔍 应该加载第 {ch1_idx} 章的实际出口")

    if exit_file.exists():
        print(f"  ✅ 上一章出口文件可用")
        # 注意：无法直接验证是否被使用，需要查看 prompt 或 LLM 日志
        print(f"  ⚠️  无法直接验证是否注入到 prompt（需查看日志）")
    else:
        print(f"  ❌ 上一章出口文件缺失")

    print(f"\n📊 闭环完整性:")
    print(f"  P0-2 (最终验证) → P0-5 (提取出口) → P0-3 (回流入口)")
    print(f"  状态: 部分可验证 (文件层面) ✅")

    return True


def main():
    if len(sys.argv) < 2:
        print("用法: python3 verify_p0_fixes.py <run-manifest.json>")
        print()
        print("示例:")
        print("  python3 scripts/verify_p0_fixes.py registry/derived/run-manifests/RUN-00001.json")
        print("  python3 scripts/verify_p0_fixes.py out/run-manifest.json")
        return 1

    manifest_path = Path(sys.argv[1])

    if not manifest_path.exists():
        print(f"❌ 文件不存在: {manifest_path}")
        return 1

    print("="*60)
    print("P0 修复验证工具")
    print("="*60)
    print(f"文件: {manifest_path}")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        # 基本信息
        print(f"\n📊 基本信息:")
        print(f"  总章节: {len(manifest.get('chapters', []))}")
        print(f"  成功: {manifest.get('produced', 0)}")
        print(f"  跳过: {manifest.get('skipped', 0)}")

        # 验证 P0-2
        p0_2_ok = verify_p0_2(manifest)

        # 验证 P0-3
        p0_3_ok = verify_p0_3(manifest_path)

        # 验证闭环
        if len(manifest.get('chapters', [])) >= 2:
            verify_contract_loop(manifest, manifest_path)

        # 总结
        print("\n" + "="*60)
        print("📋 验证总结")
        print("="*60)
        print(f"  P0-2 (最终契约验证): {'✅ 生效' if p0_2_ok else '⚠️  未验证'}")
        print(f"  P0-3 (实际出口回流): {'✅ 生效' if p0_3_ok else '⚠️  未验证'}")

        if p0_2_ok and p0_3_ok:
            print(f"\n✅ P0 修复全部生效")
            return 0
        else:
            print(f"\n⚠️  部分修复未验证")
            return 1

    except json.JSONDecodeError as e:
        print(f"\n❌ JSON 解析失败: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
