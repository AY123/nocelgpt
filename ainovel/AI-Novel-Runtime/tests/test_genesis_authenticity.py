"""
测试 A.3 Genesis 真实性验证
"""
import pytest
from runtime.genesis.authenticity import (
    GenesisProvenance,
    ComponentProvenance,
    GenerationMethod,
    validate_genesis_authenticity,
    extract_provenance_from_outline_bootstrap,
)


def test_provenance_llm_component_count():
    """测试：统计 LLM 组件数量"""
    prov = GenesisProvenance()
    prov.add_component(ComponentProvenance("outline", GenerationMethod.LLM, "deepseek-chat", "deepseek"))
    prov.add_component(ComponentProvenance("brain", GenerationMethod.DETERMINISTIC))
    prov.add_component(ComponentProvenance("position", GenerationMethod.FALLBACK_TEMPLATE))

    assert prov.llm_component_count() == 1
    assert prov.template_component_count() == 1


def test_provenance_is_all_template():
    """测试：检测全模板项目"""
    # 全部是模板
    prov_all_template = GenesisProvenance()
    prov_all_template.add_component(ComponentProvenance("outline", GenerationMethod.FALLBACK_TEMPLATE))
    prov_all_template.add_component(ComponentProvenance("position", GenerationMethod.FALLBACK_TEMPLATE))

    assert prov_all_template.is_all_template() is True

    # 有 LLM 组件
    prov_with_llm = GenesisProvenance()
    prov_with_llm.add_component(ComponentProvenance("outline", GenerationMethod.LLM, "deepseek-chat"))
    prov_with_llm.add_component(ComponentProvenance("brain", GenerationMethod.DETERMINISTIC))

    assert prov_with_llm.is_all_template() is False

    # 只有确定性组件（不算全模板）
    prov_deterministic = GenesisProvenance()
    prov_deterministic.add_component(ComponentProvenance("brain", GenerationMethod.DETERMINISTIC))
    prov_deterministic.add_component(ComponentProvenance("position", GenerationMethod.DETERMINISTIC))

    assert prov_deterministic.is_all_template() is False


def test_provenance_has_critical_llm_component():
    """测试：检测是否有关键 LLM 组件（outline）"""
    # 有 LLM outline
    prov_with = GenesisProvenance()
    prov_with.add_component(ComponentProvenance("outline", GenerationMethod.LLM, "deepseek-chat"))

    assert prov_with.has_critical_llm_component() is True

    # outline 是模板
    prov_without = GenesisProvenance()
    prov_without.add_component(ComponentProvenance("outline", GenerationMethod.FALLBACK_TEMPLATE))

    assert prov_without.has_critical_llm_component() is False

    # 没有 outline
    prov_no_outline = GenesisProvenance()
    prov_no_outline.add_component(ComponentProvenance("brain", GenerationMethod.LLM))

    assert prov_no_outline.has_critical_llm_component() is False


def test_validate_genesis_all_template_fails():
    """测试：全模板项目验证失败"""
    prov = GenesisProvenance()
    prov.add_component(ComponentProvenance("outline", GenerationMethod.FALLBACK_TEMPLATE))
    prov.add_component(ComponentProvenance("position", GenerationMethod.FALLBACK_TEMPLATE))

    result = validate_genesis_authenticity(prov)

    assert result.valid is False
    assert len(result.issues) >= 1
    assert any("All components fell back" in issue for issue in result.issues)


def test_validate_genesis_no_llm_outline_fails():
    """测试：outline 不是 LLM 生成验证失败"""
    prov = GenesisProvenance()
    prov.add_component(ComponentProvenance("outline", GenerationMethod.FALLBACK_TEMPLATE))
    prov.add_component(ComponentProvenance("brain", GenerationMethod.DETERMINISTIC))

    result = validate_genesis_authenticity(prov)

    assert result.valid is False
    assert len(result.issues) >= 1
    assert any("Outline was not LLM-generated" in issue for issue in result.issues)


def test_validate_genesis_valid_with_llm_outline():
    """测试：有 LLM outline 验证通过"""
    prov = GenesisProvenance()
    prov.add_component(ComponentProvenance("outline", GenerationMethod.LLM, "deepseek-chat", "deepseek"))
    prov.add_component(ComponentProvenance("brain", GenerationMethod.DETERMINISTIC))
    prov.add_component(ComponentProvenance("position", GenerationMethod.DETERMINISTIC))

    result = validate_genesis_authenticity(prov)

    assert result.valid is True
    assert len(result.issues) == 0


def test_validate_genesis_warns_on_partial_template():
    """测试：部分模板发出警告但不失败"""
    prov = GenesisProvenance()
    prov.add_component(ComponentProvenance("outline", GenerationMethod.LLM, "deepseek-chat"))
    prov.add_component(ComponentProvenance("brain", GenerationMethod.DETERMINISTIC))
    prov.add_component(ComponentProvenance("position", GenerationMethod.FALLBACK_TEMPLATE, fallback_reason="API timeout"))

    result = validate_genesis_authenticity(prov)

    assert result.valid is True  # 不失败
    assert len(result.issues) == 0
    assert len(result.warnings) >= 1
    assert any("fell back to templates" in warn for warn in result.warnings)


def test_extract_provenance_from_bootstrap_deterministic():
    """测试：deterministic 模式提取来源"""
    class MockBootResult:
        ok = True
        message = "success"

    result = extract_provenance_from_outline_bootstrap(MockBootResult(), model=None)

    assert result.component_name == "outline"
    assert result.method == GenerationMethod.FALLBACK_TEMPLATE
    assert result.fallback_reason == "model=None (deterministic mode)"


def test_extract_provenance_from_bootstrap_llm_success():
    """测试：LLM 成功提取来源"""
    class MockModel:
        provider = "deepseek"
        model_id = "deepseek-chat"

    class MockBootResult:
        ok = True
        message = "success"

    result = extract_provenance_from_outline_bootstrap(MockBootResult(), model=MockModel())

    assert result.component_name == "outline"
    assert result.method == GenerationMethod.LLM
    assert result.model == "deepseek-chat"
    assert result.provider == "deepseek"


def test_extract_provenance_from_bootstrap_llm_failed():
    """测试：LLM 失败提取来源"""
    class MockModel:
        provider = "deepseek"

    class MockBootResult:
        ok = False
        message = "API timeout"

    result = extract_provenance_from_outline_bootstrap(MockBootResult(), model=MockModel())

    assert result.component_name == "outline"
    assert result.method == GenerationMethod.FALLBACK_TEMPLATE
    assert "API timeout" in result.fallback_reason


def test_provenance_to_dict():
    """测试：来源记录可序列化"""
    prov = GenesisProvenance()
    prov.add_component(ComponentProvenance("outline", GenerationMethod.LLM, "deepseek-chat", "deepseek"))
    prov.add_component(ComponentProvenance("brain", GenerationMethod.DETERMINISTIC))

    prov_dict = prov.to_dict()

    assert isinstance(prov_dict, dict)
    assert "components" in prov_dict
    assert "statistics" in prov_dict
    assert len(prov_dict["components"]) == 2
    assert prov_dict["statistics"]["llm_generated"] == 1
    assert prov_dict["statistics"]["is_all_template"] is False


def test_validation_result_to_dict():
    """测试：验证结果可序列化"""
    prov = GenesisProvenance()
    prov.add_component(ComponentProvenance("outline", GenerationMethod.LLM, "deepseek-chat"))

    result = validate_genesis_authenticity(prov)
    result_dict = result.to_dict()

    assert isinstance(result_dict, dict)
    assert "valid" in result_dict
    assert "provenance" in result_dict
    assert "issues" in result_dict
    assert "warnings" in result_dict
