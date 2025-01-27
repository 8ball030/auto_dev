"""module contains tests for the pytest fixtures."""

from pathlib import Path

import yaml

from auto_dev.constants import DEFAULT_AUTHOR, DEFAULT_AGENT_NAME


def test_dummy_agent_tim(dummy_agent_tim):
    """Test fixture for dummy agent tim."""
    assert dummy_agent_tim
    config_path = Path.cwd() / "aea-config.yaml"
    assert config_path.exists()
    config = next(iter(yaml.safe_load_all(config_path.read_text(encoding="utf-8"))))
    assert config["agent_name"] == DEFAULT_AGENT_NAME
    assert config["author"] == DEFAULT_AUTHOR
