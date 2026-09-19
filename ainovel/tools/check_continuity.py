#!/usr/bin/env python3
"""
连续性检查工具
检查相邻章节的连续性问题
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any


def load_bridges(file_path: str) -> Dict[int, Dict]:
    """加载bridge数据"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 转换key为int
    return {int(k): v for k, v in data.items()}


def check_location_continuity(prev_ch: Dict, next_ch: Dict, prev_num: int, next_num: int) -> List[Dict]:
    """检查地点连续性"""
    issues = []

    prev_loc = prev_ch.get('location', '')
    next_loc = next_ch.get('location', '')

    if not prev_loc or not next_loc:
        return issues

    # 简单检查：地点名称是否有明显不同
    # 这里简化处理，实际可以更复杂
    if prev_loc != next_loc and '未提取' not in prev_loc and '未提取' not in next_loc:
        issues.append({
            'type': 'location_jump',
            'severity': 'medium',
            'chapters': f'Ch{prev_num}→Ch{next_num}',
            'prev_location': prev_loc[:50],
            'next_location': next_loc[:50],
            'description': f'地点从"{prev_loc[:30]}"跳转到"{next_loc[:30]}"',
            'suggestion': '检查是否需要添加场景转换描述'
        })

    return issues


def check_time_continuity(prev_ch: Dict, next_ch: Dict, prev_num: int, next_num: int) -> List[Dict]:
    """检查时间连续性"""
    issues = []

    prev_time = prev_ch.get('time', '')
    next_time = next_ch.get('time', '')

    if not prev_time or not next_time:
        return issues

    # 检查是否有明显的时间倒退关键词
    backward_keywords = ['前', '之前', '早']
    if any(kw in next_time for kw in backward_keywords):
        if '回忆' not in next_time and '闪回' not in next_time:
            issues.append({
                'type': 'time_backward',
                'severity': 'high',
                'chapters': f'Ch{prev_num}→Ch{next_num}',
                'prev_time': prev_time,
                'next_time': next_time,
                'description': f'时间可能倒退："{next_time}"',
                'suggestion': '检查时间线是否合理'
            })

    return issues


def check_character_continuity(prev_ch: Dict, next_ch: Dict, prev_num: int, next_num: int) -> List[Dict]:
    """检查人物连续性"""
    issues = []

    prev_chars = set(prev_ch.get('characters_present', []))
    next_chars = set(next_ch.get('characters_present', []))

    if not prev_chars or not next_chars:
        return issues

    # 检查消失的关键人物
    missing = prev_chars - next_chars
    if missing:
        # 只报告可能的主要人物消失
        main_chars = ['段奕尘', '镜见川', '二叔', '荧惑']
        missing_main = [c for c in missing if any(mc in str(c) for mc in main_chars)]

        if missing_main:
            issues.append({
                'type': 'character_disappear',
                'severity': 'low',
                'chapters': f'Ch{prev_num}→Ch{next_num}',
                'missing_characters': missing_main,
                'description': f'人物消失：{", ".join(missing_main)}',
                'suggestion': '检查是否有退场说明'
            })

    return issues


def check_unfinished_action(prev_ch: Dict, next_ch: Dict, prev_num: int, next_num: int) -> List[Dict]:
    """检查未完成动作是否被消费"""
    issues = []

    unfinished = prev_ch.get('unfinished_action', '')

    if not unfinished or unfinished == '待分析':
        return issues

    # 简单检查：未完成动作是否在下一章提及
    # 这里简化处理，实际需要读取下一章正文
    if len(unfinished) > 20:
        issues.append({
            'type': 'unfinished_action_check',
            'severity': 'info',
            'chapters': f'Ch{prev_num}→Ch{next_num}',
            'unfinished_action': unfinished[:100],
            'description': '存在未完成动作',
            'suggestion': '需要在下一章中消费或延续此动作'
        })

    return issues


def check_hook_promise(prev_ch: Dict, next_ch: Dict, prev_num: int, next_num: int) -> List[Dict]:
    """检查钩子承诺"""
    issues = []

    hook = prev_ch.get('hook_promise', '')

    if not hook or hook == '待分析':
        return issues

    # 如果有钩子，标记需要在下一章兑现
    if len(hook) > 20:
        issues.append({
            'type': 'hook_promise',
            'severity': 'info',
            'chapters': f'Ch{prev_num}→Ch{next_num}',
            'hook_promise': hook[:100],
            'description': '章末有钩子承诺',
            'suggestion': '需要在Ch' + str(next_num) + '前20%段落中回应'
        })

    return issues


def check_continuity(prev_num: int, prev_ch: Dict, next_num: int, next_ch: Dict) -> List[Dict]:
    """
    检查两个相邻章节的连续性
    """
    all_issues = []

    # 1. 地点连续性
    all_issues.extend(check_location_continuity(prev_ch, next_ch, prev_num, next_num))

    # 2. 时间连续性
    all_issues.extend(check_time_continuity(prev_ch, next_ch, prev_num, next_num))

    # 3. 人物连续性
    all_issues.extend(check_character_continuity(prev_ch, next_ch, prev_num, next_num))

    # 4. 未完成动作
    all_issues.extend(check_unfinished_action(prev_ch, next_ch, prev_num, next_num))

    # 5. 钩子承诺
    all_issues.extend(check_hook_promise(prev_ch, next_ch, prev_num, next_num))

    return all_issues


def main():
    """主函数"""
    print("=" * 70)
    print("连续性检查工具")
    print("=" * 70)
    print()

    # 读取bridge数据
    bridge_file = Path(__file__).parent.parent / 'data' / 'chapter_bridges.json'

    if not bridge_file.exists():
        print(f"❌ 错误: 未找到文件 {bridge_file}")
        return

    print(f"读取数据: {bridge_file.name}")
    bridges = load_bridges(str(bridge_file))

    print(f"✅ 已加载 {len(bridges)} 章数据")
    print()

    # 检查所有相邻章节
    all_issues = []
    checked_pairs = 0

    print("开始检查相邻章节连续性...")
    print()

    for ch_num in sorted(bridges.keys()):
        next_num = ch_num + 1

        if next_num not in bridges:
            continue

        issues = check_continuity(ch_num, bridges[ch_num], next_num, bridges[next_num])
        all_issues.extend(issues)
        checked_pairs += 1

    print(f"✅ 已检查 {checked_pairs} 对相邻章节")
    print()

    # 统计问题
    print("=" * 70)
    print("检查结果")
    print("=" * 70)
    print()

    if not all_issues:
        print("✅ 未发现明显连续性问题")
        print()
        return

    # 按严重程度分类
    by_severity = {}
    for issue in all_issues:
        severity = issue['severity']
        by_severity.setdefault(severity, []).append(issue)

    print(f"共发现 {len(all_issues)} 个问题")
    print()

    for severity in ['high', 'medium', 'low', 'info']:
        if severity not in by_severity:
            continue

        issues = by_severity[severity]
        severity_name = {
            'high': '高',
            'medium': '中',
            'low': '低',
            'info': '信息'
        }[severity]

        print(f"{severity_name}级别: {len(issues)}个")
        print("-" * 70)

        for i, issue in enumerate(issues[:10], 1):  # 只显示前10个
            print(f"{i}. [{issue['chapters']}] {issue['type']}")
            print(f"   {issue['description']}")
            print(f"   建议: {issue['suggestion']}")
            print()

        if len(issues) > 10:
            print(f"   ... 还有 {len(issues) - 10} 个同类问题")
            print()

    # 保存报告
    output_dir = Path(__file__).parent.parent / 'reports'
    output_dir.mkdir(exist_ok=True)

    report_file = output_dir / 'continuity_issues.json'

    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump({
            'total_issues': len(all_issues),
            'checked_pairs': checked_pairs,
            'by_severity': {k: len(v) for k, v in by_severity.items()},
            'issues': all_issues
        }, f, ensure_ascii=False, indent=2)

    print("=" * 70)
    print(f"📁 报告已保存: {report_file}")
    print("=" * 70)
    print()


if __name__ == '__main__':
    main()
