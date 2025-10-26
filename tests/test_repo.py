"""Tests for the click cli."""

import subprocess
from pathlib import Path


def _test_repo_scaffold(repo_type, make_commands, cli_runner, test_clean_filesystem):
    repo_root = Path(test_clean_filesystem) / "dummy"
    command = ["adev", "repo", "scaffold", repo_root.name, "-t", repo_type]
    runner = cli_runner(command)
    result = runner.execute()
    makefile = repo_root / "Makefile"

    # Verify the basic repository structure exists
    assert result, runner.output
    assert repo_root.exists(), f"Repository {repo_root} does not exist."
    assert (repo_root / ".git").exists(), f".git directory not found in {repo_root}."
    assert makefile.exists(), f"Makefile not found in {repo_root}."

    # Run each make command and collect any errors.
    error_messages = {}
    for cmd in make_commands:
        proc_result = subprocess.run(
            ["make", cmd],
            shell=False,
            capture_output=True,
            text=True,
            check=False,
            cwd=repo_root,
        )
        if proc_result.returncode != 0:
            error_messages[cmd] = proc_result.stderr
    assert not error_messages, f"Errors encountered in make commands: {error_messages}"


def test_python_repo(cli_runner, test_clean_filesystem):
    """Test scaffolding a Python repository."""

    _test_repo_scaffold(
        repo_type="python",
        make_commands=("fmt", "lint", "test"),
        cli_runner=cli_runner,
        test_clean_filesystem=test_clean_filesystem,
    )


def test_autonomy_repo(cli_runner, test_clean_filesystem):
    """Test scaffolding an Autonomy repository."""

    _test_repo_scaffold(
        repo_type="autonomy",
        make_commands=("fmt", "lint", "test",),
        cli_runner=cli_runner,
        test_clean_filesystem=test_clean_filesystem,
    )
