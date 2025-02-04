"""Tests for the click cli."""

from pathlib import Path

from auto_dev.constants import DEFAULT_AUTHOR, DEFAULT_PUBLIC_ID, AGENT_PUBLISHED_SUCCESS_MSG
from auto_dev.workflow_manager import Task
from auto_dev.services.package_manager.index import PACKAGES_NOT_FOUND


def test_lint_fails(cli_runner, test_filesystem):
    """Test the lint command fails with no packages."""
    assert str(Path.cwd()) == test_filesystem
    cmd = ["adev", "-n", "0", "lint", "-p", "packages/fake"]
    runner = cli_runner(cmd)
    runner.execute()
    assert runner.return_code == 2, runner.output


def test_lints_self(cli_runner, test_filesystem):
    """Test the lint command works with the current package."""
    assert str(Path.cwd()) == test_filesystem
    cmd = ["adev", "-v", "-n", "0", "lint", "-p", "."]
    runner = cli_runner(cmd)
    result = runner.execute()
    assert result, runner.output
    assert runner.return_code == 0, runner.output


def test_formats_self(cli_runner, test_filesystem):
    """Test the format command works with the current package."""
    assert str(Path.cwd()) == test_filesystem
    cmd = ["adev", "-n", "0", "-v", "fmt", "-p", "."]
    runner = cli_runner(cmd)
    result = runner.execute()
    assert result, runner.output
    assert runner.return_code == 0, runner.output


def test_create_invalid_name(test_filesystem):
    """Test the create command fails with invalid agent name."""
    assert str(Path.cwd()) == test_filesystem
    task = Task(command="adev create NEW_AGENT -t eightballer/base --no-clean-up")
    task.work()
    assert all([task.is_done, task.is_failed]), task.client.output

    expected_error = "Invalid value for 'PUBLIC_ID': NEW_AGENT"
    assert expected_error in task.client.output, f"Expected error message not found in output: {task.client.output}"
    agent_path = Path(test_filesystem) / "NEW_AGENT"
    assert not agent_path.exists(), "Agent directory should not have been created"


def test_create_valid_names(test_packages_filesystem):
    """Test the create command succeeds with valid agent names."""
    assert str(Path.cwd()) == test_packages_filesystem

    valid_names = ["my_agent", "_test_agent", "agent123", "valid_agent_name_123"]
    for name in valid_names:
        task = Task(
            command=f"adev create {DEFAULT_AUTHOR}/{name} -t eightballer/base --no-clean-up",
        )
        task.work()
        assert all([task.is_done, not task.is_failed]), task.client.output


def test_create_with_publish_no_packages(test_filesystem):
    """Test the create command succeeds when there is no local packages directory."""
    assert str(Path.cwd()) == test_filesystem
    task = Task(
        command=f"adev create {DEFAULT_PUBLIC_ID!s} -t eightballer/base --no-clean-up",
    )
    task.work()
    assert task.is_done, task.client.output
    assert task.is_failed, task.client.output
    assert (
        AGENT_PUBLISHED_SUCCESS_MSG not in task.client.output
    ), f"UnExpected message found in output: {task.client.output}"
    assert PACKAGES_NOT_FOUND in task.client.output, f"Expected message not found in output: {task.client.output}"


def test_run_cmd(cli_runner):
    """Test the run command help message."""
    cmd = ["adev", "run", "--help"]
    runner = cli_runner(cmd)
    result = runner.execute()
    assert result, runner.output
    assert runner.return_code == 0, runner.output
