"""
Reader Expectation Processor - 将Reader Simulation期待反馈给下一章 (P1-3)

从Reader Simulation的期待中选择1-2个进入下一章objective，其余转为中期Promise。
"""
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from collections import Counter
import re


@dataclass
class ReaderExpectation:
    """读者期待"""
    text: str  # 期待内容
    persona: str  # 来源persona
    priority: str  # "must_satisfy" | "nice_to_have"
    category: str  # "plot" | "character" | "world" | "power" | "relationship"


class ReaderExpectationProcessor:
    """
    处理Reader Simulation的期待，转化为下章目标和中期Promise

    工作流程：
    1. 从Reader Simulation提取所有期待
    2. 聚类相似期待
    3. 去重
    4. 分类和优先级排序
    5. 选择1-2个进入下章objective
    6. 其余转为中期Promise
    """

    def __init__(self):
        # 期待分类关键词
        self.category_keywords = {
            "power": ["能力", "实力", "突破", "升级", "战力", "修炼", "境界"],
            "character": ["人物", "角色", "性格", "成长", "变化", "动机"],
            "world": ["世界", "规则", "设定", "背景", "体系"],
            "relationship": ["关系", "互动", "感情", "矛盾", "合作", "两人", "之间"],
            "plot": ["接下来", "然后", "会不会", "如何", "能否", "结局", "发展"],
        }

    def extract_expectations(
        self,
        reader_simulation: Dict[str, Any]
    ) -> List[ReaderExpectation]:
        """
        从Reader Simulation提取期待

        Args:
            reader_simulation: reader simulation结果

        Returns:
            期待列表
        """
        expectations = []

        personas = reader_simulation.get("personas", [])
        for persona in personas:
            persona_name = persona.get("name", "unknown")

            # 提取期待（假设在expectations字段中）
            persona_expectations = persona.get("expectations", [])
            if isinstance(persona_expectations, str):
                # 如果是字符串，按句子分割
                persona_expectations = [persona_expectations]

            for exp_text in persona_expectations:
                if not exp_text or not isinstance(exp_text, str):
                    continue

                # 分类
                category = self._categorize_expectation(exp_text)

                # 优先级（简单规则：包含"必须"/"一定"的是must_satisfy）
                priority = "must_satisfy" if any(
                    word in exp_text for word in ["必须", "一定", "务必", "关键"]
                ) else "nice_to_have"

                expectations.append(ReaderExpectation(
                    text=exp_text,
                    persona=persona_name,
                    priority=priority,
                    category=category,
                ))

        return expectations

    def _categorize_expectation(self, text: str) -> str:
        """对期待进行分类"""
        scores = {}
        for category, keywords in self.category_keywords.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                scores[category] = score

        if not scores:
            return "plot"  # 默认分类

        return max(scores, key=scores.get)

    def cluster_expectations(
        self,
        expectations: List[ReaderExpectation]
    ) -> List[List[ReaderExpectation]]:
        """
        聚类相似期待

        使用简单的关键词重叠度进行聚类
        """
        if not expectations:
            return []

        clusters = []
        used = set()

        for i, exp1 in enumerate(expectations):
            if i in used:
                continue

            cluster = [exp1]
            used.add(i)

            # 找到相似的期待
            for j, exp2 in enumerate(expectations):
                if j in used or j <= i:
                    continue

                if self._are_similar(exp1.text, exp2.text):
                    cluster.append(exp2)
                    used.add(j)

            clusters.append(cluster)

        return clusters

    def _are_similar(self, text1: str, text2: str, threshold: float = 0.3) -> bool:
        """判断两个期待是否相似（基于关键词重叠）"""
        # 提取关键词（简单分词）
        words1 = set(self._extract_keywords(text1))
        words2 = set(self._extract_keywords(text2))

        if not words1 or not words2:
            return False

        # Jaccard相似度
        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return (intersection / union) >= threshold if union > 0 else False

    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词（简单实现）"""
        # 移除标点
        # P0-4: Use triple quotes to avoid quote conflicts
        text = re.sub(r'''[，。！？、；：""''（）《》【】\s]+''', ' ', text)

        # 分割为词（简单按字符，实际应该用分词器）
        words = []
        for i in range(len(text) - 1):
            words.append(text[i:i+2])  # 2-gram

        return words

    def deduplicate_clusters(
        self,
        clusters: List[List[ReaderExpectation]]
    ) -> List[ReaderExpectation]:
        """
        去重：每个cluster选一个代表

        优先级：must_satisfy > nice_to_have
        """
        representatives = []

        for cluster in clusters:
            # 按优先级排序
            must_satisfy = [exp for exp in cluster if exp.priority == "must_satisfy"]
            nice_to_have = [exp for exp in cluster if exp.priority == "nice_to_have"]

            # 选择代表：优先must_satisfy，其次选最长的
            if must_satisfy:
                rep = max(must_satisfy, key=lambda e: len(e.text))
            elif nice_to_have:
                rep = max(nice_to_have, key=lambda e: len(e.text))
            else:
                rep = cluster[0]

            representatives.append(rep)

        return representatives

    def select_for_next_chapter(
        self,
        expectations: List[ReaderExpectation],
        max_objectives: int = 2
    ) -> Dict[str, Any]:
        """
        选择进入下章objective的期待

        选择策略：
        1. 优先must_satisfy
        2. 分类多样性（不全选同一类）
        3. 最多选2个

        Returns:
            {
                "next_chapter_objectives": [...],  # 进入下章的期待
                "mid_term_promises": [...],        # 转为中期Promise的期待
            }
        """
        if not expectations:
            return {
                "next_chapter_objectives": [],
                "mid_term_promises": [],
            }

        # 1. 分离must_satisfy和nice_to_have
        must_satisfy = [exp for exp in expectations if exp.priority == "must_satisfy"]
        nice_to_have = [exp for exp in expectations if exp.priority == "nice_to_have"]

        # 2. 选择下章objective
        next_chapter = []

        # 优先从must_satisfy中选
        if must_satisfy:
            # 按分类分组
            by_category = {}
            for exp in must_satisfy:
                by_category.setdefault(exp.category, []).append(exp)

            # 每个分类选一个，最多max_objectives个
            for category in sorted(by_category.keys()):
                if len(next_chapter) >= max_objectives:
                    break
                # 选该分类中最长的（假设最详细）
                next_chapter.append(max(by_category[category], key=lambda e: len(e.text)))

        # 如果still不够，从nice_to_have中补充
        if len(next_chapter) < max_objectives and nice_to_have:
            # 选择不同分类的
            used_categories = {exp.category for exp in next_chapter}

            for exp in sorted(nice_to_have, key=lambda e: len(e.text), reverse=True):
                if len(next_chapter) >= max_objectives:
                    break
                if exp.category not in used_categories:
                    next_chapter.append(exp)
                    used_categories.add(exp.category)

        # 3. 其余转为中期Promise
        selected_texts = {exp.text for exp in next_chapter}
        mid_term = [exp for exp in expectations if exp.text not in selected_texts]

        return {
            "next_chapter_objectives": [
                {
                    "text": exp.text,
                    "category": exp.category,
                    "priority": exp.priority,
                    "source_persona": exp.persona,
                }
                for exp in next_chapter
            ],
            "mid_term_promises": [
                {
                    "text": exp.text,
                    "category": exp.category,
                    "priority": exp.priority,
                    "source_persona": exp.persona,
                }
                for exp in mid_term
            ],
        }

    def process(
        self,
        reader_simulation: Dict[str, Any],
        max_objectives: int = 2
    ) -> Dict[str, Any]:
        """
        完整处理流程

        Args:
            reader_simulation: Reader Simulation结果
            max_objectives: 最多选几个进入下章objective

        Returns:
            {
                "next_chapter_objectives": [...],
                "mid_term_promises": [...],
                "processing_summary": {
                    "total_expectations": int,
                    "clusters": int,
                    "deduplicated": int,
                    "selected_for_next": int,
                    "moved_to_promises": int,
                }
            }
        """
        # 1. 提取期待
        expectations = self.extract_expectations(reader_simulation)

        if not expectations:
            return {
                "next_chapter_objectives": [],
                "mid_term_promises": [],
                "processing_summary": {
                    "total_expectations": 0,
                    "clusters": 0,
                    "deduplicated": 0,
                    "selected_for_next": 0,
                    "moved_to_promises": 0,
                }
            }

        # 2. 聚类
        clusters = self.cluster_expectations(expectations)

        # 3. 去重
        deduplicated = self.deduplicate_clusters(clusters)

        # 4. 选择
        result = self.select_for_next_chapter(deduplicated, max_objectives)

        # 5. 添加处理摘要
        result["processing_summary"] = {
            "total_expectations": len(expectations),
            "clusters": len(clusters),
            "deduplicated": len(deduplicated),
            "selected_for_next": len(result["next_chapter_objectives"]),
            "moved_to_promises": len(result["mid_term_promises"]),
        }

        return result
