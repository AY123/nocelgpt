"""
章节契约插件

提供契约加载、验证和门禁功能
"""

from .gate import ContractGate, ContractCheckError, ContractViolationError, ChapterStatus

__all__ = ['ContractGate', 'ContractCheckError', 'ContractViolationError', 'ChapterStatus']
