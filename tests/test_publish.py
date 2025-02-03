"""Tests for the publish service and command."""

from pathlib import Path

import pytest
from aea.configurations.constants import DEFAULT_AEA_CONFIG_FILE

from auto_dev.utils import change_dir
from auto_dev.constants import DEFAULT_AUTHOR, DEFAULT_PUBLIC_ID, DEFAULT_AGENT_NAME, AGENT_PUBLISHED_SUCCESS_MSG
from auto_dev.exceptions import OperationError
from auto_dev.workflow_manager import Task
from auto_dev.services.package_manager.index import INCORRECT_PATH_MSG


def test_force_removes_package(package_manager, test_packages_filesystem, dummy_agent_default):
    """Test that force flag properly removes existing package."""
    assert test_packages_filesystem
    assert dummy_agent_default
    assert Path(DEFAULT_AEA_CONFIG_FILE).exists()

    # First publish
    package_manager.publish_agent()
    packages_path = Path("..") / "packages" / DEFAULT_AUTHOR / "agents" / DEFAULT_AGENT_NAME
    assert packages_path.exists()

    # Add a test file to verify it gets removed
    test_file = packages_path / "test.txt"
    test_file.write_text("test content")
    assert test_file.exists()

    # Force publish should remove the entire package directory
    package_manager.publish_agent(force=True)
    assert packages_path.exists()  # Package should be recreated
    assert (packages_path / DEFAULT_AEA_CONFIG_FILE).exists()
    assert not test_file.exists()  # Test file should be gone


def test_publish_command_invalid(cli_runner, test_packages_filesystem, dummy_agent_default):
    """Test publish command output messages."""
    assert test_packages_filesystem
    assert dummy_agent_default
    assert Path(DEFAULT_AEA_CONFIG_FILE).exists()

    # Test invalid ID message first (before any publishing)
    cmd = ["adev", "-v", "publish", "invalid_id"]
    runner = cli_runner(cmd)
    result = runner.execute()
    assert not result
    assert runner.return_code == 2
    assert "Invalid value for 'PUBLIC_ID':" in runner.output


def test_publish_command_happy_path(cli_runner, test_packages_filesystem, dummy_agent_default):
    """Test publish command output messages."""
    assert test_packages_filesystem
    assert dummy_agent_default

    # Test successful first publish
    cmd = ["adev", "-v", "publish", str(DEFAULT_PUBLIC_ID)]
    runner = cli_runner(cmd)
    result = runner.execute()
    assert result
    assert AGENT_PUBLISHED_SUCCESS_MSG in runner.output


def test_publish_command_unhappy_path(
    cli_runner,
    test_packages_filesystem,
    dummy_agent_default,
):
    """Test publish command output messages."""
    # Test package exists error without force

    test_publish_command_happy_path(cli_runner, test_packages_filesystem, dummy_agent_default)
    cmd = ["adev", "-v", "publish", str(DEFAULT_PUBLIC_ID)]
    runner = cli_runner(cmd)
    result = runner.execute()
    assert not result
    assert "already exists" in runner.output


def test_publish_command_force(
    cli_runner,
    test_packages_filesystem,
    dummy_agent_default,
):
    """Test publish command output with force."""
    test_publish_command_happy_path(cli_runner, test_packages_filesystem, dummy_agent_default)
    packages_path = Path("..") / "packages" / DEFAULT_AUTHOR / "agents" / DEFAULT_AGENT_NAME
    test_file = packages_path / "test.txt"
    test_file.write_text("test content")
    assert test_file.exists()
    task = Task(command=f"adev publish {DEFAULT_PUBLIC_ID!s}")
    task.work()
    assert all([task.is_done, task.is_failed]), task.client.output
    assert AGENT_PUBLISHED_SUCCESS_MSG not in task.client.output
    assert test_file.exists()
    task.command += " --force"
    task.work()
    assert all([task.is_done, not task.is_failed]), task.client.output
    assert AGENT_PUBLISHED_SUCCESS_MSG in task.client.output
    assert not test_file.exists()


def test_publish_error_messages(package_manager, test_packages_filesystem, dummy_agent_default):
    """Test error messages during publishing."""
    assert test_packages_filesystem
    assert dummy_agent_default
    assert Path(DEFAULT_AEA_CONFIG_FILE).exists()

    # First publish to create package
    package_manager.publish_agent()

    # Test package exists error
    with pytest.raises(
        OperationError,
    ):
        package_manager.publish_agent()

    # Test wrong directory error
    with pytest.raises(OperationError, match=INCORRECT_PATH_MSG), change_dir(".."):
        package_manager.publish_agent()


def test_publish_package_creation(package_manager, test_packages_filesystem, dummy_agent_default):
    """Test package creation and structure."""
    assert test_packages_filesystem
    assert dummy_agent_default
    assert Path(DEFAULT_AEA_CONFIG_FILE).exists()

    # Test basic publish creates correct package structure
    package_manager.publish_agent()

    packages_path = Path("..") / "packages" / DEFAULT_AUTHOR / "agents" / DEFAULT_AGENT_NAME
    assert packages_path.exists()
    assert (packages_path / DEFAULT_AEA_CONFIG_FILE).exists()

    # Test force publish recreates package structure
    test_file = packages_path / "test.txt"
    test_file.write_text("test content")
    assert test_file.exists()

    package_manager.publish_agent(force=True)
    assert packages_path.exists()
    assert (packages_path / DEFAULT_AEA_CONFIG_FILE).exists()
    assert not test_file.exists()
