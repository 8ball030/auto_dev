"""
We test the functions from utils
"""

import json
import shutil
import tempfile
from pathlib import Path

import pytest

from auto_dev.constants import DEFAULT_ENCODING
from auto_dev.utils import (
    folder_swapper,
    get_logger,
    get_packages,
    get_paths,
    has_package_code_changed,
    remove_prefix,
    remove_suffix,
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


def test_remove_prefix():
    """Test remove_prefix"""

    assert remove_prefix("HelloWorld", "Hello") == "World"
    assert remove_prefix("PythonIsGreat", "Python") == "IsGreat"
    assert remove_prefix("abcdef", "xyz") == "abcdef"
    assert remove_prefix("abc", "") == "abc"
    assert remove_prefix("", "xyz") == ""


def test_remove_suffix():
    """Test remove_suffix"""

    assert remove_suffix("HelloWorld", "World") == "Hello"
    assert remove_suffix("PythonIsGreat", "Great") == "PythonIs"
    assert remove_suffix("abcdef", "xyz") == "abcdef"
    assert remove_suffix("abc", "") == "abc"
    assert remove_suffix("", "xyz") == ""


class TestFolderSwapper:
    """TestFolderSwapper"""

    @classmethod
    def setup_class(cls):
        """Setup class"""
        cls.temp_dir = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        cls.a_dir = Path(tempfile.mkdtemp(dir=cls.temp_dir.name))
        cls.b_dir = Path(tempfile.mkdtemp(dir=cls.temp_dir.name))
        cls.a_file_path = cls.a_dir / "test_file.txt"
        cls.a_file_path.write_text("dummy data")
        cls.b_file_path = cls.b_dir / "test_file.txt"

    def test_folder_swapper(self):
        """
        Test the folder_swapper custom context manager.
        """
        assert self.a_file_path.is_file()
        assert not self.b_file_path.exists()

        with folder_swapper(self.a_dir, self.b_dir):
            assert self.b_file_path.is_file()

        assert self.a_file_path.is_file()
        assert not self.b_file_path.exists()

    def test_folder_swapper_execution_raises(self):
        """
        Test the folder_swapper custom context manager restores on raise.
        """
        assert self.a_file_path.is_file()
        assert not self.b_file_path.exists()

        try:
            with folder_swapper(self.a_dir, self.b_dir):
                raise ZeroDivisionError("Whoops!")
        except ZeroDivisionError:
            pass

        assert self.a_file_path.is_file()
        assert not self.b_file_path.exists()
