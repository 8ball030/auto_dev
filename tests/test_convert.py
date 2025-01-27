"""Tests for the convert command."""

from pathlib import Path

import pytest
from click.testing import CliRunner
from aea.configurations.base import PublicId
from aea.configurations.constants import PACKAGES, SERVICES

from auto_dev.constants import DEFAULT_AUTHOR, DEFAULT_PUBLIC_ID, DEFAULT_AGENT_NAME
from auto_dev.exceptions import UserInputError
from auto_dev.commands.convert import CONVERSION_COMPLETE_MSG, ConvertCliTool, convert


@pytest.mark.parametrize(
    ("agent_public_id", "service_public_id"),
    [
        (str(DEFAULT_PUBLIC_ID), str(DEFAULT_PUBLIC_ID)),
        (str(DEFAULT_PUBLIC_ID), "author/service"),
        (str(DEFAULT_PUBLIC_ID), "jim/jones"),
    ],
)
def test_convert_agent_to_service(dummy_agent_tim, agent_public_id, service_public_id, test_packages_filesystem):
    """Test the convert agent to service command."""
    assert dummy_agent_tim, "Dummy agent not created."
    assert test_packages_filesystem, "Test packages filesystem not created."
    convert = ConvertCliTool(agent_public_id, service_public_id)
    result = convert.generate()
    output_public_id = PublicId.from_str(service_public_id)
    assert (Path(PACKAGES) / output_public_id.author / SERVICES / output_public_id.name).exists()
    assert result


@pytest.mark.parametrize(
    ("agent_public_id", "service_public_id"),
    [
        (str(DEFAULT_PUBLIC_ID), str(DEFAULT_PUBLIC_ID)),
    ],
)
def test_force(dummy_agent_tim, agent_public_id, service_public_id, test_packages_filesystem):
    """Test the convert agent to service command."""
    assert dummy_agent_tim, "Dummy agent not created."
    assert test_packages_filesystem, "Test packages filesystem not created."
    convert = ConvertCliTool(agent_public_id, service_public_id)
    result = convert.generate()
    output_public_id = PublicId.from_str(service_public_id)
    assert (Path(PACKAGES) / output_public_id.author / SERVICES / output_public_id.name).exists()
    assert result
    # Test force
    convert = ConvertCliTool(agent_public_id, service_public_id)
    with pytest.raises(FileExistsError):
        result = convert.generate()
    assert convert.generate(force=True)


@pytest.mark.parametrize(
    ("agent_public_id", "service_public_id"),
    [
        (None, str(DEFAULT_PUBLIC_ID)),
        (str(DEFAULT_PUBLIC_ID), None),
        ("a1" + str(DEFAULT_PUBLIC_ID), str(DEFAULT_PUBLIC_ID)),
    ],
)
def test_convert_agent_to_service_fails(dummy_agent_tim, agent_public_id, service_public_id, test_packages_filesystem):
    """Test the convert agent to service command."""
    assert dummy_agent_tim, "Dummy agent not created."
    assert test_packages_filesystem, "Test packages filesystem not created."
    with pytest.raises(UserInputError):
        ConvertCliTool(agent_public_id, service_public_id)


@pytest.mark.parametrize(
    ("agent_public_id", "service_public_id", "number_of_agents", "force"),
    [
        (str(DEFAULT_PUBLIC_ID), str(DEFAULT_PUBLIC_ID), 1, False),
    ],
)
def test_agent_to_service(
    dummy_agent_tim, test_packages_filesystem, agent_public_id, service_public_id, number_of_agents, force
):
    """Test the agent to service command."""
    assert dummy_agent_tim, "Dummy agent not created."
    assert test_packages_filesystem, "Test packages filesystem not created."

    cmd = [
        "agent-to-service",
        agent_public_id,
        service_public_id,
        f"--number_of_agents={number_of_agents}",
    ]
    if force:
        cmd.append("--force")
    runner = CliRunner()
    result = runner.invoke(convert, cmd)
    assert result.exit_code == 0, f"Command failed': {result.output}"
    assert CONVERSION_COMPLETE_MSG in result.output
    assert (Path(PACKAGES) / DEFAULT_AUTHOR / SERVICES / DEFAULT_AGENT_NAME).exists()
