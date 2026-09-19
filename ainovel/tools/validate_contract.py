#!/usr/bin/env python3
"""
章节契约验证器 - Phase 1 MVP
验证章节是否满足写前契约
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple


class ContractValidator:
    """契约验证器"""

    def __init__(self, contracts_dir: str = "contracts"):
        self.contracts_dir = Path(contracts_dir)

    def load_contract(self, chapter: int) -> Dict:
        """加载章节契约"""
        contract_file = self.contracts_dir / f"chapter_{chapter:03d}_contract.json"

        if not contract_file.exists():
            return None

        with open(contract_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def extract_entry_state(self, text: str) -> Dict:
        """
        提取实际入口状态（前20%）

        简化版：提取前500字的基本信息
        """
        # 取前500字
        opening = text[:500]

        # 简单提取（实际应用中会用LLM）
        return {
            "location": self._extract_location(opening),
            "pov": self._extract_pov(opening),
            "characters": self._extract_characters(opening)
        }

    def extract_exit_state(self, text: str) -> Dict:
        """
        提取实际出口状态（最后300字）
        """
        ending = text[-300:]

        return {
            "location": self._extract_location(ending),
            "characters": self._extract_characters(ending),
            "unfinished": ending[-100:] if ending else ""
        }

    def _extract_location(self, text: str) -> str:
        """
        提取地点（改进版）

        尝试从文本中提取地点并映射到location_id
        """
        # 地点关键词映射
        location_patterns = {
            "loc_矿场边缘_乱石堆": ["矿场边缘", "乱石堆"],
            "loc_矿场_秘密通道入口": ["秘密通道入口", "通道入口"],
            "loc_秘密通道_第一层深处": ["通道深处", "第一层", "通道内"],
            "loc_秘密通道_第二层入口": ["第二层", "石门"],
            "loc_赤曜矿脉_地宫外": ["地宫外", "矿脉"],
        }

        # 匹配地点
        for loc_id, keywords in location_patterns.items():
            if any(kw in text for kw in keywords):
                return loc_id

        # 未匹配到，返回通用提取
        return "loc_unknown"

    def _extract_pov(self, text: str) -> str:
        """提取视角人物（简化版）"""
        # 简化：检查开头是否有常见主角名
        if "段奕尘" in text[:100]:
            return "段奕尘"
        return "unknown"

    def _extract_characters(self, text: str) -> List[str]:
        """提取在场角色（简化版）"""
        characters = []
        common_chars = ["段奕尘", "镜见川", "荧惑", "二叔"]

        for char in common_chars:
            if char in text:
                characters.append(char)

        return characters

    def validate_transition(
        self,
        prev_chapter: int,
        next_chapter: int,
        prev_text: str,
        next_text: str
    ) -> Dict:
        """
        验证相邻章节的过渡

        返回：
        {
            "valid": bool,
            "hard_errors": [],  # 硬错误（阻止发布）
            "soft_issues": []   # 软问题（提醒）
        }
        """
        # 加载契约
        next_contract = self.load_contract(next_chapter)

        if not next_contract:
            return {
                "valid": False,
                "hard_errors": [f"Ch{next_chapter}缺少写前契约"],
                "soft_issues": []
            }

        # 检查是否已批准
        if not next_contract.get("approved"):
            return {
                "valid": False,
                "hard_errors": [f"Ch{next_chapter}契约未批准"],
                "soft_issues": []
            }

        hard_errors = []
        soft_issues = []

        # 提取实际状态
        prev_exit = self.extract_exit_state(prev_text)
        next_entry = self.extract_entry_state(next_text)

        # 获取契约要求
        entry_state = next_contract.get("entry_state", {})

        # 验证1: 地点连续性
        location_error = self._validate_location(
            entry_state,
            prev_exit,
            next_entry,
            next_text
        )
        if location_error:
            hard_errors.append(location_error)

        # 验证2: 时间连续性
        time_error = self._validate_time(
            entry_state,
            next_text
        )
        if time_error:
            hard_errors.append(time_error)

        # 验证3: 视角连续性
        pov_error = self._validate_pov(
            entry_state,
            next_entry,
            next_text
        )
        if pov_error:
            hard_errors.append(pov_error)

        # 验证4: 钩子消费
        hook_issue = self._validate_hook_consumption(
            next_contract,
            prev_text,
            next_text
        )
        if hook_issue:
            soft_issues.append(hook_issue)

        return {
            "valid": len(hard_errors) == 0,
            "hard_errors": hard_errors,
            "soft_issues": soft_issues
        }

    def _validate_location(
        self,
        entry_state: Dict,
        prev_exit: Dict,
        next_entry: Dict,
        next_text: str
    ) -> str:
        """验证地点连续性"""
        required_location = entry_state.get("location_id")

        if not required_location:
            return None

        # 提取下一章实际地点
        actual_location = self._extract_location(next_text[:500])

        # 场景转换标记
        transition_markers = [
            "与此同时", "另一边", "此时", "同时",
            "回到", "转场", "镜头切换", "场景切换"
        ]

        has_transition = any(marker in next_text[:200] for marker in transition_markers)

        # 检查地点是否匹配
        if required_location != actual_location and actual_location != "loc_unknown":
            # 如果地点不匹配，检查是否有转场说明
            if not has_transition:
                return f"契约要求地点{required_location}，实际为{actual_location}，缺少转场说明"

        # 如果契约要求immediate但有转场标记
        scene_continuity = entry_state.get("time_relation")
        if scene_continuity == "immediate" and has_transition:
            return f"契约要求immediate连续，但文本有场景转换标记"

        return None

    def _validate_time(self, entry_state: Dict, next_text: str) -> str:
        """验证时间连续性"""
        time_relation = entry_state.get("time_relation")

        if time_relation == "immediate":
            # 检查是否有时间倒退标记
            backward_markers = ["早些时候", "之前", "回溯", "闪回"]

            for marker in backward_markers:
                if marker in next_text[:200]:
                    return f"契约要求immediate，但文本包含时间倒退标记: {marker}"

        elif time_relation == "flashback":
            # 必须有明确的闪回标记
            flashback_markers = ["回忆", "闪回", "那时", "当年"]

            if not any(marker in next_text[:200] for marker in flashback_markers):
                return "契约标记为flashback，但文本缺少闪回标记"

        return None

    def _validate_pov(
        self,
        entry_state: Dict,
        next_entry: Dict,
        next_text: str
    ) -> str:
        """验证视角连续性"""
        required_pov = entry_state.get("pov")
        actual_pov = next_entry.get("pov")

        if required_pov and actual_pov:
            if required_pov != actual_pov and actual_pov != "unknown":
                # 检查是否有明确的视角切换说明
                pov_markers = ["视角转向", "镜头转向", f"回到{required_pov}"]

                if not any(marker in next_text[:300] for marker in pov_markers):
                    return f"契约要求POV={required_pov}，实际={actual_pov}，缺少切换说明"

        return None

    def _validate_hook_consumption(
        self,
        contract: Dict,
        prev_text: str,
        next_text: str
    ) -> str:
        """验证钩子消费（软检查）"""
        entry_state = contract.get("entry_state", {})
        hook_to_consume = entry_state.get("hook_to_consume")
        must_address = entry_state.get("must_address")

        if not must_address:
            return None

        # 计算前20%位置
        consume_percent = contract.get("transition_to_next", {}).get("consume_hook_by_percent", 20)
        checkpoint = int(len(next_text) * consume_percent / 100)
        opening = next_text[:checkpoint]

        # 简化检查：关键词是否出现
        # 实际应该用LLM判断是否真正回应了钩子
        keywords = self._extract_keywords(must_address)

        found = any(kw in opening for kw in keywords)

        if not found:
            return f"钩子可能未在前{consume_percent}%消费: {must_address[:50]}..."

        return None

    def _extract_keywords(self, text: str) -> List[str]:
        """
        提取关键词（改进版）

        从文本中提取2-4字的关键词
        """
        import re

        # 移除标点
        text = re.sub(r'[，。！？；：""''（）【】《》、]', ' ', text)

        # 分词（简单按空格和长度）
        words = []
        for segment in text.split():
            # 提取2-4字的片段
            for i in range(len(segment)):
                for length in [2, 3, 4]:
                    if i + length <= len(segment):
                        word = segment[i:i+length]
                        if len(word) >= 2:
                            words.append(word)

        # 去重并取前10个
        return list(dict.fromkeys(words))[:10]


def main():
    """测试验证器"""
    print("=" * 70)
    print("契约验证器 - Phase 1 MVP")
    print("=" * 70)
    print()

    validator = ContractValidator()

    # 示例：验证Ch94
    # （实际使用时会从文件加载）

    print("✅ 验证器已就绪")
    print()
    print("使用方法:")
    print("  validator = ContractValidator('contracts/')")
    print("  result = validator.validate_transition(93, 94, prev_text, next_text)")
    print()
    print("返回格式:")
    print("  {")
    print("    'valid': True/False,")
    print("    'hard_errors': [],  # 阻止发布")
    print("    'soft_issues': []   # 提醒")
    print("  }")
    print()


if __name__ == '__main__':
    main()
