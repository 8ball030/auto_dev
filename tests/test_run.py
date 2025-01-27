"""Tests for the run command."""

import pytest
from click.testing import CliRunner

from auto_dev.commands.run import dev, prod


@pytest.mark.parametrize(
    "group",
    [
        (dev,),
        (prod,),
    ],
)
def test_executes_help(group):
    """Test that the help group is executed."""
    runner = CliRunner()
    result = runner.invoke(group, ["--help"])
    assert result.exit_code == 0
    assert "Usage" in result.output
