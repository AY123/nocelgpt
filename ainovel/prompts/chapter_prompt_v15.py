#!/usr/bin/env python3
"""
Chapter Prompt v15 - 集成章节契约
"""

def generate_chapter_prompt_v15(
    chapter: int,
    contract: dict,
    objective: str = None,
    ir: dict = None,
    mandate: dict = None
) -> str:
    """
    生成包含契约的章节prompt

    Args:
        chapter: 章节号
        contract: 章节契约
        objective: 本章目标（可选，从契约派生）
        ir: Chapter IR（可选）
        mandate: Narrative Mandate（可选）

    Returns:
        完整的章节prompt
    """

    # 提取契约信息
    entry_state = contract.get("entry_state", {})
    chapter_intent = contract.get("chapter_intent", {})
    exit_target = contract.get("exit_target", {})
    transition = contract.get("transition_to_next", {})

    # 构建prompt
    prompt = f"""你正在创作长篇小说《玲色》的第{chapter}章。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 章节契约（必须严格遵守）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【入口要求】
本章必须如何开始：

• 地点：{_format_location(entry_state.get('location_id'))}
• 时间关系：{_format_time_relation(entry_state.get('time_relation'))}
• 视角：{entry_state.get('pov', '段奕尘')}
• 在场人物：{', '.join(entry_state.get('required_characters', ['段奕尘']))}

上一章钩子（必须在前20%消费）：
{entry_state.get('must_address', '无')}

{_format_hook_consumption_rule(entry_state.get('hook_to_consume'), transition.get('consume_hook_by_percent', 20))}

【本章目标】
{chapter_intent.get('objective', objective or f'Ch{chapter}目标')}

主要冲突：
{chapter_intent.get('main_conflict', '待定义')}

推进剧情线：
{', '.join(chapter_intent.get('plot_lines', []))}

必须产生的不可逆变化：
{chapter_intent.get('irreversible_change', '待定义')}

【出口要求】
本章必须如何结束：

• 结束地点：{_format_location(exit_target.get('location_id'))}
• 在场人物：{', '.join(exit_target.get('characters_present', ['段奕尘']))}

未完成动作（留给下一章）：
{exit_target.get('unfinished_action', '待定义')}

章末钩子（必须设置）：
{exit_target.get('hook_promise', '待定义')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 契约遵守检查清单
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

生成后请确认：
□ 开头符合入口要求（地点、时间、视角、人物）
□ 前20%处理了上章钩子
□ 实现了本章目标和不可逆变化
□ 结尾符合出口要求
□ 设置了明确的章末钩子

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📖 创作要求
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. 严格遵守契约（这是硬约束）
2. 保持人物一致性
3. 使用具体细节和感官描写
4. 对话推动情节
5. 章末钩子要强烈

字数要求：2500-3500字

现在开始创作第{chapter}章。
"""

    return prompt


def _format_location(location_id: str) -> str:
    """格式化地点ID为可读文本"""
    if not location_id or location_id == "loc_unknown":
        return "（待定义）"

    # 简单替换loc_前缀
    return location_id.replace("loc_", "").replace("_", " ")


def _format_time_relation(time_relation: str) -> str:
    """格式化时间关系"""
    mapping = {
        "immediate": "紧接上章（无时间间隔）",
        "short_gap": "短暂间隔（几分钟到半小时）",
        "jump": "时间跳跃（需要明确说明）",
        "flashback": "闪回/回忆（需要明确标记）"
    }
    return mapping.get(time_relation, time_relation)


def _format_hook_consumption_rule(hook_id: str, percent: int) -> str:
    """格式化钩子消费规则"""
    if not hook_id:
        return ""

    return f"""
⚠️ 重要：钩子消费规则
钩子ID: {hook_id}
必须在前{percent}%段落中回应或处理上述内容。
不能遗忘、不能拖延到章节后半部分。
"""


def test_prompt():
    """测试prompt生成"""
    # 模拟Ch101契约
    contract = {
        "entry_state": {
            "location_id": "loc_矿场边缘_乱石堆",
            "time_relation": "immediate",
            "pov": "段奕尘",
            "required_characters": ["段奕尘", "镜见川"],
            "hook_to_consume": "hook_100_01",
            "must_address": "曜师听见了段奕尘的呼唤，远处晶石响应发光"
        },
        "chapter_intent": {
            "objective": "段奕尘与镜见川商议下一步计划，决定深入寻找曜师",
            "main_conflict": "急于行动 vs 理性警告",
            "plot_lines": ["主线-寻找曜师", "成长线-失落曜晶"],
            "irreversible_change": "公开了寻找曜师的真正目的"
        },
        "exit_target": {
            "location_id": "loc_矿场_秘密通道入口",
            "characters_present": ["段奕尘", "镜见川"],
            "unfinished_action": "通道入口出现异常能量波动",
            "hook_promise": "通道深处传来诡异声音"
        },
        "transition_to_next": {
            "consume_hook_by_percent": 20
        }
    }

    prompt = generate_chapter_prompt_v15(101, contract)
    print(prompt)


if __name__ == '__main__':
    test_prompt()
