#!/usr/bin/env python3
"""
章间契约提取工具
从100章正文中自动提取 exit_bridge 和 entry_state
"""

import re
import json
import os
import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 尝试导入OpenAI
try:
    from openai import OpenAI
except ImportError:
    print("警告: 未安装openai库，将使用模拟模式")
    OpenAI = None


def load_env():
    """加载.env环境变量"""
    env_vars = {}
    env_file = Path(__file__).parent.parent / '.env'

    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value

    return env_vars


def extract_chapters(content):
    """
    从小说内容中提取各章节

    Returns:
        dict: {chapter_num: chapter_text}
    """
    chapters = {}

    # 分割章节
    chapter_pattern = re.compile(r'## 第(\d+)章')
    matches = list(chapter_pattern.finditer(content))

    for i, match in enumerate(matches):
        ch_num = int(match.group(1))
        start = match.start()

        # 确定结束位置
        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            end = len(content)

        chapter_text = content[start:end]
        chapters[ch_num] = chapter_text

    return chapters


def extract_chapter_ending(chapter_text, n_paragraphs=5):
    """
    提取章节末尾N段
    """
    # 分段（按双换行）
    paragraphs = [p.strip() for p in chapter_text.split('\n\n') if p.strip()]

    # 过滤掉标题和空行
    content_paragraphs = []
    for p in paragraphs:
        if p.startswith('#'):
            continue
        if len(p) < 10:
            continue
        content_paragraphs.append(p)

    # 返回最后N段
    ending = content_paragraphs[-n_paragraphs:] if len(content_paragraphs) >= n_paragraphs else content_paragraphs

    return '\n\n'.join(ending)


def extract_chapter_opening(chapter_text, n_paragraphs=3):
    """
    提取章节开头N段
    """
    paragraphs = [p.strip() for p in chapter_text.split('\n\n') if p.strip()]

    content_paragraphs = []
    for p in paragraphs:
        if p.startswith('#'):
            continue
        if len(p) < 10:
            continue
        content_paragraphs.append(p)

    opening = content_paragraphs[:n_paragraphs] if len(content_paragraphs) >= n_paragraphs else content_paragraphs

    return '\n\n'.join(opening)


def extract_bridge_with_llm(chapter_num, ending_text, next_opening_text=None):
    """
    使用LLM提取章节桥接信息
    """
    env_vars = load_env()

    if not OpenAI:
        return create_mock_bridge(chapter_num, ending_text)

    # 初始化客户端
    api_key = env_vars.get('CC_VIBE_OPENAI_AUTH_TOKEN') or env_vars.get('DEEPSEEK_API_KEY')
    base_url = env_vars.get('CC_VIBE_OPENAI_BASE_URL') or 'https://api.deepseek.com'

    if not api_key:
        print(f"警告: 未找到API密钥，Ch{chapter_num}使用模拟数据")
        return create_mock_bridge(chapter_num, ending_text)

    client = OpenAI(api_key=api_key, base_url=base_url)

    # 构建提示词
    # 构建下一章部分
    next_chapter_part = ""
    if next_opening_text:
        next_chapter_part = f"【下一章开头】\n{next_opening_text}\n"

    prompt = f"""你是小说分析专家。分析以下第{chapter_num}章的结尾段落，提取章间桥接信息。

【章节结尾】
{ending_text}

{next_chapter_part}

请提取以下信息，以JSON格式输出：

{{
  "time": "时间状态（如：当夜、三天后、同时）",
  "location": "地点（具体位置）",
  "pov": "视角人物",
  "characters_present": ["在场人物列表"],
  "physical_state": {{"人物": "身体状态描述"}},
  "emotional_state": {{"人物": "情绪状态"}},
  "unfinished_action": "未完成的动作或悬念",
  "hook_promise": "章末留下的钩子承诺",
  "next_chapter_hint": "下一章应该如何开始"
}}

只输出JSON，不要其他内容。
"""

    # 确定模型名称
    if 'cc-vibe' in base_url.lower():
        # CC_VIBE: 优先使用环境变量中的模型，否则用gpt-4o-mini
        model_name = env_vars.get('CC_VIBE_OPENAI_MODEL', 'gpt-4o-mini')
    else:
        model_name = "deepseek-chat"  # DeepSeek

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "你是专业的小说结构分析专家。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1000
        )

        content = response.choices[0].message.content

        # 提取JSON
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        bridge_data = json.loads(content.strip())
        bridge_data['chapter'] = chapter_num

        return bridge_data

    except Exception as e:
        print(f"警告: Ch{chapter_num} LLM提取失败: {str(e)[:50]}")
        return create_mock_bridge(chapter_num, ending_text)


def create_mock_bridge(chapter_num, ending_text):
    """
    创建模拟的桥接数据（当LLM不可用时）
    """
    return {
        "chapter": chapter_num,
        "time": "未提取",
        "location": "未提取",
        "pov": "段奕尘",
        "characters_present": [],
        "physical_state": {},
        "emotional_state": {},
        "unfinished_action": "待分析",
        "hook_promise": "待分析",
        "next_chapter_hint": "待分析",
        "extraction_method": "mock",
        "ending_preview": ending_text[:200]
    }


def main():
    """
    主函数
    """
    print("=" * 70)
    print("章间契约提取工具")
    print("=" * 70)
    print()

    # 读取小说
    novel_path = Path(__file__).parent.parent / 'novel-lingse-complete-100-chapters.md'

    if not novel_path.exists():
        print(f"错误: 未找到文件 {novel_path}")
        return

    print(f"读取文件: {novel_path.name}")

    with open(novel_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 提取章节
    print("提取章节...")
    chapters = extract_chapters(content)

    print(f"✅ 提取到 {len(chapters)} 章")
    print()

    # 提取桥接信息
    print("开始提取章间桥接信息...")
    print()

    bridges = {}

    # 提取全部100章
    import sys

    # 从命令行参数获取范围，默认前10章
    if len(sys.argv) > 1:
        if sys.argv[1] == '--all':
            test_chapters = range(1, len(chapters) + 1)
            print(f"模式: 全量提取（1-{len(chapters)}章）")
        else:
            start, end = map(int, sys.argv[1].split('-'))
            test_chapters = range(start, min(end + 1, len(chapters) + 1))
            print(f"模式: 范围提取（{start}-{end}章）")
    else:
        test_chapters = range(1, min(11, len(chapters) + 1))
        print(f"模式: 测试提取（前10章）")

    for i, ch_num in enumerate(test_chapters, 1):
        print(f"[{i}/{len(list(test_chapters))}] 提取Ch{ch_num}...", end=" ", flush=True)

        if ch_num not in chapters:
            print("❌ 章节不存在")
            continue

        # 提取章末
        ending = extract_chapter_ending(chapters[ch_num])

        # 提取下一章开头（如果存在）
        next_opening = None
        if ch_num + 1 in chapters:
            next_opening = extract_chapter_opening(chapters[ch_num + 1])

        # 提取桥接
        bridge = extract_bridge_with_llm(ch_num, ending, next_opening)
        bridges[ch_num] = bridge

        print("✅")

    print()
    print("=" * 70)
    print("✅ 提取完成（测试：前10章）")
    print("=" * 70)
    print()

    # 保存结果
    output_path = Path(__file__).parent.parent / 'data' / 'chapter_bridges.json'

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(bridges, f, ensure_ascii=False, indent=2)

    print(f"📁 已保存: {output_path}")
    print()

    # 显示示例
    if bridges:
        first_ch = list(bridges.keys())[0]
        print(f"示例（Ch{first_ch}）:")
        print("-" * 70)
        print(json.dumps(bridges[first_ch], ensure_ascii=False, indent=2)[:500])
        print("...")
        print()

    print("下一步:")
    print("  1. 检查 data/chapter_bridges.json")
    print("  2. 如果质量满意，运行全量提取（1-100章）")
    print("  3. 运行连续性检查工具")
    print()


if __name__ == '__main__':
    main()
