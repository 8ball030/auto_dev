"""
We test the functions from utils
"""

import json
import shutil
from pathlib import Path
from typing import List

import pytest
import yaml

from auto_dev.constants import AGENT_TEMPLATE_FOLDER, DEFAULT_ENCODING
from auto_dev.utils import (
    DotAccessibleClass,
    YAMLConfigManager,
    get_logger,
    get_packages,
    get_paths,
    has_package_code_changed,
)

TEST_PACKAGES_JSON = {
    "packages/packages.json": """
{
    "dev": {
        "agent/eightballer/tmp/aea-config.yaml": "bafybeiaa3jynk3bx4uged6wye7pddkpbyr2t7avzze475vkyu2bbjeddrm"
    },
    "third_party": {
    }
}
"""
}

TEST_PACKAGE_FILE = {
    "packages/eightballer/agents/tmp/aea-config.yaml": """
agent_name: tmp
author: eightballer
version: 0.1.0
license: Apache-2.0
description: ''
aea_version: '>=1.35.0, <2.0.0'
fingerprint: {}
fingerprint_ignore_patterns: []
connections: []
contracts: []
protocols:
- open_aea/signing:1.0.0:bafybeibqlfmikg5hk4phzak6gqzhpkt6akckx7xppbp53mvwt6r73h7tk4
skills: []
default_connection: null
default_ledger: ethereum
required_ledgers:
- ethereum
default_routing: {}
connection_private_key_paths: {}
private_key_paths: {}
logging_config:
  disable_existing_loggers: false
  version: 1
dependencies:
  open-aea-ledger-ethereum: {}
"""
}


def test_get_logger():
    """Test get_logger."""
    log = get_logger()
    assert log.level == 20


def test_get_packages(test_packages_filesystem):
    """Test get_packages."""
    del test_packages_filesystem
    packages = get_packages()
    assert len(packages) == 1


def test_has_package_code_changed_true(test_packages_filesystem):
    """
    Test has_package_code_changed.
    """
    with open(Path(test_packages_filesystem) / Path("packages/test_file.txt"), "w", encoding=DEFAULT_ENCODING) as file:
        file.write("test")
    assert has_package_code_changed(Path("packages"))


@pytest.fixture
def autonomy_fs(test_packages_filesystem):
    """
    Test get_paths.
    """
    Path(list(TEST_PACKAGES_JSON.keys()).pop())
    for key, value in TEST_PACKAGES_JSON.items():
        key_path = Path(test_packages_filesystem) / Path(key)
        if key_path.exists():
            shutil.rmtree(key_path, ignore_errors=True)
        if not key_path.parent.exists():
            key_path.parent.mkdir(parents=True)
        with open(key_path, "w", encoding=DEFAULT_ENCODING) as path:
            path.write(value)

    for data_file in [
        TEST_PACKAGE_FILE,
    ]:
        for file_name, data in data_file.items():
            file_path = Path(test_packages_filesystem) / Path(file_name)
            if not file_path.parent.exists():
                file_path.parent.mkdir(parents=True)
            with open(file_path, "w", encoding=DEFAULT_ENCODING) as path:
                path.write(json.dumps(data))
    yield test_packages_filesystem


def test_get_paths_changed_only(test_packages_filesystem):
    """
    Test get_paths.
    """
    assert test_packages_filesystem == str(Path.cwd())
    assert len(get_paths(changed_only=True)) == 0


def test_get_paths(test_packages_filesystem):
    """
    Test get_paths.
    """
    assert test_packages_filesystem == str(Path.cwd())
    assert len(get_paths()) == 0


class TestYAMLConfigManager:
    """TestYAMLConfigManager"""

    templates: DotAccessibleClass
    expected: str

    def setup(self):
        """Setup"""
        self.templates = DotAccessibleClass({f.name: f for f in Path(AGENT_TEMPLATE_FOLDER).glob("*")})
        self.expected = "\n---\n".join(self.raw_configs)

    @property
    def str_paths(self) -> List[str]:
        """string paths"""
        return [self.templates.abci_connection, self.templates.prometheus_connection]

    @property
    def paths(self) -> List[Path]:
        """Paths"""
        return list(map(Path, self.str_paths))

    @property
    def raw_configs(self) -> List[str]:
        """Raw config content"""
        return [path.read_text(encoding=DEFAULT_ENCODING) for path in self.paths]

    def test_yaml_config_manager_append_from_different_types(self):
        """Test YAMLConfigManager.append"""

        for configs in (self.str_paths, self.paths, self.raw_configs):
            manager = YAMLConfigManager()
            for config in configs:
                manager.append(config)
            assert len(manager) == 2
            assert str(manager) == self.expected

    def test_yaml_config_manipulation(self):
        """Test yaml config manipulation"""

        manager = YAMLConfigManager(*self.str_paths)
        abci_config = manager[0]
        assert abci_config.config.port == "${int:26658}"

        abci_config.config.port = "1234"
        assert "1234" in str(abci_config)

    def test_yaml_config_manager_invalid_yaml(self):
        """Test initializing YAMLConfigManager with invalid YAML content."""

        invalid_yaml = "invalid_yaml_here: ]]]"
        with pytest.raises(yaml.YAMLError):
            YAMLConfigManager(invalid_yaml)

    def test_yaml_config_manager_nonexistent_paths(self):
        """Test initializing YAMLConfigManager with non-existent file paths."""

        nonexistent_paths = ["nonexistent1.yaml", "nonexistent2.yaml"]
        with pytest.raises(FileNotFoundError):
            YAMLConfigManager(*nonexistent_paths)
