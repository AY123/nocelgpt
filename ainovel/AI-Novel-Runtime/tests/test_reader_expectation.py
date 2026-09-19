"""
测试 Reader Expectation Processor (P1-3)
"""
import pytest
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from runtime.reader_expectation import (
    ReaderExpectationProcessor,
    ReaderExpectation,
)


def test_extract_expectations():
    """测试提取期待"""
    processor = ReaderExpectationProcessor()

    reader_simulation = {
        "personas": [
            {
                "name": "情节党",
                "expectations": ["想知道主角接下来如何突破", "期待看到反派的真实身份"],
            },
            {
                "name": "爽点追求者",
                "expectations": ["希望看到主角展示新能力"],
            },
        ]
    }

    expectations = processor.extract_expectations(reader_simulation)

    assert len(expectations) == 3
    assert expectations[0].persona == "情节党"
    assert "突破" in expectations[0].text
    assert expectations[0].category in ["plot", "power"]


def test_categorize_expectation():
    """测试期待分类"""
    processor = ReaderExpectationProcessor()

    assert processor._categorize_expectation("想知道主角接下来的能力突破") == "power"
    assert processor._categorize_expectation("期待看到角色成长") == "character"
    assert processor._categorize_expectation("想了解世界规则") == "world"
    assert processor._categorize_expectation("希望看到两人关系发展") == "relationship"


def test_cluster_expectations():
    """测试聚类相似期待"""
    processor = ReaderExpectationProcessor()

    expectations = [
        ReaderExpectation("想知道主角如何突破", "persona1", "nice_to_have", "power"),
        ReaderExpectation("期待主角实力提升", "persona2", "nice_to_have", "power"),
        ReaderExpectation("希望看到反派身份", "persona3", "nice_to_have", "plot"),
    ]

    clusters = processor.cluster_expectations(expectations)

    # 前两个应该聚在一起（都关于主角实力）
    assert len(clusters) >= 2


def test_deduplicate_clusters():
    """测试去重"""
    processor = ReaderExpectationProcessor()

    clusters = [
        [
            ReaderExpectation("想知道主角如何突破", "persona1", "nice_to_have", "power"),
            ReaderExpectation("期待主角实力提升", "persona2", "must_satisfy", "power"),
        ],
        [
            ReaderExpectation("希望看到反派身份", "persona3", "nice_to_have", "plot"),
        ],
    ]

    representatives = processor.deduplicate_clusters(clusters)

    assert len(representatives) == 2
    # 第一个cluster应该选must_satisfy的
    assert representatives[0].priority == "must_satisfy"


def test_select_for_next_chapter():
    """测试选择下章objective"""
    processor = ReaderExpectationProcessor()

    expectations = [
        ReaderExpectation("必须看到主角突破", "persona1", "must_satisfy", "power"),
        ReaderExpectation("希望了解反派动机", "persona2", "nice_to_have", "plot"),
        ReaderExpectation("期待角色成长", "persona3", "nice_to_have", "character"),
    ]

    result = processor.select_for_next_chapter(expectations, max_objectives=2)

    assert len(result["next_chapter_objectives"]) <= 2
    assert len(result["mid_term_promises"]) >= 1

    # must_satisfy应该被选中
    selected_texts = [obj["text"] for obj in result["next_chapter_objectives"]]
    assert "必须看到主角突破" in selected_texts


def test_select_diversity():
    """测试选择多样性"""
    processor = ReaderExpectationProcessor()

    expectations = [
        ReaderExpectation("主角能力提升", "persona1", "must_satisfy", "power"),
        ReaderExpectation("主角突破瓶颈", "persona2", "must_satisfy", "power"),
        ReaderExpectation("角色关系发展", "persona3", "must_satisfy", "relationship"),
    ]

    result = processor.select_for_next_chapter(expectations, max_objectives=2)

    # 应该选择不同分类的
    categories = [obj["category"] for obj in result["next_chapter_objectives"]]
    assert len(set(categories)) == 2  # 两个不同分类


def test_process_complete():
    """测试完整处理流程"""
    processor = ReaderExpectationProcessor()

    reader_simulation = {
        "personas": [
            {
                "name": "情节党",
                "expectations": ["想知道主角接下来如何突破实力", "期待看到反派的真实目的"],
            },
            {
                "name": "爽点追求者",
                "expectations": ["必须看到主角展示新能力", "希望有爽快的战斗"],
            },
            {
                "name": "人设粉",
                "expectations": ["期待角色成长和变化"],
            },
        ]
    }

    result = processor.process(reader_simulation, max_objectives=2)

    assert "next_chapter_objectives" in result
    assert "mid_term_promises" in result
    assert "processing_summary" in result

    summary = result["processing_summary"]
    assert summary["total_expectations"] == 5
    assert summary["selected_for_next"] <= 2
    assert summary["selected_for_next"] + summary["moved_to_promises"] <= summary["deduplicated"]


def test_process_empty():
    """测试空输入"""
    processor = ReaderExpectationProcessor()

    reader_simulation = {"personas": []}

    result = processor.process(reader_simulation)

    assert result["next_chapter_objectives"] == []
    assert result["mid_term_promises"] == []
    assert result["processing_summary"]["total_expectations"] == 0


def test_priority_must_satisfy():
    """测试must_satisfy优先级"""
    processor = ReaderExpectationProcessor()

    expectations = [
        ReaderExpectation("一般期待1", "persona1", "nice_to_have", "power"),
        ReaderExpectation("必须看到的内容", "persona2", "must_satisfy", "plot"),
        ReaderExpectation("一般期待2", "persona3", "nice_to_have", "character"),
    ]

    result = processor.select_for_next_chapter(expectations, max_objectives=2)

    # must_satisfy应该优先被选中
    selected_texts = [obj["text"] for obj in result["next_chapter_objectives"]]
    assert "必须看到的内容" in selected_texts


def test_extract_keywords():
    """测试关键词提取"""
    processor = ReaderExpectationProcessor()

    keywords = processor._extract_keywords("主角如何突破实力")

    assert len(keywords) > 0
    assert isinstance(keywords, list)


def test_are_similar():
    """测试相似度判断"""
    processor = ReaderExpectationProcessor()

    # 相似的（调整阈值，因为2-gram可能导致相似度较低）
    # "主角如何突破"和"主角能否突破"的2-gram有重叠，但可能不到30%
    assert processor._are_similar("主角如何突破实力", "主角能否突破实力") is True

    # 不相似的
    assert processor._are_similar("主角突破", "反派身份") is False
