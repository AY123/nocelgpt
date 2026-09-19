#!/usr/bin/env python3
"""
伏笔追踪工具
自动追踪伏笔的埋设、提醒和回收状态
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any


def load_promises() -> Dict:
    """加载伏笔管理表"""
    promise_file = Path(__file__).parent.parent / 'knowledge-base' / 'plot' / '伏笔管理表.json'

    if not promise_file.exists():
        print(f"❌ 错误: 未找到伏笔管理表 {promise_file}")
        return {}

    with open(promise_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def check_promise_status(promise: Dict, current_chapter: int) -> Dict:
    """
    检查伏笔当前状态
    """
    promise_id = promise['promise_id']
    埋设章节 = promise['埋设章节']
    预计回收章节 = promise['预计回收章节']
    已提醒章节 = promise.get('已提醒章节', [])
    下次提醒章节 = promise.get('下次提醒章节')
    检查点 = promise.get('检查点', [])

    status = {
        'promise_id': promise_id,
        'priority': promise['priority'],
        'current_status': '正常',
        'alerts': []
    }

    # 检查1: 是否已埋设
    if current_chapter < 埋设章节:
        status['current_status'] = '未埋设'
        return status

    # 检查2: 是否已回收
    if current_chapter >= 预计回收章节:
        status['current_status'] = '应该已回收'
        status['alerts'].append({
            'type': 'should_be_collected',
            'severity': 'high',
            'message': f'应在Ch{预计回收章节}回收，当前Ch{current_chapter}'
        })
        return status

    # 检查3: 提醒频率
    if 已提醒章节:
        last_remind = max(已提醒章节)
        chapters_since_remind = current_chapter - last_remind

        # 超过30章未提醒
        if chapters_since_remind > 30:
            status['alerts'].append({
                'type': 'long_time_no_remind',
                'severity': 'medium',
                'message': f'距上次提醒已{chapters_since_remind}章（Ch{last_remind}）'
            })

    # 检查4: 下次提醒点
    if 下次提醒章节 and current_chapter >= 下次提醒章节:
        status['alerts'].append({
            'type': 'remind_due',
            'severity': 'info',
            'message': f'应在Ch{下次提醒章节}提醒，当前Ch{current_chapter}'
        })

    # 检查5: 检查点
    for checkpoint in 检查点:
        cp_chapter = checkpoint.get('chapter')
        cp_status = checkpoint.get('status', 'pending')

        if cp_chapter and current_chapter >= cp_chapter and cp_status == 'pending':
            status['alerts'].append({
                'type': 'checkpoint_pending',
                'severity': 'info',
                'message': f'检查点Ch{cp_chapter}待处理'
            })

    return status


def generate_timeline(promises: List[Dict], max_chapter: int = 100) -> Dict:
    """
    生成伏笔时间线
    """
    timeline = {}

    for ch in range(1, max_chapter + 1):
        timeline[ch] = {
            'should_remind': [],
            'should_collect': [],
            'checkpoints': []
        }

    for promise in promises:
        埋设 = promise['埋设章节']
        回收 = promise['预计回收章节']
        下次提醒 = promise.get('下次提醒章节')
        检查点列表 = promise.get('检查点', [])

        # 埋设点
        if 埋设 <= max_chapter:
            timeline[埋设].setdefault('buried', []).append(promise['promise_id'])

        # 回收点
        if 回收 <= max_chapter:
            timeline[回收]['should_collect'].append({
                'promise_id': promise['promise_id'],
                'priority': promise['priority']
            })

        # 提醒点
        if 下次提醒 and 下次提醒 <= max_chapter:
            timeline[下次提醒]['should_remind'].append({
                'promise_id': promise['promise_id'],
                '提醒方式': promise.get('提醒方式', '待定')
            })

        # 检查点
        for cp in 检查点列表:
            cp_ch = cp.get('chapter')
            if cp_ch and cp_ch <= max_chapter:
                timeline[cp_ch]['checkpoints'].append({
                    'promise_id': promise['promise_id'],
                    'requirement': cp.get('requirement', '')
                })

    return timeline


def main():
    """主函数"""
    print("=" * 70)
    print("伏笔追踪工具")
    print("=" * 70)
    print()

    # 加载伏笔管理表
    data = load_promises()

    if not data:
        return

    promises = data.get('promises', [])
    回收时间表 = data.get('回收时间表', {})

    print(f"✅ 已加载 {len(promises)} 个伏笔")
    print()

    # 当前进度（假设检查到Ch70）
    current_chapter = 70

    # 检查每个伏笔状态
    print("=" * 70)
    print(f"伏笔状态检查（当前进度：Ch{current_chapter}）")
    print("=" * 70)
    print()

    all_alerts = []

    for promise in promises:
        status = check_promise_status(promise, current_chapter)

        if status['alerts']:
            all_alerts.extend([
                {**alert, 'promise_id': promise['promise_id'],
                 'priority': promise['priority']}
                for alert in status['alerts']
            ])

    # 按严重程度分类
    by_severity = {}
    for alert in all_alerts:
        severity = alert['severity']
        by_severity.setdefault(severity, []).append(alert)

    if not all_alerts:
        print("✅ 所有伏笔状态正常")
        print()
    else:
        print(f"发现 {len(all_alerts)} 个提醒")
        print()

        for severity in ['high', 'medium', 'info']:
            if severity not in by_severity:
                continue

            alerts = by_severity[severity]
            severity_name = {'high': '高优先级', 'medium': '中优先级', 'info': '信息'}.get(severity)

            print(f"{severity_name}: {len(alerts)}个")
            print("-" * 70)

            for alert in alerts[:5]:
                print(f"[{alert['promise_id']}] {alert['message']}")

            if len(alerts) > 5:
                print(f"... 还有 {len(alerts) - 5} 个")

            print()

    # 生成时间线
    print("=" * 70)
    print("伏笔时间线（未来30章）")
    print("=" * 70)
    print()

    timeline = generate_timeline(promises, 100)

    for ch in range(current_chapter + 1, min(current_chapter + 31, 101)):
        events = timeline.get(ch, {})

        has_events = (events.get('should_remind') or
                     events.get('should_collect') or
                     events.get('checkpoints'))

        if not has_events:
            continue

        print(f"Ch{ch}:")

        if events.get('should_remind'):
            print("  🔔 提醒:")
            for item in events['should_remind']:
                print(f"     - {item['promise_id']}: {item['提醒方式']}")

        if events.get('should_collect'):
            print("  ✅ 回收:")
            for item in events['should_collect']:
                print(f"     - {item['promise_id']} ({item['priority']})")

        if events.get('checkpoints'):
            print("  📍 检查点:")
            for item in events['checkpoints']:
                print(f"     - {item['promise_id']}: {item['requirement']}")

        print()

    # 保存报告
    output_dir = Path(__file__).parent.parent / 'reports'
    output_dir.mkdir(exist_ok=True)

    report = {
        'current_chapter': current_chapter,
        'total_promises': len(promises),
        'alerts': all_alerts,
        'by_severity': {k: len(v) for k, v in by_severity.items()},
        'timeline': {
            str(k): v for k, v in timeline.items()
            if any([v.get('should_remind'), v.get('should_collect'), v.get('checkpoints')])
        }
    }

    report_file = output_dir / 'promise_tracking.json'

    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("=" * 70)
    print(f"📁 报告已保存: {report_file}")
    print("=" * 70)
    print()


if __name__ == '__main__':
    main()
