"""We test the functions from utils."""

import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import yaml
import pytest
import rich_click as click

from auto_dev.enums import FileType
from auto_dev.utils import (
    get_paths,
    get_logger,
    get_packages,
    load_aea_ctx,
    remove_prefix,
    remove_suffix,
    write_to_file,
    folder_swapper,
    has_package_code_changed,
)
from auto_dev.constants import DEFAULT_ENCODING


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
    """Test has_package_code_changed."""
    with open(Path(test_packages_filesystem) / Path("packages/test_file.txt"), "w", encoding=DEFAULT_ENCODING) as file:
        file.write("test")
    assert has_package_code_changed(Path("packages"))


@pytest.fixture
def autonomy_fs(test_packages_filesystem):
    """Test get_paths."""
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
    return test_packages_filesystem


def test_get_paths_changed_only(test_packages_filesystem):
    """Test get_paths."""
    assert test_packages_filesystem == str(Path.cwd())
    assert len(get_paths(changed_only=True)) == 0


def test_get_paths(test_packages_filesystem):
    """Test get_paths."""
    assert test_packages_filesystem == str(Path.cwd())
    assert len(get_paths()) == 0


def test_remove_prefix():
    """Test remove_prefix."""

    assert remove_prefix("HelloWorld", "Hello") == "World"
    assert remove_prefix("PythonIsGreat", "Python") == "IsGreat"
    assert remove_prefix("abcdef", "xyz") == "abcdef"
    assert remove_prefix("abc", "") == "abc"
    assert remove_prefix("", "xyz") == ""


def test_remove_suffix():
    """Test remove_suffix."""

    assert remove_suffix("HelloWorld", "World") == "Hello"
    assert remove_suffix("PythonIsGreat", "Great") == "PythonIs"
    assert remove_suffix("abcdef", "xyz") == "abcdef"
    assert remove_suffix("abc", "") == "abc"
    assert remove_suffix("", "xyz") == ""


class TestFolderSwapper:
    """TestFolderSwapper."""

    @classmethod
    def setup_class(cls) -> None:
        """Setup the class."""
        cls.temp_dir = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        cls.a_dir = Path(tempfile.mkdtemp(dir=cls.temp_dir.name))
        cls.b_dir = Path(tempfile.mkdtemp(dir=cls.temp_dir.name))
        cls.a_file_path = cls.a_dir / "test_file.txt"
        cls.a_file_path.write_text("dummy data")
        cls.b_file_path = cls.b_dir / "test_file.txt"

    def test_folder_swapper(self):
        """Test the folder_swapper custom context manager."""
        assert self.a_file_path.is_file()
        assert not self.b_file_path.exists()

        with folder_swapper(self.a_dir, self.b_dir):
            assert self.b_file_path.is_file()

        assert self.a_file_path.is_file()
        assert not self.b_file_path.exists()

    def test_folder_swapper_execution_raises(self):
        """Test the folder_swapper custom context manager restores on raise."""
        assert self.a_file_path.is_file()
        assert not self.b_file_path.exists()

        try:
            with folder_swapper(self.a_dir, self.b_dir):
                msg = "Whoops!"
                raise ZeroDivisionError(msg)
        except ZeroDivisionError as exc:
            assert str(exc) == msg
        assert self.a_file_path.is_file()
        assert not self.b_file_path.exists()


def test_load_aea_ctx(dummy_agent_tim):
    """Test load_aea_ctx."""

    assert dummy_agent_tim

    def mock_func(ctx, *args, **kwargs):
        return ctx, args, kwargs  # pylint: disable=C3001

    mock_context = MagicMock(spec=click.Context)

    decorated_func = load_aea_ctx(mock_func)
    result = decorated_func(mock_context, "arg1", "arg2", kwarg1="value1", kwarg2="value2")

    ctx, args, kwargs = result
    assert ctx.aea_ctx.agent_config.name == "tim"
    assert args == ("arg1", "arg2")
    assert kwargs == {"kwarg1": "value1", "kwarg2": "value2"}


def test_load_aea_ctx_without_config_fails():
    """Test load_aea_ctx fails without aea-config.yaml in local directory."""

    def mock_func(ctx, *args, **kwargs):
        return ctx, args, kwargs  # pylint: disable=C3001

    mock_context = MagicMock(spec=click.Context)

    decorated_func = load_aea_ctx(mock_func)
    with pytest.raises(FileNotFoundError):
        decorated_func(mock_context, "arg1", "arg2", kwarg1="value1", kwarg2="value2")


@pytest.fixture
def temp_dir(tmp_path):
    """Temp dir fixture."""
    return tmp_path


def test_write_to_file_text(temp_dir):
    """Test write_to_file writes a text file."""
    file_path = temp_dir / "test.txt"
    content = "Hello, world!"
    write_to_file(str(file_path), content, FileType.TEXT)

    assert file_path.exists()
    with open(file_path, encoding=DEFAULT_ENCODING) as f:
        assert f.read() == content


def test_write_to_file_yaml(temp_dir):
    """Test write_to_file writes a YAML file."""
    file_path = temp_dir / "test.yaml"
    content = {"key": "value", "list": [1, 2, 3]}
    write_to_file(str(file_path), content, FileType.YAML)

    assert file_path.exists()
    with open(file_path, encoding=DEFAULT_ENCODING) as f:
        assert yaml.safe_load(f) == content


def test_write_to_file_json(temp_dir):
    """Test write_to_file writes a JSON file."""
    file_path = temp_dir / "test.json"
    content = {"key": "value", "list": [1, 2, 3]}
    write_to_file(str(file_path), content, FileType.JSON)

    assert file_path.exists()
    with open(file_path, encoding=DEFAULT_ENCODING) as f:
        assert json.load(f) == content


def test_write_to_file_invalid_type(temp_dir):
    """Test write_to_file raises an exception when the file type is invalid."""
    file_path = temp_dir / "test.invalid"
    content = "Some content"

    invalid_file_type = "INVALID"

    with pytest.raises(ValueError, match="Invalid file_type"):
        write_to_file(str(file_path), content, invalid_file_type)


def test_write_to_file_exception(temp_dir):
    """Test write_to_file raises an exception when the file path is invalid."""
    file_path = temp_dir / "nonexistent_dir" / "test.txt"
    content = "Some content"

    with pytest.raises(ValueError, match="Error writing to file"):
        write_to_file(str(file_path), content, FileType.TEXT)
