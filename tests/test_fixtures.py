"""module contains tests for the pytest fixtures."""

from pathlib import Path

import yaml


def test_dummy_agent_tim(dummy_agent_tim):
    """Test fixture for dummy agent tim."""
    assert dummy_agent_tim
    config_path = Path.cwd() / "aea-config.yaml"
    assert config_path.exists()
    config = list(yaml.safe_load_all(config_path.read_text(encoding="utf-8")))[0]
    assert config["agent_name"] == "tim"
