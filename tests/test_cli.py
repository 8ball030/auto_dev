"""Tests for the click cli."""

from pathlib import Path

from auto_dev.constants import DEFAULT_AUTHOR


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


def test_create_invalid_name(cli_runner, test_filesystem):
    """Test the create command fails with invalid agent name."""
    assert str(Path.cwd()) == test_filesystem
    cmd = ["adev", "-v", "create", "NEW_AGENT", "-t", "eightballer/base", "--publish", "--force"]
    runner = cli_runner(cmd)
    result = runner.execute()
    expected_error = "Invalid value for 'PUBLIC_ID': NEW_AGENT"
    assert not result
    assert expected_error in runner.output, f"Expected error message not found in output: {runner.output}"
    agent_path = Path(test_filesystem) / "NEW_AGENT"
    assert not agent_path.exists(), "Agent directory should not have been created"


def test_create_valid_names(cli_runner, test_packages_filesystem):
    """Test the create command succeeds with valid agent names."""
    assert str(Path.cwd()) == test_packages_filesystem

    valid_names = ["my_agent", "_test_agent", "agent123", "valid_agent_name_123"]

    for name in valid_names:
        cmd = [
            "adev",
            "-v",
            "create",
            f"{DEFAULT_AUTHOR}/{name}",
            "-t",
            "eightballer/base",
            "--no-clean-up",
        ]

        runner = cli_runner(cmd)
        assert runner.execute()
        assert runner.return_code == 0, f"Command failed for valid name '{name}': {runner.output}"


def test_create_with_publish_no_packages(cli_runner, test_filesystem):
    """Test the create command succeeds when there is no local packages directory."""
    assert str(Path.cwd()) == test_filesystem
    cmd = ["adev", "-v", "create", f"{DEFAULT_AUTHOR}/test_agent", "-t", "eightballer/base"]

    runner = cli_runner(cmd)
    assert runner.execute()
    assert "No such file or directory" not in runner.output
    assert runner.return_code == 0, f"Command failed': {runner.output}"
