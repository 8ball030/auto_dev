"""Tests for the run command."""

import pytest
from click.testing import CliRunner

from auto_dev.commands.run import run


@pytest.mark.parametrize(
    ("group", "command"),
    [
        (
            run,
            "dev",
        ),
        (
            run,
            "prod",
        ),
    ],
)
def test_executes_help(group, command):
    """Test that the help group is executed."""
    runner = CliRunner()
    result = runner.invoke(group, [command, "--help"])
    assert result.exit_code == 0
    assert "Usage" in result.output
