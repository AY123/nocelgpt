"""
契约审批与版本管理工具 (Task 3.3)

提供契约审批历史记录和版本管理功能。
"""

from pathlib import Path
import json
from datetime import datetime
from typing import Optional


class ContractApprovalManager:
    """契约审批与版本管理器"""

    def __init__(self, contracts_dir: Path):
        """
        初始化管理器

        Args:
            contracts_dir: 契约目录
        """
        self.contracts_dir = Path(contracts_dir)

    def approve_contract(
        self,
        chapter: int,
        approved_by: str,
        reason: str = "",
        changes: str = ""
    ) -> dict:
        """
        审批契约

        Args:
            chapter: 章节号
            approved_by: 审批人
            reason: 审批理由
            changes: 相对于前一版本的变更说明

        Returns:
            更新后的契约

        Raises:
            FileNotFoundError: 契约文件不存在
        """
        contract_file = self.contracts_dir / f'chapter_{chapter:03d}_contract.json'

        if not contract_file.exists():
            raise FileNotFoundError(f"契约文件不存在: {contract_file}")

        with open(contract_file, 'r', encoding='utf-8') as f:
            contract = json.load(f)

        # 记录审批历史
        if 'approval_history' not in contract:
            contract['approval_history'] = []

        approval_record = {
            "version": contract.get('version', 'v1.0'),
            "approved": True,
            "approved_at": datetime.now().isoformat(),
            "approved_by": approved_by,
            "reason": reason,
            "changes_from_previous": changes
        }

        contract['approval_history'].append(approval_record)

        # 更新顶层字段（向后兼容）
        contract['approved'] = True
        contract['approved_at'] = approval_record['approved_at']

        # 保存回文件
        with open(contract_file, 'w', encoding='utf-8') as f:
            json.dump(contract, f, ensure_ascii=False, indent=2)

        return contract

    def reject_contract(
        self,
        chapter: int,
        rejected_by: str,
        reason: str
    ) -> dict:
        """
        拒绝契约

        Args:
            chapter: 章节号
            rejected_by: 拒绝人
            reason: 拒绝理由

        Returns:
            更新后的契约
        """
        contract_file = self.contracts_dir / f'chapter_{chapter:03d}_contract.json'

        if not contract_file.exists():
            raise FileNotFoundError(f"契约文件不存在: {contract_file}")

        with open(contract_file, 'r', encoding='utf-8') as f:
            contract = json.load(f)

        # 记录拒绝历史
        if 'approval_history' not in contract:
            contract['approval_history'] = []

        rejection_record = {
            "version": contract.get('version', 'v1.0'),
            "approved": False,
            "approved_at": datetime.now().isoformat(),
            "approved_by": rejected_by,
            "reason": reason,
            "changes_from_previous": ""
        }

        contract['approval_history'].append(rejection_record)

        # 更新顶层字段
        contract['approved'] = False
        contract['approved_at'] = rejection_record['approved_at']

        # 保存回文件
        with open(contract_file, 'w', encoding='utf-8') as f:
            json.dump(contract, f, ensure_ascii=False, indent=2)

        return contract

    def increment_version(
        self,
        chapter: int,
        increment_type: str = "minor"
    ) -> str:
        """
        递增契约版本

        Args:
            chapter: 章节号
            increment_type: 递增类型 ("major" or "minor")

        Returns:
            新版本号

        Raises:
            FileNotFoundError: 契约文件不存在
            ValueError: 无效的递增类型
        """
        if increment_type not in ("major", "minor"):
            raise ValueError("increment_type must be 'major' or 'minor'")

        contract_file = self.contracts_dir / f'chapter_{chapter:03d}_contract.json'

        if not contract_file.exists():
            raise FileNotFoundError(f"契约文件不存在: {contract_file}")

        with open(contract_file, 'r', encoding='utf-8') as f:
            contract = json.load(f)

        current_version = contract.get('version', 'v1.0')

        # 解析版本号
        version_str = current_version.replace('v', '')
        parts = version_str.split('.')
        major = int(parts[0])
        minor = int(parts[1]) if len(parts) > 1 else 0

        # 递增
        if increment_type == "major":
            major += 1
            minor = 0
        else:  # minor
            minor += 1

        new_version = f"v{major}.{minor}"

        # 更新契约
        contract['version'] = new_version

        # 重置审批状态（新版本需要重新审批）
        contract['approved'] = False
        contract['approved_at'] = None

        # 保存回文件
        with open(contract_file, 'w', encoding='utf-8') as f:
            json.dump(contract, f, ensure_ascii=False, indent=2)

        return new_version

    def get_approval_history(self, chapter: int) -> list:
        """
        获取契约的审批历史

        Args:
            chapter: 章节号

        Returns:
            审批历史列表

        Raises:
            FileNotFoundError: 契约文件不存在
        """
        contract_file = self.contracts_dir / f'chapter_{chapter:03d}_contract.json'

        if not contract_file.exists():
            raise FileNotFoundError(f"契约文件不存在: {contract_file}")

        with open(contract_file, 'r', encoding='utf-8') as f:
            contract = json.load(f)

        return contract.get('approval_history', [])

    def get_version_timeline(self, chapter: int) -> list:
        """
        获取契约的版本时间线

        Args:
            chapter: 章节号

        Returns:
            版本时间线（按时间排序的审批记录）
        """
        history = self.get_approval_history(chapter)

        # 按时间排序
        sorted_history = sorted(
            history,
            key=lambda x: x.get('approved_at', ''),
            reverse=False
        )

        return sorted_history

    def audit_trail(self, chapter: int) -> str:
        """
        生成契约的审计追踪报告

        Args:
            chapter: 章节号

        Returns:
            人类可读的审计报告
        """
        try:
            timeline = self.get_version_timeline(chapter)
        except FileNotFoundError:
            return f"契约 Ch{chapter} 不存在"

        if not timeline:
            return f"契约 Ch{chapter} 无审批历史"

        report = [f"契约 Ch{chapter} 审计追踪:"]
        report.append("=" * 50)

        for i, record in enumerate(timeline, 1):
            version = record.get('version', 'unknown')
            approved = "✅ 批准" if record.get('approved') else "❌ 拒绝"
            at = record.get('approved_at', 'unknown')
            by = record.get('approved_by', 'unknown')
            reason = record.get('reason', '')
            changes = record.get('changes_from_previous', '')

            report.append(f"\n{i}. {version} - {approved}")
            report.append(f"   时间: {at}")
            report.append(f"   审批人: {by}")
            if reason:
                report.append(f"   理由: {reason}")
            if changes:
                report.append(f"   变更: {changes}")

        return "\n".join(report)
