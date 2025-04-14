"""Tests for the click cli."""

import subprocess
import subprocess
from pathlib import Path

import toml
import pytest
from aea.cli.utils.config import get_default_author_from_cli_config

from auto_dev.utils import change_dir


def test_python_repo(cli_runner, test_clean_filesystem):

    repo_root = Path(test_clean_filesystem) / "dummy_python"

    command = ["adev", "repo", "scaffold", repo_root.name, "-t", "python"]
    runner = cli_runner(command)
    result = runner.execute()
    makefile = repo_root / "Makefile"

    assert result, runner.output
    assert repo_root.exists()
    assert (repo_root / ".git").exists()
    assert makefile.exists()

    error_messages = {}
    make_commands = "fmt", "lint", "test"
    for command in make_commands:
        result = subprocess.run(
            ["make", command],
            shell=False,
            capture_output=True,
            text=True,
            check=False,
        )
        if not runner.return_code == 0:
            error_messages[command] = runner.stderr
    assert not error_messages


def test_autonomy_repo(cli_runner, test_clean_filesystem):

    repo_root = Path(test_clean_filesystem) / "dummy_autonomy"

    command = ["adev", "repo", "scaffold", repo_root.name, "-t", "autonomy"]
    runner = cli_runner(command)
    result = runner.execute()
    makefile = repo_root / "Makefile"

    assert result, runner.output
    assert repo_root.exists()
    assert (repo_root / ".git").exists()
    assert makefile.exists()

    error_messages = {}
    make_commands = "fmt", "lint", "test", "hashes"
    for command in make_commands:
        result = subprocess.run(
            ["make", command],
            shell=False,
            capture_output=True,
            text=True,
            check=False,
        )
        if not runner.return_code == 0:
            error_messages[command] = runner.stderr
    assert not error_messages
