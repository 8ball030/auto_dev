"""
Conftest for testing command-line interfaces.
"""
# pylint: disable=W0135

import os
from pathlib import Path

import pytest

from auto_dev.cli_executor import CommandExecutor
from auto_dev.constants import AUTONOMY_PACKAGES_FILE, DEFAULT_ENCODING, SAMPLE_PACKAGE_FILE, SAMPLE_PACKAGES_JSON
from auto_dev.utils import isolated_filesystem


@pytest.fixture
def test_filesystem():
    """Fixture for invoking command-line interfaces."""
    with isolated_filesystem(copy_cwd=True) as directory:
        yield directory


@pytest.fixture
def test_clean_filesystem():
    """Fixture for invoking command-line interfaces."""
    with isolated_filesystem() as directory:
        yield directory


@pytest.fixture
def test_packages_filesystem(test_filesystem):
    """
    Fixure for testing packages.
    """
    (Path(test_filesystem) / "packages").mkdir(parents=True, exist_ok=True)
    with open(AUTONOMY_PACKAGES_FILE, "w", encoding=DEFAULT_ENCODING) as file:
        file.write(SAMPLE_PACKAGES_JSON["packages/packages.json"])

    for file, data in SAMPLE_PACKAGE_FILE.items():
        (Path(test_filesystem) / Path(file).parent).mkdir(parents=True, exist_ok=True)
        with open(Path(test_filesystem) / Path(file), "w", encoding=DEFAULT_ENCODING) as path:
            path.write(data)

    yield test_filesystem


@pytest.fixture
def cli_runner():
    """Fixture for invoking command-line interfaces."""
    return CommandExecutor


@pytest.fixture
def dummy_agent_tim(test_filesystem, monkeypatch) -> Path:
    """Fixture for dummy agent tim."""

    monkeypatch.syspath_prepend(test_filesystem)
    assert Path.cwd() == Path(test_filesystem)
    (Path.cwd() / "packages").mkdir()

    agent = "tim"
    command = f"aea create {agent}"
    command_executor = CommandExecutor(command)
    result = command_executor.execute(verbose=True, shell=True)
    if not result:
        raise ValueError(f"CLI command execution failed: `{command}`")

    os.chdir(str(Path.cwd() / agent))

    commands = (
        "aea generate-key ethereum",
        "aea add-key ethereum",
    )
    for command in commands:
        command_executor = CommandExecutor(command.split())
        result = command_executor.execute(verbose=True)
        if not result:
            raise ValueError(f"CLI command execution failed: `{command}`")

    return Path.cwd()
