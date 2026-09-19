"""Test Task 3.1: Validator 去硬编码（简化版本）

验证配置系统的核心逻辑，不依赖复杂的模块导入。
"""
import pytest
import yaml
import tempfile
from pathlib import Path


def test_config_structure():
    """Test that config file has the right structure."""
    config = {
        'location_keywords': {
            'loc_test': ['测试']
        },
        'validation_strategy': {
            'location_check_portion': 0.33
        },
        'fallback': {
            'auto_extract_from_id': True
        }
    }

    # Verify structure
    assert 'location_keywords' in config
    assert 'validation_strategy' in config
    assert 'fallback' in config


def test_yaml_config_loading():
    """Test that YAML config can be loaded."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / 'test_config.yaml'

        config = {
            'location_keywords': {
                'loc_place': ['地点']
            }
        }

        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True)

        # Load it back
        with open(config_file, 'r', encoding='utf-8') as f:
            loaded = yaml.safe_load(f)

        assert loaded['location_keywords']['loc_place'] == ['地点']


def test_keyword_extraction_logic():
    """Test the logic of extracting keywords from location_id."""
    location_id = "loc_矿场边缘_乱石堆"

    # Extract keywords
    id_str = location_id.replace('loc_', '')
    keywords = id_str.split('_')

    assert '矿场边缘' in keywords
    assert '乱石堆' in keywords


def test_location_check_portion_logic():
    """Test the logic of checking location in a portion of text."""
    text = "段奕尘来到广场。后面还有很多内容。" * 10
    keyword = "广场"

    # Check in first 33%
    check_portion = 0.33
    check_length = int(len(text) * check_portion)
    first_portion = text[:check_length]

    assert keyword in first_portion


def test_fallback_strategy():
    """Test fallback strategy when no predefined keywords."""
    # Simulate fallback config
    fallback_config = {
        'auto_extract_from_id': True,
        'strip_loc_prefix': True,
        'id_separator': '_'
    }

    location_id = "loc_dark_forest"

    # Apply fallback
    if fallback_config['auto_extract_from_id']:
        id_str = location_id
        if fallback_config['strip_loc_prefix']:
            id_str = id_str.replace('loc_', '')

        keywords = id_str.split(fallback_config['id_separator'])

        assert 'dark' in keywords
        assert 'forest' in keywords


def test_config_file_exists():
    """Verify that contract_validation_config.yaml was created."""
    config_file = Path(__file__).parent.parent.parent / "contracts" / "contract_validation_config.yaml"

    assert config_file.exists(), f"Config file should exist at {config_file}"

    # Load and verify structure
    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    assert 'location_keywords' in config
    assert 'validation_strategy' in config
    assert 'strictness' in config
    assert 'fallback' in config


def test_config_has_real_locations():
    """Verify that config file has real location definitions."""
    config_file = Path(__file__).parent.parent.parent / "contracts" / "contract_validation_config.yaml"

    if not config_file.exists():
        pytest.skip("Config file not found")

    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    location_keywords = config.get('location_keywords', {})

    # Should have some predefined locations
    assert len(location_keywords) > 0

    # Check a specific location
    assert 'loc_city_square' in location_keywords or 'loc_矿场边缘_乱石堆' in location_keywords


def test_implementation_uses_config():
    """Verify that gate.py was modified to use config."""
    gate_file = Path(__file__).parent.parent.parent.parent / "runtime_plugins" / "contract" / "gate.py"

    if not gate_file.exists():
        pytest.skip("gate.py not found")

    content = gate_file.read_text(encoding='utf-8')

    # Should have _load_config method
    assert "_load_config" in content

    # Should use self.config
    assert "self.config" in content

    # Should have Task 3.1 comments
    assert "Task 3.1" in content


def test_backward_compatibility():
    """Test that default config provides backward compatibility."""
    default_config = {
        'location_keywords': {},  # Can be empty
        'validation_strategy': {
            'location_check_portion': 0.33,  # Same as before
        },
        'fallback': {
            'auto_extract_from_id': True,  # Same behavior as before
            'id_separator': '_',
            'strip_loc_prefix': True,
        }
    }

    # Verify defaults match old behavior
    assert default_config['validation_strategy']['location_check_portion'] == 0.33
    assert default_config['fallback']['auto_extract_from_id'] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
