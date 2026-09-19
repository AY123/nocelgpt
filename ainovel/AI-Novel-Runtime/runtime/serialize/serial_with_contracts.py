"""
Serial with Contract Integration

这是 run_serial 的包装器，集成了契约验证和状态管理。
"""

from pathlib import Path
from typing import Optional, Dict, Any
import logging

from .contract_integration import create_integration
from ..contract import ProductionState


logger = logging.getLogger(__name__)


def run_serial_with_contracts(
    *,
    enable_contract_integration: bool = False,
    **serial_kwargs
):
    """
    run_serial 的包装器，集成契约验证

    Args:
        enable_contract_integration: 是否启用契约集成（默认 False）
        **serial_kwargs: 传递给 run_serial 的其他参数

    Returns:
        与 run_serial 相同的返回值
    """
    from .loop import run_serial

    # 如果不启用契约集成，直接调用原始 run_serial
    if not enable_contract_integration:
        logger.info("契约集成未启用，使用标准 Serial 流程")
        return run_serial(**serial_kwargs)

    # 启用契约集成
    logger.info("=" * 60)
    logger.info("契约集成已启用")
    logger.info("=" * 60)

    # 获取项目路径
    project_path = Path(serial_kwargs.get('project_path', '.'))

    # 创建契约集成
    integration = create_integration(
        project_path=project_path,
        enable_contract_integration=True
    )

    if not integration or not integration.is_enabled():
        logger.warning("契约集成创建失败，降级到标准 Serial 流程")
        return run_serial(**serial_kwargs)

    logger.info(integration.summary())
    logger.info("=" * 60)

    # TODO: 这里需要更深度的集成
    # 目前作为概念验证，我们调用标准 Serial 并在之后验证

    logger.info("运行标准 Serial 流程...")
    result = run_serial(**serial_kwargs)

    logger.info("=" * 60)
    logger.info("Serial 运行完成，开始验证章节...")
    logger.info("=" * 60)

    # 后验证：检查生成的章节
    _post_validate_chapters(integration, project_path, serial_kwargs)

    return result


def _post_validate_chapters(
    integration,
    project_path: Path,
    serial_kwargs: Dict[str, Any]
):
    """
    后验证：检查已生成的章节

    这是一个简化版本，用于演示契约验证。
    完整集成需要在生成过程中实时验证。
    """
    start_chapter = serial_kwargs.get('start_chapter', 1)
    max_chapters = serial_kwargs.get('max_chapters', 30)

    validation_results = []

    for chapter_num in range(start_chapter, start_chapter + max_chapters):
        # 查找章节文件
        # 实际路径需要根据项目结构调整
        chapter_file = _find_chapter_file(project_path, chapter_num)

        if not chapter_file:
            logger.info(f"第{chapter_num}章未找到，停止验证")
            break

        # 读取章节内容
        try:
            with open(chapter_file, 'r', encoding='utf-8') as f:
                import json
                chapter_data = json.load(f)
                draft_text = chapter_data.get('content', '')
        except Exception as e:
            logger.error(f"读取第{chapter_num}章失败: {e}")
            continue

        # 验证契约
        passed, result = integration.validate_chapter_draft(
            chapter_num,
            draft_text=draft_text
        )

        validation_results.append({
            'chapter': chapter_num,
            'passed': passed,
            'result': result
        })

        # 输出验证结果
        if passed:
            logger.info(f"✓ 第{chapter_num}章契约验证通过")
        else:
            logger.warning(f"✗ 第{chapter_num}章契约验证失败")
            logger.warning(f"  错误: {result.get('errors', [])}")
            logger.warning(f"  警告: {result.get('warnings', [])}")

    # 输出验证统计
    logger.info("=" * 60)
    logger.info("验证统计:")
    total = len(validation_results)
    passed_count = sum(1 for r in validation_results if r['passed'])
    failed_count = total - passed_count

    logger.info(f"  总章节数: {total}")
    logger.info(f"  通过: {passed_count}")
    logger.info(f"  失败: {failed_count}")
    logger.info(f"  通过率: {passed_count/total*100:.1f}%" if total > 0 else "  通过率: N/A")
    logger.info("=" * 60)


def _find_chapter_file(project_path: Path, chapter_num: int) -> Optional[Path]:
    """
    查找章节文件

    可能的位置：
    - registry/derived/chapter-final/final-TASK-{chapter_num:05d}.json
    - out/chapter-{chapter_num:05d}.json
    """
    candidates = [
        project_path / "registry" / "derived" / "chapter-final" / f"final-TASK-{chapter_num:05d}.json",
        project_path / "out" / f"chapter-{chapter_num:05d}.json",
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return None


# 便捷函数：用于命令行调用
def main():
    """
    命令行入口

    用法:
        python -m runtime.serialize.serial_with_contracts \\
            --project-path novel-dushi \\
            --enable-contract-integration
    """
    import argparse

    parser = argparse.ArgumentParser(description="Serial with Contract Integration")
    parser.add_argument('--project-path', required=True, help="项目路径")
    parser.add_argument('--enable-contract-integration', action='store_true', help="启用契约集成")
    parser.add_argument('--start-chapter', type=int, default=1, help="起始章节")
    parser.add_argument('--max-chapters', type=int, default=3, help="最大章节数")

    args = parser.parse_args()

    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 运行
    run_serial_with_contracts(
        enable_contract_integration=args.enable_contract_integration,
        project_path=args.project_path,
        start_chapter=args.start_chapter,
        max_chapters=args.max_chapters,
        # 其他必要参数需要补充
    )


if __name__ == '__main__':
    main()
