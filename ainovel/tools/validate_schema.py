#!/usr/bin/env python3
"""
Schema验证器 - 验证所有契约是否符合schema
"""

import json
import jsonschema
from pathlib import Path


def load_schema():
    """加载schema"""
    schema_file = Path('schemas/chapter_contract.schema.json')

    with open(schema_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def validate_contract(contract_file: Path, schema: dict) -> dict:
    """
    验证单个契约文件

    Returns:
        {
            "valid": bool,
            "errors": []
        }
    """
    with open(contract_file, 'r', encoding='utf-8') as f:
        contract = json.load(f)

    try:
        jsonschema.validate(instance=contract, schema=schema)
        return {"valid": True, "errors": []}
    except jsonschema.ValidationError as e:
        return {
            "valid": False,
            "errors": [
                {
                    "message": e.message,
                    "path": list(e.path),
                    "schema_path": list(e.schema_path)
                }
            ]
        }
    except jsonschema.SchemaError as e:
        return {
            "valid": False,
            "errors": [{"message": f"Schema错误: {e.message}"}]
        }


def main():
    """验证所有契约"""
    print("=" * 70)
    print("Schema验证器")
    print("=" * 70)
    print()

    # 加载schema
    print("加载schema...")
    schema = load_schema()
    print("✅ Schema已加载")
    print()

    # 查找所有契约
    contracts_dir = Path('contracts')
    contract_files = sorted(contracts_dir.glob('chapter_*_contract.json'))

    print(f"找到 {len(contract_files)} 个契约文件")
    print()

    # 验证每个契约
    results = []
    passed = 0
    failed = 0

    for contract_file in contract_files:
        chapter = int(contract_file.stem.split('_')[1])
        result = validate_contract(contract_file, schema)

        results.append({
            "chapter": chapter,
            "file": contract_file.name,
            "valid": result["valid"],
            "errors": result["errors"]
        })

        if result["valid"]:
            passed += 1
            print(f"✅ Ch{chapter:03d}: 通过")
        else:
            failed += 1
            print(f"❌ Ch{chapter:03d}: 失败")
            for error in result["errors"]:
                print(f"   错误: {error['message']}")
                if error.get('path'):
                    print(f"   路径: {'.'.join(map(str, error['path']))}")

    print()
    print("=" * 70)
    print("验证总结")
    print("=" * 70)
    print()
    print(f"总计: {len(contract_files)} 个契约")
    print(f"通过: {passed} 个 ({passed/len(contract_files)*100:.1f}%)")
    print(f"失败: {failed} 个 ({failed/len(contract_files)*100:.1f}%)")
    print()

    # 保存报告
    report = {
        "total": len(contract_files),
        "passed": passed,
        "failed": failed,
        "results": results
    }

    report_file = Path('reports/schema_validation.json')
    report_file.parent.mkdir(exist_ok=True)

    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"📁 报告已保存: {report_file}")
    print()

    if failed > 0:
        print("⚠️  存在不合规契约，请修复后再继续")
        return 1
    else:
        print("✅ 所有契约符合schema")
        return 0


if __name__ == '__main__':
    exit(main())
