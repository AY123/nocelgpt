"""
Contract Validator for Release

发布前的契约验证器，确保只有符合要求的章节进入发布包。
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
import json
import logging

from ..contract import ProductionState
from ..serialize.contract_integration import create_integration


logger = logging.getLogger(__name__)


def validate_chapter_contracts_for_release(
    project_path: Path,
    chapter_list: List[int]
) -> Dict[str, Any]:
    """
    发布前的章节契约验证

    检查：
    1. 所有章节文件存在
    2. 所有章节状态为 HUMAN_APPROVED 或 PUBLISHED
    3. 所有章节通过契约验证
    4. 章节间连续性正确

    Args:
        project_path: 项目路径
        chapter_list: 要发布的章节号列表

    Returns:
        dict: {
            'passed': bool,              # 总体是否通过
            'blocking_issues': list[str], # 阻塞问题列表
            'chapter_validations': dict,  # 每章验证结果
            'statistics': dict,           # 统计信息
            'contract_validation_report': dict  # 详细验证报告
        }
    """
    result = {
        'passed': True,
        'blocking_issues': [],
        'chapter_validations': {},
        'statistics': {
            'total_chapters': len(chapter_list),
            'validated_chapters': 0,
            'approved_chapters': 0,
            'blocked_chapters': 0,
            'contract_passed': 0,
            'contract_failed': 0,
        },
        'contract_validation_report': {}
    }

    # 创建契约集成
    integration = create_integration(
        project_path=project_path,
        enable_contract_integration=True
    )

    if not integration or not integration.is_enabled():
        logger.warning("契约集成未启用，跳过契约验证")
        result['blocking_issues'].append("Contract integration not enabled")
        result['passed'] = False
        return result

    logger.info(f"开始验证 {len(chapter_list)} 个章节用于发布")

    # 验证每个章节
    for chapter_num in chapter_list:
        chapter_validation = _validate_single_chapter(
            project_path,
            chapter_num,
            integration
        )

        result['chapter_validations'][chapter_num] = chapter_validation
        result['statistics']['validated_chapters'] += 1

        # 更新统计
        if chapter_validation['state_check']['approved']:
            result['statistics']['approved_chapters'] += 1
        else:
            result['statistics']['blocked_chapters'] += 1
            result['blocking_issues'].append(
                f"Chapter {chapter_num}: {chapter_validation['state_check']['message']}"
            )
            result['passed'] = False

        if chapter_validation['contract_check']['passed']:
            result['statistics']['contract_passed'] += 1
        else:
            result['statistics']['contract_failed'] += 1
            result['blocking_issues'].extend([
                f"Chapter {chapter_num}: {err}"
                for err in chapter_validation['contract_check']['errors']
            ])
            result['passed'] = False

    # 检查连续性（如果章节是连续的）
    if chapter_list == list(range(min(chapter_list), max(chapter_list) + 1)):
        continuity_check = _check_story_continuity(
            project_path,
            chapter_list,
            integration
        )
        result['continuity_check'] = continuity_check

        if not continuity_check['passed']:
            result['blocking_issues'].extend(continuity_check['errors'])
            result['passed'] = False

    # 生成验证报告
    result['contract_validation_report'] = _generate_validation_report(result)

    logger.info(f"验证完成: {result['statistics']}")

    return result


def _validate_single_chapter(
    project_path: Path,
    chapter_num: int,
    integration
) -> Dict[str, Any]:
    """
    验证单个章节

    Returns:
        {
            'exists': bool,
            'state_check': dict,
            'contract_check': dict
        }
    """
    validation = {
        'exists': False,
        'state_check': {
            'approved': False,
            'state': None,
            'message': ''
        },
        'contract_check': {
            'passed': False,
            'errors': [],
            'warnings': []
        }
    }

    # 查找章节文件
    chapter_file = _find_chapter_file(project_path, chapter_num)

    if not chapter_file:
        validation['state_check']['message'] = f"Chapter file not found"
        return validation

    validation['exists'] = True

    # 加载章节数据
    try:
        with open(chapter_file, 'r', encoding='utf-8') as f:
            chapter_data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load chapter {chapter_num}: {e}")
        validation['state_check']['message'] = f"Failed to load chapter file"
        return validation

    # 检查状态
    state_str = chapter_data.get('production_state', 'generated')
    try:
        state = ProductionState(state_str)
    except ValueError:
        state = ProductionState.GENERATED

    validation['state_check']['state'] = state.value
    validation['state_check']['approved'] = state.can_export()

    if not state.can_export():
        validation['state_check']['message'] = (
            f"State {state.display_name()} cannot be exported"
        )
    else:
        validation['state_check']['message'] = "State approved for export"

    # 契约验证
    draft_text = chapter_data.get('content', '')
    if draft_text:
        passed, result = integration.validate_chapter_draft(
            chapter_num,
            draft_text
        )
        validation['contract_check']['passed'] = passed
        validation['contract_check']['errors'] = result.get('errors', [])
        validation['contract_check']['warnings'] = result.get('warnings', [])
    else:
        validation['contract_check']['errors'] = ["No content to validate"]

    return validation


def _find_chapter_file(project_path: Path, chapter_num: int) -> Optional[Path]:
    """查找章节文件"""
    candidates = [
        project_path / "registry" / "derived" / "chapter-final" / f"final-TASK-{chapter_num:05d}.json",
        project_path / "out" / f"chapter-{chapter_num:05d}.json",
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return None


def _check_story_continuity(
    project_path: Path,
    chapter_list: List[int],
    integration
) -> Dict[str, Any]:
    """检查故事连续性"""
    continuity = {
        'passed': True,
        'errors': [],
        'checks': []
    }

    # 简化版：只检查章节号是否连续
    sorted_chapters = sorted(chapter_list)

    for i in range(len(sorted_chapters) - 1):
        curr = sorted_chapters[i]
        next_ch = sorted_chapters[i + 1]

        if next_ch != curr + 1:
            continuity['passed'] = False
            continuity['errors'].append(
                f"Chapter gap: {curr} → {next_ch} (expected {curr + 1})"
            )

    # TODO: 更深入的连续性检查
    # - 时间线检查
    # - 人物一致性
    # - 故事状态传递

    return continuity


def _generate_validation_report(validation_result: Dict[str, Any]) -> Dict[str, Any]:
    """生成验证报告"""
    stats = validation_result['statistics']

    report = {
        'summary': {
            'total_chapters': stats['total_chapters'],
            'validation_passed': validation_result['passed'],
            'approved_rate': (
                stats['approved_chapters'] / stats['total_chapters'] * 100
                if stats['total_chapters'] > 0 else 0
            ),
            'contract_pass_rate': (
                stats['contract_passed'] / stats['validated_chapters'] * 100
                if stats['validated_chapters'] > 0 else 0
            ),
        },
        'details': {
            'approved_chapters': stats['approved_chapters'],
            'blocked_chapters': stats['blocked_chapters'],
            'contract_passed': stats['contract_passed'],
            'contract_failed': stats['contract_failed'],
        },
        'blocking_issues': validation_result['blocking_issues'],
    }

    return report


def get_release_validation_summary(validation_result: Dict[str, Any]) -> str:
    """生成人类可读的验证摘要"""
    stats = validation_result['statistics']
    passed = validation_result['passed']

    lines = [
        "=" * 60,
        "Release Validation Summary",
        "=" * 60,
        f"Total Chapters: {stats['total_chapters']}",
        f"Approved: {stats['approved_chapters']}",
        f"Blocked: {stats['blocked_chapters']}",
        f"Contract Passed: {stats['contract_passed']}",
        f"Contract Failed: {stats['contract_failed']}",
        f"",
        f"Overall: {'✓ PASSED' if passed else '✗ FAILED'}",
    ]

    if not passed:
        lines.append("")
        lines.append("Blocking Issues:")
        for issue in validation_result['blocking_issues'][:10]:  # 最多显示10个
            lines.append(f"  - {issue}")

        if len(validation_result['blocking_issues']) > 10:
            remaining = len(validation_result['blocking_issues']) - 10
            lines.append(f"  ... and {remaining} more issues")

    lines.append("=" * 60)

    return "\n".join(lines)
