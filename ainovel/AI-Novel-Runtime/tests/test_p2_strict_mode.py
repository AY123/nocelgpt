"""
P2 测试：严格模式功能验证
"""
import pytest
import tempfile
from pathlib import Path
import json
import sys

# 添加项目路径
project_root = Path(__file__).resolve().parent.parent.parent
if not (project_root / 'runtime_plugins').exists():
    pytest.skip("runtime_plugins not found", allow_module_level=True)
sys.path.insert(0, str(project_root))

from runtime_plugins.contract import ContractGate, ContractViolationError, ChapterStatus


def test_strict_mode_disabled_by_default():
    """测试严格模式默认关闭"""
    with tempfile.TemporaryDirectory() as tmpdir:
        contracts_dir = Path(tmpdir) / "contracts"
        schemas_dir = Path(tmpdir) / "schemas"
        contracts_dir.mkdir()
        schemas_dir.mkdir()

        # 创建 schema
        schema_file = schemas_dir / "chapter_contract.schema.json"
        schema_file.write_text(json.dumps({"type": "object"}), encoding="utf-8")

        gate = ContractGate(
            contracts_dir=contracts_dir,
            schemas_dir=schemas_dir
        )
        assert gate.strict_mode is False


def test_strict_mode_enabled():
    """测试严格模式可以启用"""
    with tempfile.TemporaryDirectory() as tmpdir:
        contracts_dir = Path(tmpdir) / "contracts"
        schemas_dir = Path(tmpdir) / "schemas"
        contracts_dir.mkdir()
        schemas_dir.mkdir()

        # 创建 schema
        schema_file = schemas_dir / "chapter_contract.schema.json"
        schema_file.write_text(json.dumps({"type": "object"}), encoding="utf-8")

        gate = ContractGate(
            contracts_dir=contracts_dir,
            schemas_dir=schemas_dir,
            strict_mode=True
        )
        assert gate.strict_mode is True
        assert "confidence_threshold" in gate.strict_config


def test_strict_mode_critical_deviation_blocks():
    """测试严格模式阻断关键偏差"""
    with tempfile.TemporaryDirectory() as tmpdir:
        contracts_dir = Path(tmpdir) / "contracts"
        schemas_dir = Path(tmpdir) / "schemas"
        contracts_dir.mkdir()
        schemas_dir.mkdir()

        # 创建契约
        contract = {
            "chapter": 1,
            "exit_target": {
                "location_id": "loc_forest",
                "characters_present": ["主角"],
                "emotional_state": "determined"
            }
        }
        contract_file = contracts_dir / "chapter_001_contract.json"
        contract_file.write_text(json.dumps(contract, ensure_ascii=False), encoding="utf-8")

        # 创建 schema（空的也可以，因为我们只测试比较逻辑）
        schema_file = schemas_dir / "chapter_contract.schema.json"
        schema_file.write_text(json.dumps({"type": "object"}), encoding="utf-8")

        gate = ContractGate(
            contracts_dir=contracts_dir,
            schemas_dir=schemas_dir,
            strict_mode=True
        )

        # 实际出口有关键偏差（地点错误）
        actual_exit = {
            "chapter": 1,
            "location_id": "loc_city",  # 关键偏差
            "location_confidence": 0.9,
            "characters_present": ["主角"],
            "characters_confidence": 0.8,
            "emotional_state": "determined",
            "emotional_confidence": 0.9,
            "overall_confidence": 0.87
        }

        result = gate.compare_planned_vs_actual(1, actual_exit)

        # 验证严格模式结果
        assert "strict_mode" in result
        assert result["strict_mode"]["status"] == ChapterStatus.CONTRACT_INVALID.value
        assert result["strict_mode"]["blocked"] is True
        assert "Critical" in result["strict_mode"]["reason"]


def test_strict_mode_low_confidence_requires_review():
    """测试严格模式下低置信度需要人工审核"""
    with tempfile.TemporaryDirectory() as tmpdir:
        contracts_dir = Path(tmpdir) / "contracts"
        schemas_dir = Path(tmpdir) / "schemas"
        contracts_dir.mkdir()
        schemas_dir.mkdir()

        # 创建契约
        contract = {
            "chapter": 1,
            "exit_target": {
                "location_id": "loc_forest",
                "characters_present": ["主角"]
            }
        }
        contract_file = contracts_dir / "chapter_001_contract.json"
        contract_file.write_text(json.dumps(contract, ensure_ascii=False), encoding="utf-8")

        schema_file = schemas_dir / "chapter_contract.schema.json"
        schema_file.write_text(json.dumps({"type": "object"}), encoding="utf-8")

        gate = ContractGate(
            contracts_dir=contracts_dir,
            schemas_dir=schemas_dir,
            strict_mode=True
        )

        # 实际出口无偏差但置信度低
        actual_exit = {
            "chapter": 1,
            "location_id": "loc_forest",
            "location_confidence": 0.4,  # 低置信度
            "characters_present": ["主角"],
            "characters_confidence": 0.5,
            "overall_confidence": 0.45  # 低于阈值 0.7
        }

        result = gate.compare_planned_vs_actual(1, actual_exit)

        # 验证严格模式结果
        assert "strict_mode" in result
        assert result["strict_mode"]["status"] == ChapterStatus.REQUIRES_HUMAN_REVIEW.value
        assert result["strict_mode"]["blocked"] is True
        assert "Low confidence" in result["strict_mode"]["reason"]


def test_strict_mode_high_severity_warning():
    """测试严格模式下高级别偏差产生警告"""
    with tempfile.TemporaryDirectory() as tmpdir:
        contracts_dir = Path(tmpdir) / "contracts"
        schemas_dir = Path(tmpdir) / "schemas"
        contracts_dir.mkdir()
        schemas_dir.mkdir()

        # 创建契约
        contract = {
            "chapter": 1,
            "exit_target": {
                "location_id": "loc_forest",
                "characters_present": ["主角", "导师"],  # 计划有导师
                "hook_promise": "计划的钩子"
            }
        }
        contract_file = contracts_dir / "chapter_001_contract.json"
        contract_file.write_text(json.dumps(contract, ensure_ascii=False), encoding="utf-8")

        schema_file = schemas_dir / "chapter_contract.schema.json"
        schema_file.write_text(json.dumps({"type": "object"}), encoding="utf-8")

        gate = ContractGate(
            contracts_dir=contracts_dir,
            schemas_dir=schemas_dir,
            strict_mode=True
        )

        # 实际出口：地点正确，人物缺失导师（high），钩子不同（high），但置信度高
        actual_exit = {
            "chapter": 1,
            "location_id": "loc_forest",
            "location_confidence": 0.9,
            "characters_present": ["主角"],  # 缺少导师 -> high severity
            "characters_confidence": 0.8,
            "hook_promise": "实际的钩子",  # 不同 -> high severity
            "hook_confidence": 0.7,
            "overall_confidence": 0.8  # 高置信度
        }

        result = gate.compare_planned_vs_actual(1, actual_exit)

        # 验证严格模式结果
        assert "strict_mode" in result
        assert result["strict_mode"]["status"] == ChapterStatus.CONTRACT_WARNING.value
        assert result["strict_mode"]["blocked"] is False  # 警告不阻断
        assert "High-severity" in result["strict_mode"]["reason"]


def test_strict_mode_pass():
    """测试严格模式下完全通过"""
    with tempfile.TemporaryDirectory() as tmpdir:
        contracts_dir = Path(tmpdir) / "contracts"
        schemas_dir = Path(tmpdir) / "schemas"
        contracts_dir.mkdir()
        schemas_dir.mkdir()

        # 创建契约
        contract = {
            "chapter": 1,
            "exit_target": {
                "location_id": "loc_forest",
                "characters_present": ["主角"]
            }
        }
        contract_file = contracts_dir / "chapter_001_contract.json"
        contract_file.write_text(json.dumps(contract, ensure_ascii=False), encoding="utf-8")

        schema_file = schemas_dir / "chapter_contract.schema.json"
        schema_file.write_text(json.dumps({"type": "object"}), encoding="utf-8")

        gate = ContractGate(
            contracts_dir=contracts_dir,
            schemas_dir=schemas_dir,
            strict_mode=True
        )

        # 实际出口完全匹配且置信度高
        actual_exit = {
            "chapter": 1,
            "location_id": "loc_forest",
            "location_confidence": 0.9,
            "characters_present": ["主角"],
            "characters_confidence": 0.8,
            "overall_confidence": 0.85
        }

        result = gate.compare_planned_vs_actual(1, actual_exit)

        # 验证严格模式结果
        assert "strict_mode" in result
        assert result["strict_mode"]["status"] == ChapterStatus.PRODUCED.value
        assert result["strict_mode"]["blocked"] is False
        assert "passed" in result["strict_mode"]["reason"]


def test_non_strict_mode_no_blocking():
    """测试非严格模式不阻断"""
    with tempfile.TemporaryDirectory() as tmpdir:
        contracts_dir = Path(tmpdir) / "contracts"
        schemas_dir = Path(tmpdir) / "schemas"
        contracts_dir.mkdir()
        schemas_dir.mkdir()

        # 创建契约
        contract = {
            "chapter": 1,
            "exit_target": {
                "location_id": "loc_forest"
            }
        }
        contract_file = contracts_dir / "chapter_001_contract.json"
        contract_file.write_text(json.dumps(contract, ensure_ascii=False), encoding="utf-8")

        schema_file = schemas_dir / "chapter_contract.schema.json"
        schema_file.write_text(json.dumps({"type": "object"}), encoding="utf-8")

        gate = ContractGate(
            contracts_dir=contracts_dir,
            schemas_dir=schemas_dir,
            strict_mode=False  # 非严格模式
        )

        # 实际出口有关键偏差
        actual_exit = {
            "chapter": 1,
            "location_id": "loc_city",  # 关键偏差
            "location_confidence": 0.3,  # 低置信度
            "overall_confidence": 0.3
        }

        result = gate.compare_planned_vs_actual(1, actual_exit)

        # 验证非严格模式不添加 strict_mode 结果
        assert "strict_mode" not in result
        # 但仍然报告偏差
        assert result["critical_count"] > 0
