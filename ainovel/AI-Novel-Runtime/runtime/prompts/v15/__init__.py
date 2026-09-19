"""
Prompt v15 - 契约注入版本

v15在v5基础上添加章节契约注入功能。
通过Contract Gate确保每章生成前有明确的入口/出口契约。
"""

from .chapter import render_chapter_prompt_v15

__all__ = ['render_chapter_prompt_v15']
