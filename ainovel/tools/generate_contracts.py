#!/usr/bin/env python3
"""
章节契约生成器 - Phase 1 MVP
为Ch101-110生成写前契约
"""

import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List


class ContractGenerator:
    """契约生成器"""

    def __init__(self, output_dir: str = "contracts"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def generate_contract(
        self,
        chapter: int,
        prev_chapter_text: str = None,
        outline_ref: str = None,
        objective: str = None,
        long_arc_band: int = None
    ) -> Dict:
        """
        生成单章契约

        Args:
            chapter: 章节号
            prev_chapter_text: 上一章正文（用于提取exit_state）
            outline_ref: 大纲引用
            objective: 本章目标
            long_arc_band: 所属长弧band

        Returns:
            契约字典
        """
        # 如果有上一章，提取其exit_state
        prev_exit = None
        if prev_chapter_text and chapter > 1:
            prev_exit = self._extract_exit_state(prev_chapter_text)

        # 生成entry_state
        entry_state = self._generate_entry_state(chapter, prev_exit)

        # 生成exit_target
        exit_target = self._generate_exit_target(chapter, objective)

        # 生成transition要求
        transition = self._generate_transition(chapter, exit_target)

        # 生成契约
        contract = {
            "chapter": chapter,
            "version": "v1.0",
            "approved": False,  # 需要人工批准
            "approved_at": None,

            "entry_state": entry_state,

            "chapter_intent": {
                "objective": objective or f"Ch{chapter}目标待定义",
                "main_conflict": "待定义",
                "plot_lines": [],
                "irreversible_change": "待定义"
            },

            "exit_target": exit_target,

            "transition_to_next": transition,

            "sources": {
                "outline_ref": outline_ref,
                "long_arc_band": long_arc_band,
                "generated_at": datetime.now().isoformat(),
                "generated_from": "manual",
                "content_hash": self._compute_hash(chapter, objective)
            },

            "notes": "Phase 1 MVP - 需要人工审核和完善"
        }

        return contract

    def _extract_exit_state(self, text: str) -> Dict:
        """提取上一章的exit_state（简化版）"""
        # 实际应该用LLM提取
        # 这里返回模板
        return {
            "location_id": "loc_extracted",
            "characters_present": [],
            "unfinished_action": "",
            "hook_promise": ""
        }

    def _generate_entry_state(self, chapter: int, prev_exit: Dict = None) -> Dict:
        """生成entry_state"""
        if prev_exit:
            # 基于上一章的exit生成
            return {
                "location_id": prev_exit.get("location_id", "loc_unknown"),
                "time_relation": "immediate",  # 默认紧接
                "pov": "段奕尘",  # 默认主角视角
                "required_characters": prev_exit.get("characters_present", []),
                "hook_to_consume": f"hook_{chapter-1:03d}_01",
                "must_address": prev_exit.get("unfinished_action", "")
            }
        else:
            # 第一章或缺少上文
            return {
                "location_id": "loc_unknown",
                "time_relation": "immediate",
                "pov": "段奕尘"
            }

    def _generate_exit_target(self, chapter: int, objective: str = None) -> Dict:
        """生成exit_target"""
        return {
            "location_id": "loc_unknown",
            "time_state": "待定义",
            "characters_present": ["段奕尘"],
            "unfinished_action": "待定义",
            "hook_id": f"hook_{chapter:03d}_01",
            "hook_promise": "待定义"
        }

    def _generate_transition(self, chapter: int, exit_target: Dict) -> Dict:
        """生成transition要求"""
        return {
            "scene_continuity": "immediate",
            "location_change": False,
            "pov_change": False,
            "consume_hook_by_percent": 20
        }

    def _compute_hash(self, chapter: int, objective: str = None) -> str:
        """计算内容哈希"""
        content = f"{chapter}:{objective or ''}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def save_contract(self, contract: Dict) -> Path:
        """保存契约到文件"""
        chapter = contract["chapter"]
        filename = f"chapter_{chapter:03d}_contract.json"
        filepath = self.output_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(contract, f, ensure_ascii=False, indent=2)

        return filepath

    def generate_batch(
        self,
        start_chapter: int,
        end_chapter: int,
        prev_chapter_text: str = None
    ) -> List[Dict]:
        """
        批量生成契约

        Args:
            start_chapter: 起始章节
            end_chapter: 结束章节（包含）
            prev_chapter_text: 起始章节的上一章正文

        Returns:
            契约列表
        """
        contracts = []

        for ch in range(start_chapter, end_chapter + 1):
            print(f"生成Ch{ch}契约...")

            # 第一章使用提供的prev_text
            prev_text = prev_chapter_text if ch == start_chapter else None

            contract = self.generate_contract(
                chapter=ch,
                prev_chapter_text=prev_text,
                long_arc_band=(ch - 1) // 10 + 1
            )

            filepath = self.save_contract(contract)
            print(f"  已保存: {filepath}")

            contracts.append(contract)

        return contracts


def main():
    """主函数 - 生成Ch101-110契约"""
    print("=" * 70)
    print("契约生成器 - Phase 1 MVP")
    print("=" * 70)
    print()

    generator = ContractGenerator("contracts")

    # 读取Ch100正文作为起点
    novel_file = Path("novel-lingse-complete-100-chapters.md")

    if not novel_file.exists():
        print("❌ 未找到小说文件")
        print("   需要: novel-lingse-complete-100-chapters.md")
        return

    # 简化：不实际提取Ch100，而是生成模板契约
    print("为Ch101-110生成契约模板...")
    print()

    contracts = generator.generate_batch(
        start_chapter=101,
        end_chapter=110,
        prev_chapter_text=None  # Phase 1暂不提取
    )

    print()
    print("=" * 70)
    print("✅ 生成完成")
    print("=" * 70)
    print()
    print(f"已生成 {len(contracts)} 个契约")
    print(f"位置: contracts/")
    print()
    print("下一步:")
    print("  1. 人工审核每个契约")
    print("  2. 完善location_id、objective、hook等")
    print("  3. 设置approved=true")
    print("  4. 使用契约生成Ch101-110")
    print()


if __name__ == '__main__':
    main()
