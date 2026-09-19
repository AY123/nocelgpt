#!/usr/bin/env python3
"""create_events_31_100.py — 基于 Outline 创建 Events 31-100

为每个章节创建对应的 Event，然后 mint 到 registry
"""
import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime.memory.registry import Registry
from runtime.memory.mint import mint_candidate

def main():
    print("=== 创建 Events 31-100 ===\n")

    # 加载 registry
    novel_dir = Path(__file__).parent.parent.parent / "novel-lingse"
    registry = Registry(novel_dir / "registry")

    # 加载 outline
    outline_path = novel_dir / "registry/derived/outline/OUTLINE-00001.json"
    outline = json.loads(outline_path.read_text())
    chapters = outline.get("chapters", [])

    print(f"Outline 包含 {len(chapters)} 章")

    # 检查现有 Events
    existing_events = list((novel_dir / "registry/facts/events").glob("EVT-*.yaml"))
    print(f"现有 Events: {len(existing_events)} 个\n")

    # 为 Chapter 31-100 创建 Events
    chapters_31_100 = [ch for ch in chapters if ch.get('chapter_no', 0) >= 31]
    print(f"需要创建 Events: {len(chapters_31_100)} 个\n")

    created_count = 0
    skipped_count = 0

    for chapter in chapters_31_100:
        ch_no = chapter.get('chapter_no')

        # 构造 Event 候选
        candidate = {
            "candidate_id": f"CAND-CH{ch_no:03d}",
            "classification": "new",
            "confidence": 1.0,
            "target_type": "Event",
            "field": "name",
            "extracted_value": f"第{ch_no}章事件",
            "existing_value": None,
            "evidence": f"Chapter {ch_no} from outline",
            "reason": "created from outline for chapter planning"
        }

        # 构造完整的 Event 数据（用于初始化）
        event_data = {
            "name": f"第{ch_no}章事件",
            "summary": chapter.get('goal', ''),
            "participants": [],  # 将在生成时填充
            "timeline": {
                "start": None,
                "end": None
            },
            "statement": chapter.get('conflict', '')[:200]  # 截取前200字符
        }

        # Mint（这会创建 EVT-000XX）
        try:
            receipt = mint_candidate(
                registry=registry,
                candidate=candidate,
                authority="human",
                gating=False,
                initial_facts=event_data  # 传入初始数据
            )

            if receipt.get("ok"):
                entity_id = receipt.get("entity_id")
                print(f"✓ Chapter {ch_no:3d} → {entity_id}")
                created_count += 1
            else:
                reason = receipt.get("reason", "unknown")
                print(f"✗ Chapter {ch_no:3d}: {reason}")
                skipped_count += 1

        except Exception as e:
            print(f"✗ Chapter {ch_no:3d}: {e}")
            skipped_count += 1

    print(f"\n=== 完成 ===")
    print(f"成功创建: {created_count}")
    print(f"跳过: {skipped_count}")

    # 验证最终 Events 数量
    final_events = list((novel_dir / "registry/facts/events").glob("EVT-*.yaml"))
    print(f"最终 Events 总数: {len(final_events)}")

if __name__ == "__main__":
    main()
