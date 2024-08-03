"""
Tests for the click cli.
"""

import os

BASE = ['poetry', 'run', 'adev', '-v', '-n', '0']


def test_lint_fails(cli_runner, test_filesystem):
    """Test the lint command fails with no packages."""
    assert os.getcwd() == test_filesystem
    runner = cli_runner(
        BASE
        + [
            "lint",
            "-p",
            "packages/fake",
        ]
    )
    assert not runner.execute(True, True)


def test_lints_self(cli_runner, test_filesystem):
    """Test the lint command works with the current package."""
    assert os.getcwd() == test_filesystem
    runner = cli_runner(
        BASE
        + [
            "lint",
            "-p",
            ".",
        ]
    )
    assert not runner.execute(True, True)


def test_formats_self(cli_runner, test_filesystem):
    """Test the format command works with the current package."""
    assert os.getcwd() == test_filesystem
    runner = cli_runner(
        BASE
        + [
            "fmt",
            "-p",
            ".",
        ]
    )
    assert runner.execute(True, True)
