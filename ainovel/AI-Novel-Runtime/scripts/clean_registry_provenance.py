#!/usr/bin/env python3
"""
P0 整改：清理 Registry provenance 中的奇幻遗留引用

清理内容：
1. 删除 MAG-* (magic) 相关的 mint-ledger 条目
2. 删除 genesis-receipts 中的 MAG 引用
3. 建议：完整重新生成项目
"""
import sys
from pathlib import Path
import yaml
import json

def clean_mint_ledger(project_path: Path):
    """清理 mint-ledger.yaml 中的 MAG 条目"""
    ledger_path = project_path / "registry" / "_meta" / "mint-ledger.yaml"

    if not ledger_path.exists():
        print(f"⚠️  {ledger_path} 不存在，跳过")
        return

    with open(ledger_path, 'r', encoding='utf-8') as f:
        ledger = yaml.safe_load(f)

    original_count = len(ledger.get("entries", []))

    # 过滤掉 MAG-* 条目
    ledger["entries"] = [
        entry for entry in ledger.get("entries", [])
        if not entry.get("id", "").startswith("MAG-")
    ]

    removed = original_count - len(ledger["entries"])

    if removed > 0:
        with open(ledger_path, 'w', encoding='utf-8') as f:
            yaml.dump(ledger, f, allow_unicode=True, sort_keys=False)
        print(f"✅ 从 mint-ledger.yaml 删除 {removed} 个 MAG 条目")
    else:
        print(f"✅ mint-ledger.yaml 无 MAG 条目")


def clean_genesis_receipts(project_path: Path):
    """清理 genesis-receipts 中的 MAG 引用（警告而不删除，因为这些是审计记录）"""
    receipts_dir = project_path / "registry" / "derived" / "genesis-receipts"

    if not receipts_dir.exists():
        print(f"⚠️  {receipts_dir} 不存在，跳过")
        return

    receipt_files = list(receipts_dir.glob("GEN-*.json"))

    if not receipt_files:
        print(f"✅ 无 genesis-receipts")
        return

    has_mag = False
    for receipt_file in receipt_files:
        with open(receipt_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if "MAG-" in content:
                has_mag = True
                break

    if has_mag:
        print(f"⚠️  genesis-receipts 包含 MAG 引用（{len(receipt_files)} 个文件）")
        print(f"    建议：完整重新生成项目以清理历史记录")
    else:
        print(f"✅ genesis-receipts 无 MAG 引用")


def main():
    if len(sys.argv) < 2:
        print("用法: python3 clean_registry_provenance.py <project_path>")
        print("示例: python3 clean_registry_provenance.py ../novel-dushi")
        sys.exit(1)

    project_path = Path(sys.argv[1]).resolve()

    if not project_path.exists():
        print(f"❌ 项目路径不存在: {project_path}")
        sys.exit(1)

    print(f"清理项目: {project_path.name}")
    print("=" * 60)

    clean_mint_ledger(project_path)
    clean_genesis_receipts(project_path)

    print("\n" + "=" * 60)
    print("清理完成")
    print("\n建议：")
    print("1. 检查 registry/facts/world_rules/ 是否有遗留 MAG-*.yaml")
    print("2. 如果需要彻底清理，建议重新运行 genesis 生成项目")
    print("3. 验证生成的 outline 包含 genre_profile_id 字段")


if __name__ == "__main__":
    main()
