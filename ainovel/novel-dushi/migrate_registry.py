#!/usr/bin/env python3
"""
Registry 迁移脚本
功能：从 Import Plan 导入事实到 Registry
"""

import json
import yaml
from pathlib import Path
from typing import Dict, List, Any

# 路径配置
PROJECT_ROOT = Path("/Users/angyang/Documents/xiaoshuo/AINovel/novel-dushi")
IMPORT_PLAN_PATH = PROJECT_ROOT / "workspace/outline-bootstrap/runs/urban-finance-20260908/import-plan.json"
REGISTRY_DIR = PROJECT_ROOT / "registry/facts"

def load_import_plan() -> Dict[str, Any]:
    """加载 Import Plan"""
    with open(IMPORT_PLAN_PATH) as f:
        return json.load(f)

def analyze_dependencies(items: List[Dict]) -> Dict[str, List[str]]:
    """分析依赖关系"""
    deps = {
        'Timeline': [],
        'Character': [],
        'WorldRule': [],
        'Event_arc': [],  # 卷级事件
        'Event_chapter': []  # 章节事件
    }

    for item in items:
        target_type = item.get('target_type')
        candidate_id = item.get('candidate_id')

        if target_type == 'Timeline':
            deps['Timeline'].append(candidate_id)
        elif target_type == 'Character':
            deps['Character'].append(candidate_id)
        elif target_type == 'WorldRule':
            deps['WorldRule'].append(candidate_id)
        elif target_type == 'Event':
            record = item.get('record', {})
            notes = record.get('notes', '')
            if '卷级事件' in notes:
                deps['Event_arc'].append(candidate_id)
            else:
                deps['Event_chapter'].append(candidate_id)

    return deps

def write_fact(facts_dir: str, fact_id: str, record: Dict) -> Path:
    """写入事实到 Registry"""
    target_dir = REGISTRY_DIR / facts_dir
    target_dir.mkdir(parents=True, exist_ok=True)

    output_path = target_dir / f"{fact_id}.yaml"

    with open(output_path, 'w', encoding='utf-8') as f:
        yaml.dump(record, f, allow_unicode=True, sort_keys=False)

    return output_path

def main():
    print("=" * 80)
    print("Registry 迁移脚本")
    print("=" * 80)

    # 1. 加载 Import Plan
    print("\n[1/6] 加载 Import Plan...")
    import_plan = load_import_plan()
    items = import_plan.get('items', [])
    print(f"  总事实数: {len(items)}")

    # 2. 分析依赖
    print("\n[2/6] 分析依赖关系...")
    deps = analyze_dependencies(items)
    for dep_type, ids in deps.items():
        print(f"  {dep_type}: {len(ids)} 个")

    # 3. 标记旧事件为 deprecated
    print("\n[3/6] 标记旧事件为 deprecated...")
    old_events = ['EVT-00001', 'EVT-00002', 'EVT-00003']
    for evt_id in old_events:
        evt_path = REGISTRY_DIR / 'events' / f'{evt_id}.yaml'
        if evt_path.exists():
            with open(evt_path) as f:
                evt_data = yaml.safe_load(f)

            evt_data['status'] = 'deprecated'
            evt_data['deprecated_at'] = '2026-09-08'
            evt_data['deprecated_reason'] = 'replaced by new outline event chain'

            with open(evt_path, 'w', encoding='utf-8') as f:
                yaml.dump(evt_data, f, allow_unicode=True, sort_keys=False)

            print(f"  ✅ {evt_id} 标记为 deprecated")

    # 4. 导入新事实（按依赖顺序）
    print("\n[4/6] 导入新事实...")
    imported = {'Timeline': 0, 'Character': 0, 'WorldRule': 0, 'Event': 0}

    # 4.1 导入 Timeline
    for item in items:
        if item.get('target_type') == 'Timeline':
            record = item.get('record', {})
            fact_id = item.get('candidate_id')
            facts_dir = item.get('facts_dir', 'timelines')

            output_path = write_fact(facts_dir, fact_id, record)
            imported['Timeline'] += 1
            print(f"  ✅ Timeline: {fact_id}")

    # 4.2 导入 Character
    for item in items:
        if item.get('target_type') == 'Character':
            record = item.get('record', {})
            fact_id = item.get('candidate_id')
            facts_dir = item.get('facts_dir', 'characters')

            output_path = write_fact(facts_dir, fact_id, record)
            imported['Character'] += 1
            print(f"  ✅ Character: {fact_id}")

    # 4.3 导入 WorldRule
    for item in items:
        if item.get('target_type') == 'WorldRule':
            record = item.get('record', {})
            fact_id = item.get('candidate_id')
            facts_dir = item.get('facts_dir', 'world_rules')

            output_path = write_fact(facts_dir, fact_id, record)
            imported['WorldRule'] += 1
            print(f"  ✅ WorldRule: {fact_id}")

    # 4.4 处理事件（修复卷级事件引用）
    print("\n  处理事件（修复引用）...")
    for item in items:
        if item.get('target_type') == 'Event':
            record = item.get('record', {}).copy()
            fact_id = item.get('candidate_id')
            facts_dir = item.get('facts_dir', 'events')
            notes = record.get('notes', '')

            # 检查是否为卷级事件
            is_arc = '卷级事件' in notes

            if is_arc:
                # 卷级事件：标记为 arc_metadata，不参与 Serial
                record['arc_metadata'] = True
                record['notes'] = record.get('notes', '') + ' [不参与章节生成]'
                print(f"  ⚠️  卷级: {fact_id} (标记为 arc_metadata)")
            else:
                # 章节事件：修复 causes 引用
                causes = record.get('causes', [])
                if causes and causes[0] in deps['Event_arc']:
                    # 移除对卷级事件的引用
                    record['causes'] = []
                    print(f"  🔧 修复: {fact_id} (移除卷级引用)")

            output_path = write_fact(facts_dir, fact_id, record)
            imported['Event'] += 1

    print(f"\n  导入统计:")
    for fact_type, count in imported.items():
        print(f"    {fact_type}: {count} 个")

    # 5. 验证导入
    print("\n[5/6] 验证导入结果...")
    events_dir = REGISTRY_DIR / 'events'
    all_events = list(events_dir.glob('*.yaml'))
    active_events = []
    deprecated_events = []
    arc_events = []

    for evt_path in all_events:
        with open(evt_path) as f:
            evt_data = yaml.safe_load(f)

        status = evt_data.get('status')
        is_arc = evt_data.get('arc_metadata', False)

        if status == 'deprecated':
            deprecated_events.append(evt_path.name)
        elif is_arc:
            arc_events.append(evt_path.name)
        elif status == 'active':
            active_events.append(evt_path.name)

    print(f"  总事件数: {len(all_events)}")
    print(f"  活跃章节事件: {len(active_events)}")
    print(f"  卷级事件: {len(arc_events)}")
    print(f"  已弃用: {len(deprecated_events)}")

    if len(active_events) == 30:
        print(f"\n  ✅ 验证通过：30个章节事件已导入")
    else:
        print(f"\n  ⚠️  警告：预期30个章节事件，实际{len(active_events)}个")

    print("\n[6/6] 完成")
    print("=" * 80)
    print("\n下一步：运行 plan_chapters() 验证")

if __name__ == '__main__':
    main()
