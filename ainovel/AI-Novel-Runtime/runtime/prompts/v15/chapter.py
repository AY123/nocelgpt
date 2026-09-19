"""
v15 Chapter Prompt生成器

将Contract Gate集成到prompt生成流程中
"""

from pathlib import Path
from typing import Optional, Dict, Any
import sys

# 添加Contract Gate到路径
contract_plugin_path = Path(__file__).parent.parent.parent.parent.parent / 'runtime_plugins'
sys.path.insert(0, str(contract_plugin_path))

from runtime_plugins.contract import ContractGate, ContractCheckError


def render_chapter_prompt_v15(
    chapter: int,
    contracts_dir: Path,
    schemas_dir: Path,
    base_context: Dict[str, Any],
    strict_mode: bool = False
) -> str:
    """
    生成v15版本的章节prompt

    v15特性：
    1. 强制契约检查（precheck）
    2. 契约内容注入到prompt
    3. 基于v5的所有功能

    Args:
        chapter: 章节号
        contracts_dir: 契约目录
        schemas_dir: Schema目录
        base_context: 基础上下文（objective、ir等）
        strict_mode: 严格模式（precheck失败时抛异常）

    Returns:
        完整的prompt字符串

    Raises:
        ContractCheckError: strict_mode=True且precheck失败时
    """
    # 初始化Contract Gate
    gate = ContractGate(
        contracts_dir=contracts_dir,
        schemas_dir=schemas_dir
    )

    # 1. Precheck - 验证契约
    try:
        gate.precheck(chapter)
    except ContractCheckError as e:
        if strict_mode:
            raise
        else:
            # 非严格模式：记录警告但继续
            import logging
            logging.warning(f"Ch{chapter}契约检查失败（非严格模式，继续生成）: {e}")
            # 降级到v5（无契约）
            return _render_v5_fallback(chapter, base_context)

    # 2. 加载契约
    try:
        contract = gate.load_contract(chapter)
    except Exception as e:
        import logging
        logging.error(f"Ch{chapter}契约加载失败: {e}")
        # 降级到v5
        return _render_v5_fallback(chapter, base_context)

    # 3. 生成基础prompt（继承v5逻辑）
    base_prompt = _render_base_prompt(chapter, base_context)

    # 4. 注入契约
    full_prompt = gate.inject_contract(base_prompt, contract)

    return full_prompt


def _render_base_prompt(chapter: int, context: Dict[str, Any]) -> str:
    """
    生成基础prompt（简化版v5逻辑）

    在实际集成时，这里应该调用真正的v5 prompt生成器
    """
    objective = context.get('objective', '')
    ir = context.get('ir', '')
    actual_entry_state = context.get('actual_entry_state', '')

    # 构建 prompt 各部分
    prompt_parts = [f"你正在创作长篇小说《玲色》的第{chapter}章。"]

    # P0-3: 如果存在实际入口状态，优先展示
    if actual_entry_state:
        prompt_parts.append(f"\n{actual_entry_state}\n")

    prompt_parts.append(f"""
【创作目标】
{objective}

【情节要求】
{ir}

【创作要求】
1. 保持人物一致性
2. 使用具体细节和感官描写
3. 对话推动情节
4. 保持节奏紧凑

字数要求：2500-3500字

现在开始创作第{chapter}章。
""")

    return "".join(prompt_parts)


def _render_v5_fallback(chapter: int, context: Dict[str, Any]) -> str:
    """
    降级到v5（无契约版本）

    当契约检查失败或加载失败时使用
    """
    import logging
    logging.info(f"Ch{chapter}使用v5 fallback（无契约）")

    return _render_base_prompt(chapter, context)


def validate_v15_config(contracts_dir: Path, schemas_dir: Path) -> bool:
    """
    验证v15配置是否正确

    Returns:
        True if valid, False otherwise
    """
    if not contracts_dir.exists():
        return False

    if not schemas_dir.exists():
        return False

    schema_file = schemas_dir / 'chapter_contract.schema.json'
    if not schema_file.exists():
        return False

    return True
