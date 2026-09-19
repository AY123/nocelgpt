#!/usr/bin/env python3
"""
验证 Story Bible 中的章节事件链

检查：
1. 30章是否完整
2. 时间线是否连续
3. 钩子是否被消费
4. 地点是否一致
5. 人物是否连贯
"""

import yaml
from pathlib import Path
from datetime import datetime
from typing import List, Dict

def load_story_bible(bible_path: Path) -> dict:
    """加载 Story Bible"""
    with open(bible_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def validate_completeness(bible: dict) -> List[str]:
    """验证完整性"""
    errors = []
    chapter_events = bible.get('chapter_events', [])

    if len(chapter_events) != 30:
        errors.append(f"❌ 章节数量不足：{len(chapter_events)}/30")
    else:
        print(f"✓ 章节数量正确：30章")

    # 检查章节编号连续性
    chapter_numbers = [ch['chapter'] for ch in chapter_events]
    expected = list(range(1, 31))
    if chapter_numbers != expected:
        missing = set(expected) - set(chapter_numbers)
        if missing:
            errors.append(f"❌ 缺少章节：{missing}")
    else:
        print(f"✓ 章节编号连续：1-30")

    return errors

def validate_timeline(bible: dict) -> List[str]:
    """验证时间线"""
    errors = []
    chapter_events = bible.get('chapter_events', [])

    prev_date = None
    for ch in chapter_events:
        date_str = ch.get('date')
        if not date_str:
            errors.append(f"❌ 第{ch['chapter']}章缺少日期")
            continue

        try:
            curr_date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            errors.append(f"❌ 第{ch['chapter']}章日期格式错误：{date_str}")
            continue

        if prev_date and curr_date < prev_date:
            errors.append(f"❌ 第{ch['chapter']}章时间倒流：{prev_date.date()} → {curr_date.date()}")

        prev_date = curr_date

    if not errors:
        start_date = chapter_events[0]['date']
        end_date = chapter_events[-1]['date']
        print(f"✓ 时间线连续：{start_date} → {end_date}")

    return errors

def validate_hooks(bible: dict) -> List[str]:
    """验证钩子消费"""
    errors = []
    warnings = []
    chapter_events = bible.get('chapter_events', [])

    for i, ch in enumerate(chapter_events):
        if i == 0:
            continue  # 第一章没有前置钩子

        prev_ch = chapter_events[i - 1]

        # 检查是否有 entry_hook_resolution
        if 'entry_hook_resolution' not in ch:
            warnings.append(f"⚠️  第{ch['chapter']}章缺少 entry_hook_resolution")

        # 检查上一章是否有 end_hook
        if 'end_hook' not in prev_ch:
            errors.append(f"❌ 第{prev_ch['chapter']}章缺少 end_hook")

    if not errors:
        print(f"✓ 所有章节都有 end_hook")

    if not warnings:
        print(f"✓ 所有章节都有 entry_hook_resolution")
    else:
        for w in warnings:
            print(w)

    return errors

def validate_locations(bible: dict) -> List[str]:
    """验证地点一致性"""
    errors = []
    chapter_events = bible.get('chapter_events', [])
    known_locations = {loc['name'] for loc in bible.get('world', {}).get('key_locations', [])}

    # 允许的常见地点词汇
    common_places = {'办公室', '会所', '会议室', '安全屋', '机场', '咖啡厅', '商业区', '金融监管局', '检察院', '科技园区'}

    for ch in chapter_events:
        location = ch.get('location', '')
        # 检查是否包含已知地点或常见地点
        found = False
        for known in known_locations:
            if known in location:
                found = True
                break

        if not found:
            # 检查常见地点
            for common in common_places:
                if common in location:
                    found = True
                    break

        if not found and location:
            # 检查是否是城市名
            if any(city in location for city in ['江城', '上海', '北京', '深圳', '香港']):
                found = True

        if not found and location:
            errors.append(f"⚠️  第{ch['chapter']}章地点未授权：{location}")

    if not errors:
        print(f"✓ 所有地点都在授权范围内")

    return errors

def validate_characters(bible: dict) -> List[str]:
    """验证人物一致性"""
    errors = []
    chapter_events = bible.get('chapter_events', [])
    protagonist_name = bible.get('protagonist', {}).get('name', '陈默')

    # 检查主角名字
    for ch in chapter_events:
        title = ch.get('title', '')
        setup = str(ch.get('setup', []))
        beats = str(ch.get('key_beats', []))

        # 简单检查：标题、设定、情节点中不应出现错误的主角名
        wrong_names = ['林远', '周洛铭', '张明']  # 常见错误名字
        full_text = f"{title} {setup} {beats}"

        for wrong_name in wrong_names:
            if wrong_name in full_text:
                errors.append(f"❌ 第{ch['chapter']}章出现错误主角名：{wrong_name}（应为{protagonist_name}）")

    if not errors:
        print(f"✓ 主角名字一致：{protagonist_name}")

    return errors

def validate_golden_finger(bible: dict) -> List[str]:
    """验证金手指使用"""
    warnings = []
    chapter_events = bible.get('chapter_events', [])

    use_count = 0
    for ch in chapter_events:
        gf_use = ch.get('golden_finger_use')
        if gf_use:
            # 检查是否真正使用了金手指
            trigger = gf_use.get('trigger', '')
            manifestation = gf_use.get('manifestation', '')

            # 如果trigger或manifestation包含"无"，则认为没有使用
            if '无' not in trigger and '无' not in manifestation:
                use_count += 1

    print(f"ℹ️  金手指使用次数：{use_count}/30章")

    if use_count > 20:
        warnings.append(f"⚠️  金手指使用过于频繁：{use_count}/30章（建议<20次）")

    return warnings

def main():
    """主函数"""
    project_root = Path(__file__).parent
    bible_path = project_root / 'registry/story-bible/BIBLE-00001.yaml'

    print("=" * 60)
    print("Story Bible 验证报告")
    print("=" * 60)
    print()

    if not bible_path.exists():
        print(f"❌ 找不到 Story Bible: {bible_path}")
        return

    print(f"📖 加载: {bible_path}")
    bible = load_story_bible(bible_path)
    print(f"   版本: {bible.get('version')}")
    print(f"   状态: {bible.get('status')}")
    print()

    all_errors = []
    all_warnings = []

    # 1. 完整性检查
    print("1️⃣  完整性检查")
    print("-" * 60)
    errors = validate_completeness(bible)
    all_errors.extend(errors)
    print()

    # 2. 时间线检查
    print("2️⃣  时间线检查")
    print("-" * 60)
    errors = validate_timeline(bible)
    all_errors.extend(errors)
    print()

    # 3. 钩子检查
    print("3️⃣  钩子连贯性检查")
    print("-" * 60)
    errors = validate_hooks(bible)
    all_errors.extend(errors)
    print()

    # 4. 地点检查
    print("4️⃣  地点一致性检查")
    print("-" * 60)
    errors = validate_locations(bible)
    all_warnings.extend(errors)  # 地点问题作为警告
    print()

    # 5. 人物检查
    print("5️⃣  人物一致性检查")
    print("-" * 60)
    errors = validate_characters(bible)
    all_errors.extend(errors)
    print()

    # 6. 金手指检查
    print("6️⃣  金手指平衡性检查")
    print("-" * 60)
    warnings = validate_golden_finger(bible)
    all_warnings.extend(warnings)
    print()

    # 总结
    print("=" * 60)
    print("验证总结")
    print("=" * 60)

    if all_errors:
        print(f"❌ 发现 {len(all_errors)} 个错误：")
        for err in all_errors:
            print(f"   {err}")
        print()
    else:
        print("✅ 未发现严重错误")
        print()

    if all_warnings:
        print(f"⚠️  发现 {len(all_warnings)} 个警告：")
        for warn in all_warnings:
            print(f"   {warn}")
        print()
    else:
        print("✅ 未发现警告")
        print()

    if not all_errors and not all_warnings:
        print("🎉 Story Bible 验证通过！")
        print()
        print("下一步：")
        print("1. 人工审核 Story Bible")
        print("2. 确认无误后，设置 status: human_approved")
        print("3. 运行 python generate_events_from_bible.py 生成事件")
    else:
        print("⚠️  请修复上述问题后重新验证")

    print()

if __name__ == '__main__':
    main()
