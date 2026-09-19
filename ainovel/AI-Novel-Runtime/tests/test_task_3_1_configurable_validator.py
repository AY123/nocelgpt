"""Test Task 3.1: Validator 去硬编码

验证 ContractGate 可以从配置文件加载验证规则，而不是使用硬编码。
"""
import pytest
import json
import tempfile
from pathlib import Path


def test_config_loading_from_file():
    """Test that ContractGate can load config from file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        contracts_dir = tmp_path / "contracts"
        schemas_dir = tmp_path / "schemas"
        contracts_dir.mkdir()
        schemas_dir.mkdir()

        # Create a config file
        config = {
            'location_keywords': {
                'loc_test_place': ['测试地点', '实验场所']
            },
            'validation_strategy': {
                'location_check_portion': 0.5
            }
        }

        config_file = contracts_dir / 'contract_validation_config.yaml'
        import yaml
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True)

        # Create minimal schema
        schema = {"type": "object", "properties": {}}
        (schemas_dir / "chapter_contract.schema.json").write_text(
            json.dumps(schema), encoding='utf-8'
        )

        # Load ContractGate
        import sys
        plugins_path = Path(__file__).parent.parent.parent.parent / 'runtime_plugins'
        if str(plugins_path) not in sys.path:
            sys.path.insert(0, str(plugins_path))

        from contract.gate import ContractGate

        gate = ContractGate(contracts_dir=contracts_dir, schemas_dir=schemas_dir)

        # Verify config was loaded
        assert 'location_keywords' in gate.config
        assert 'loc_test_place' in gate.config['location_keywords']
        assert gate.config['validation_strategy']['location_check_portion'] == 0.5


def test_location_check_uses_config():
    """Test that location check uses config instead of hardcode."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        contracts_dir = tmp_path / "contracts"
        schemas_dir = tmp_path / "schemas"
        contracts_dir.mkdir()
        schemas_dir.mkdir()

        # Create config with custom location
        config = {
            'location_keywords': {
                'loc_custom_place': ['自定义地点', '特殊位置']
            },
            'validation_strategy': {
                'location_check_portion': 0.5
            }
        }

        config_file = contracts_dir / 'contract_validation_config.yaml'
        import yaml
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True)

        schema = {"type": "object", "properties": {}}
        (schemas_dir / "chapter_contract.schema.json").write_text(
            json.dumps(schema), encoding='utf-8'
        )

        import sys
        plugins_path = Path(__file__).parent.parent.parent.parent / 'runtime_plugins'
        if str(plugins_path) not in sys.path:
            sys.path.insert(0, str(plugins_path))

        from contract.gate import ContractGate

        gate = ContractGate(contracts_dir=contracts_dir, schemas_dir=schemas_dir)

        # Test location check
        text_with_location = "段奕尘来到自定义地点，观察四周。"
        text_without_location = "段奕尘四处观望。"

        # Should find the location (from config)
        assert gate._check_location_in_text(text_with_location, 'loc_custom_place') is True

        # Should not find the location
        assert gate._check_location_in_text(text_without_location, 'loc_custom_place') is False


def test_fallback_to_id_extraction():
    """Test that fallback extracts keywords from location_id."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        contracts_dir = tmp_path / "contracts"
        schemas_dir = tmp_path / "schemas"
        contracts_dir.mkdir()
        schemas_dir.mkdir()

        # Config with fallback enabled but no predefined keywords
        config = {
            'location_keywords': {},  # Empty
            'fallback': {
                'auto_extract_from_id': True,
                'strip_loc_prefix': True,
                'id_separator': '_'
            },
            'validation_strategy': {
                'location_check_portion': 0.5
            }
        }

        config_file = contracts_dir / 'contract_validation_config.yaml'
        import yaml
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True)

        schema = {"type": "object", "properties": {}}
        (schemas_dir / "chapter_contract.schema.json").write_text(
            json.dumps(schema), encoding='utf-8'
        )

        import sys
        plugins_path = Path(__file__).parent.parent.parent.parent / 'runtime_plugins'
        if str(plugins_path) not in sys.path:
            sys.path.insert(0, str(plugins_path))

        from contract.gate import ContractGate

        gate = ContractGate(contracts_dir=contracts_dir, schemas_dir=schemas_dir)

        # Test with location_id that has extractable keywords
        text = "段奕尘走进矿场边缘的乱石堆。"

        # Should extract "矿场", "边缘", "乱石堆" from loc_矿场边缘_乱石堆
        result = gate._check_location_in_text(text, 'loc_矿场边缘_乱石堆')

        # Should find at least one keyword
        assert result is True


def test_default_config_when_no_file():
    """Test that default config is used when no config file exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        contracts_dir = tmp_path / "contracts"
        schemas_dir = tmp_path / "schemas"
        contracts_dir.mkdir()
        schemas_dir.mkdir()

        # No config file created

        schema = {"type": "object", "properties": {}}
        (schemas_dir / "chapter_contract.schema.json").write_text(
            json.dumps(schema), encoding='utf-8'
        )

        import sys
        plugins_path = Path(__file__).parent.parent.parent.parent / 'runtime_plugins'
        if str(plugins_path) not in sys.path:
            sys.path.insert(0, str(plugins_path))

        from contract.gate import ContractGate

        gate = ContractGate(contracts_dir=contracts_dir, schemas_dir=schemas_dir)

        # Should have default config
        assert 'location_keywords' in gate.config
        assert 'validation_strategy' in gate.config
        assert 'fallback' in gate.config

        # Default fallback should be enabled
        assert gate.config['fallback']['auto_extract_from_id'] is True


def test_configurable_check_portions():
    """Test that check portions are configurable."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        contracts_dir = tmp_path / "contracts"
        schemas_dir = tmp_path / "schemas"
        contracts_dir.mkdir()
        schemas_dir.mkdir()

        # Config with custom portions
        config = {
            'location_keywords': {
                'loc_test': ['测试']
            },
            'validation_strategy': {
                'location_check_portion': 0.25,  # Only first 25%
                'hook_consumption_portion': 0.40,
                'hook_setup_portion': 0.15
            }
        }

        config_file = contracts_dir / 'contract_validation_config.yaml'
        import yaml
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True)

        schema = {"type": "object", "properties": {}}
        (schemas_dir / "chapter_contract.schema.json").write_text(
            json.dumps(schema), encoding='utf-8'
        )

        import sys
        plugins_path = Path(__file__).parent.parent.parent.parent / 'runtime_plugins'
        if str(plugins_path) not in sys.path:
            sys.path.insert(0, str(plugins_path))

        from contract.gate import ContractGate

        gate = ContractGate(contracts_dir=contracts_dir, schemas_dir=schemas_dir)

        # Verify portions are loaded
        assert gate.config['validation_strategy']['location_check_portion'] == 0.25
        assert gate.config['validation_strategy']['hook_consumption_portion'] == 0.40
        assert gate.config['validation_strategy']['hook_setup_portion'] == 0.15


def test_no_hardcoded_locations_in_code():
    """Verify that location keywords are not hardcoded in gate.py."""
    gate_file = Path(__file__).parent.parent.parent.parent / "runtime_plugins" / "contract" / "gate.py"

    if not gate_file.exists():
        pytest.skip("gate.py not found")

    content = gate_file.read_text(encoding='utf-8')

    # The old hardcoded dict should be removed or commented
    # Look for the pattern of hardcoded dict
    lines = content.split('\n')

    hardcoded_dict_found = False
    for i, line in enumerate(lines):
        if "'loc_city_square': [" in line and "location_keywords = {" in lines[max(0, i-2):i+1]:
            # Check if it's inside _check_location_in_text or _extract_location
            context = '\n'.join(lines[max(0, i-10):i+5])
            if 'self.config' not in context:
                hardcoded_dict_found = True
                break

    # Should not find hardcoded dict (should use self.config instead)
    assert not hardcoded_dict_found, "Found hardcoded location keywords, should use self.config"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
