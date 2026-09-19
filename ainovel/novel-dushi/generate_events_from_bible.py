#!/usr/bin/env python3
"""
从 Story Bible 生成章节事件

这个脚本读取 BIBLE-00001.yaml，为每一章生成具体的 Event 文件
"""

import yaml
from pathlib import Path
from datetime import datetime
import hashlib

def load_story_bible(bible_path: Path) -> dict:
    """加载 Story Bible"""
    with open(bible_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def generate_event_from_chapter(chapter_data: dict, bible: dict) -> dict:
    """从章节数据生成 Event"""
    chapter_no = chapter_data['chapter']

    event = {
        'id': f'EVT-{90000 + chapter_no:05d}',
        'fact_version': 1,
        'certainty': 'canon',
        'status': 'active',
        'name': f"第{chapter_no}章：{chapter_data['title']}",
        'summary': chapter_data['title'],
        'timeline': 'TML-90001',
        'sequence_index': chapter_no,
        'date': chapter_data['date'],
        'location': chapter_data['location'],

        # 参与者
        'participants': [bible['protagonist']['id']],

        # 因果关系
        'causes': [f'EVT-{90000 + chapter_no - 1:05d}'] if chapter_no > 1 else [],
        'effects': [f'EVT-{90000 + chapter_no + 1:05d}'],

        # 详细描述
        'notes': f"""
章节事件：{chapter_data['title']}

## 设定
{yaml.dump(chapter_data.get('setup', []), allow_unicode=True)}

## 冲突
- 类型：{chapter_data['conflict']['type']}
- 对手：{chapter_data['conflict']['antagonist']}
- 压力：{chapter_data['conflict']['pressure']}

## 主角目标
{chapter_data['protagonist_goal']}

## 关键情节点
{yaml.dump(chapter_data.get('key_beats', []), allow_unicode=True)}

## 金手指使用
{yaml.dump(chapter_data.get('golden_finger_use', {}), allow_unicode=True) if chapter_data.get('golden_finger_use') else '本章无金手指使用'}

## 不可逆改变
{chapter_data['irreversible_change']}

## 结尾钩子
{chapter_data['end_hook']['content']}
{f"下一威胁：{chapter_data['end_hook']['next_threat']}" if 'next_threat' in chapter_data['end_hook'] else f"下一卷设定：{chapter_data['end_hook'].get('next_volume_setup', '完结')}"}

## 退出状态
{yaml.dump(chapter_data['exit_state'], allow_unicode=True)}
        """.strip(),

        # 元数据
        'duration': '1天',  # 默认1天
        'locations': [chapter_data['location']],
    }

    return event

def write_event(event: dict, output_dir: Path):
    """写入 Event 文件"""
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{event['id']}.yaml"

    with open(output_path, 'w', encoding='utf-8') as f:
        yaml.dump(event, f, allow_unicode=True, sort_keys=False)

    print(f"✓ 生成: {output_path}")

def main():
    """主函数"""
    project_root = Path(__file__).parent
    bible_path = project_root / 'registry/story-bible/BIBLE-00001.yaml'
    event_output_dir = project_root / 'registry/facts/events'

    print(f"加载 Story Bible: {bible_path}")

    if not bible_path.exists():
        print(f"❌ 错误: 找不到 Story Bible 文件")
        print(f"   当前工作目录: {Path.cwd()}")
        print(f"   脚本目录: {project_root}")
        print(f"   期望路径: {bible_path}")
        return

    bible = load_story_bible(bible_path)

    print(f"\n生成章节事件...")
    chapter_events = bible.get('chapter_events', [])

    if not chapter_events:
        print("⚠️  Story Bible 中没有 chapter_events")
        return

    for chapter_data in chapter_events:
        event = generate_event_from_chapter(chapter_data, bible)
        write_event(event, event_output_dir)

    print(f"\n✅ 完成：生成 {len(chapter_events)} 个章节事件")
    print(f"输出目录: {event_output_dir}")

if __name__ == '__main__':
    main()
