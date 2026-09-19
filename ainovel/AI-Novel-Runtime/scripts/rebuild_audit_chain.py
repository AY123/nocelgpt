#!/usr/bin/env python3
"""
重建审计链 - A.1 统一审计口径

从实际产物（drafts、checkpoints、run manifests）重建完整的审计链，
解决 evidence ledger 与实际文件不一致的问题。
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime


def compute_file_hash(file_path: Path) -> str:
    """计算文件的 SHA-256 hash"""
    if not file_path.exists():
        return "missing"

    with open(file_path, 'rb') as f:
        return f"sha256:{hashlib.sha256(f.read()).hexdigest()}"


def extract_chapter_info(draft_path: Path) -> Optional[Dict]:
    """从 draft 文件提取章节信息"""
    try:
        with open(draft_path, 'r', encoding='utf-8') as f:
            envelope = json.load(f)

        # 新的 envelope 结构：draft 在内层
        draft = envelope.get("draft", {})

        # 从文件名提取 task_id
        task_id = draft_path.stem  # TASK-00001

        # 尝试从 task_id 推导 chapter_index
        try:
            chapter_index = int(task_id.split('-')[1])
        except:
            chapter_index = None

        # 提取核心信息
        return {
            "chapter_index": chapter_index,
            "task_id": task_id,
            "event_id": envelope.get("event_id"),  # 可能在顶层
            "file_hash": compute_file_hash(draft_path),
            "content_hash": draft.get("content_hash"),
            "body_length": len(draft.get("body", "")),
            "produced_by": draft.get("produced_by", {}),
            "director": envelope.get("director", {}),
            "ok": True,
            "path": str(draft_path.relative_to(draft_path.parents[3]))
        }
    except Exception as e:
        return {
            "path": str(draft_path),
            "ok": False,
            "error": str(e)
        }


def scan_checkpoints(checkpoint_dir: Path) -> Dict[int, Dict]:
    """扫描所有 checkpoint 文件"""
    checkpoints = {}

    if not checkpoint_dir.exists():
        return checkpoints

    for cp_file in sorted(checkpoint_dir.glob("cp-*.json")):
        try:
            chapter_num = int(cp_file.stem.split('-')[1])
            with open(cp_file, 'r', encoding='utf-8') as f:
                cp_data = json.load(f)

            checkpoints[chapter_num] = {
                "chapter_index": chapter_num,
                "path": str(cp_file.relative_to(cp_file.parents[3])),
                "file_hash": compute_file_hash(cp_file),
                "state_hash": cp_data.get("state_hash"),
                "present": True
            }
        except Exception as e:
            print(f"Warning: Failed to read checkpoint {cp_file}: {e}")

    return checkpoints


def rebuild_evidence_ledger(novel_dir: Path) -> Dict:
    """重建完整的 evidence ledger"""

    drafts_dir = novel_dir / "registry" / "derived" / "drafts"
    checkpoints_dir = novel_dir / "registry" / "derived" / "serial-checkpoints"

    print(f"扫描 drafts: {drafts_dir}")
    print(f"扫描 checkpoints: {checkpoints_dir}")

    # 扫描所有 draft 文件
    chapters = []
    task_files = sorted(drafts_dir.glob("TASK-*.json"))

    print(f"\n找到 {len(task_files)} 个 draft 文件")

    for draft_file in task_files:
        info = extract_chapter_info(draft_file)
        if info:
            chapters.append(info)

    # 扫描所有 checkpoint
    checkpoints = scan_checkpoints(checkpoints_dir)
    print(f"找到 {len(checkpoints)} 个 checkpoint 文件")

    # 按章节索引排序
    chapters_ok = [c for c in chapters if c.get("ok")]

    # 只保留有有效 chapter_index 的章节
    chapters_ok = [c for c in chapters_ok if c.get("chapter_index") is not None]
    chapters_ok.sort(key=lambda x: x.get("chapter_index", 999))

    chapters_failed = [c for c in chapters if not c.get("ok")]

    # 构建统计
    chapter_indices = [c.get("chapter_index") for c in chapters_ok if c.get("chapter_index") is not None]

    stats = {
        "total_draft_files": len(task_files),
        "chapters_parsed": len(chapters_ok),
        "chapters_failed": len(chapters_failed),
        "chapter_range": f"{min(chapter_indices)}-{max(chapter_indices)}" if chapter_indices else "none",
        "checkpoints_found": len(checkpoints),
        "checkpoint_indices": sorted(checkpoints.keys())
    }

    # 检查连续性
    contiguous = True
    gaps = []
    if chapter_indices:
        expected = set(range(min(chapter_indices), max(chapter_indices) + 1))
        actual = set(chapter_indices)
        gaps = sorted(expected - actual)
        contiguous = len(gaps) == 0

    stats["contiguous"] = contiguous
    stats["gaps"] = gaps

    # 构建 evidence ledger
    ledger = {
        "kind": "chapter_evidence_ledger",
        "project_id": novel_dir.name,
        "rebuilt_at": datetime.now().isoformat(),
        "version": "2.0-rebuilt",
        "statistics": stats,
        "chapters": chapters_ok,
        "failed_parses": chapters_failed,
        "checkpoints": checkpoints
    }

    return ledger


def validate_evidence_ledger(ledger: Dict) -> Dict:
    """验证 evidence ledger 的完整性"""

    stats = ledger["statistics"]
    chapters = ledger["chapters"]
    checkpoints = ledger["checkpoints"]

    checks = []

    # Check 1: 连续性
    checks.append({
        "check_id": "chapter_contiguity",
        "passed": stats["contiguous"],
        "detail": f"range={stats['chapter_range']}, gaps={stats['gaps']}"
    })

    # Check 2: draft 数量
    parsed = stats["chapters_parsed"]
    checks.append({
        "check_id": "all_drafts_parsed",
        "passed": stats["chapters_failed"] == 0,
        "detail": f"parsed={parsed}, failed={stats['chapters_failed']}"
    })

    # Check 3: checkpoint 对齐
    expected_checkpoints = set(range(10, parsed + 1, 10))
    actual_checkpoints = set(checkpoints.keys())
    checkpoint_aligned = expected_checkpoints == actual_checkpoints

    checks.append({
        "check_id": "checkpoint_alignment",
        "passed": checkpoint_aligned,
        "detail": f"expected={sorted(expected_checkpoints)}, actual={sorted(actual_checkpoints)}"
    })

    # Check 4: hash 完整性
    hash_ok = all(c.get("file_hash") and c["file_hash"] != "missing" for c in chapters)
    checks.append({
        "check_id": "hash_integrity",
        "passed": hash_ok,
        "detail": f"all_hashes_present={hash_ok}"
    })

    all_passed = all(c["passed"] for c in checks)

    return {
        "kind": "evidence_ledger_validation",
        "validated_at": datetime.now().isoformat(),
        "all_checks_passed": all_passed,
        "checks": checks,
        "summary": {
            "total_chapters": parsed,
            "contiguous": stats["contiguous"],
            "checkpoints": len(checkpoints),
            "status": "valid" if all_passed else "has_issues"
        }
    }


def main():
    """主函数"""

    # 项目根目录
    script_dir = Path(__file__).parent
    runtime_dir = script_dir.parent
    project_root = runtime_dir.parent
    novel_dir = project_root / "novel-lingse"

    print("=" * 80)
    print("A.1 审计链重建工具")
    print("=" * 80)
    print(f"\n项目目录: {novel_dir}")

    if not novel_dir.exists():
        print(f"ERROR: 项目目录不存在: {novel_dir}")
        return 1

    # 重建 evidence ledger
    print("\n[1/3] 重建 Evidence Ledger...")
    ledger = rebuild_evidence_ledger(novel_dir)

    # 验证
    print("\n[2/3] 验证 Evidence Ledger...")
    validation = validate_evidence_ledger(ledger)

    # 输出结果
    output_dir = novel_dir / "analysis"
    output_dir.mkdir(exist_ok=True, parents=True)

    ledger_file = output_dir / "chapter-evidence-ledger-rebuilt.json"
    validation_file = output_dir / "evidence-validation-report.json"

    print(f"\n[3/3] 写入结果...")

    with open(ledger_file, 'w', encoding='utf-8') as f:
        json.dump(ledger, f, indent=2, ensure_ascii=False)
    print(f"✓ Evidence Ledger: {ledger_file}")

    with open(validation_file, 'w', encoding='utf-8') as f:
        json.dump(validation, f, indent=2, ensure_ascii=False)
    print(f"✓ Validation Report: {validation_file}")

    # 打印摘要
    print("\n" + "=" * 80)
    print("审计摘要")
    print("=" * 80)

    stats = ledger["statistics"]
    print(f"\n总计:")
    print(f"  - Draft 文件: {stats['total_draft_files']}")
    print(f"  - 解析成功: {stats['chapters_parsed']}")
    print(f"  - 解析失败: {stats['chapters_failed']}")
    print(f"  - 章节范围: {stats['chapter_range']}")
    print(f"  - Checkpoints: {stats['checkpoints_found']} @ {stats['checkpoint_indices']}")

    print(f"\n连续性:")
    if stats['contiguous']:
        print(f"  ✓ 章节连续，无跳跃")
    else:
        print(f"  ✗ 发现 {len(stats['gaps'])} 个缺口: {stats['gaps']}")

    print(f"\n验证结果:")
    for check in validation["checks"]:
        status = "✓" if check["passed"] else "✗"
        print(f"  {status} {check['check_id']}: {check['detail']}")

    print(f"\n最终状态: {validation['summary']['status'].upper()}")

    if validation["all_checks_passed"]:
        print("\n✓ 审计链已重建并验证通过")
        return 0
    else:
        print("\n⚠ 审计链存在问题，需要进一步修复")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
