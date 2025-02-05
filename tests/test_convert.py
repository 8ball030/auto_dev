"""Tests for the convert command."""

import os
from pathlib import Path

import pytest
from aea.configurations.base import PublicId
from aea.configurations.constants import PACKAGES, SERVICES

from auto_dev.constants import DEFAULT_AUTHOR, DEFAULT_PUBLIC_ID
from auto_dev.exceptions import UserInputError
from auto_dev.commands.convert import CONVERSION_COMPLETE_MSG, ConvertCliTool
from auto_dev.workflow_manager import Task


@pytest.mark.parametrize(
    ("agent_public_id", "service_public_id"),
    [
        (DEFAULT_PUBLIC_ID, DEFAULT_PUBLIC_ID),
        (DEFAULT_PUBLIC_ID, PublicId.from_str("author/service")),
        (DEFAULT_PUBLIC_ID, PublicId.from_str("jim/jones")),
    ],
)
def test_convert_agent_to_service(dummy_agent_tim, agent_public_id, service_public_id, test_packages_filesystem):
    """Test the convert agent to service command."""
    assert dummy_agent_tim, "Dummy agent not created."
    os.chdir(test_packages_filesystem)
    convert = ConvertCliTool(agent_public_id, service_public_id)
    result = convert.generate()
    assert (Path(PACKAGES) / service_public_id.author / SERVICES / service_public_id.name).exists()
    assert result


@pytest.mark.parametrize(
    ("agent_public_id", "service_public_id"),
    [
        (DEFAULT_PUBLIC_ID, DEFAULT_PUBLIC_ID),
    ],
)
def test_force(dummy_agent_tim, agent_public_id, service_public_id, test_packages_filesystem):
    """Test the convert agent to service command."""
    assert dummy_agent_tim, "Dummy agent not created."
    os.chdir(test_packages_filesystem)
    convert = ConvertCliTool(agent_public_id, service_public_id)
    result = convert.generate()
    assert (Path(PACKAGES) / service_public_id.author / SERVICES / service_public_id.name).exists()
    assert result
    # Test force
    convert = ConvertCliTool(agent_public_id, service_public_id)
    with pytest.raises(FileExistsError):
        result = convert.generate()
    assert convert.generate(force=True)


@pytest.mark.parametrize(
    ("agent_public_id", "service_public_id"),
    [
        (None, DEFAULT_PUBLIC_ID),
        (DEFAULT_PUBLIC_ID, None),
        (PublicId.from_str("a1" + str(DEFAULT_PUBLIC_ID)), DEFAULT_PUBLIC_ID),
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
        (DEFAULT_PUBLIC_ID, DEFAULT_PUBLIC_ID, 1, True),
    ],
)
def test_agent_to_service(
    dummy_agent_tim, test_packages_filesystem, agent_public_id, service_public_id, number_of_agents, force
):
    """Test the agent to service command."""
    assert dummy_agent_tim, "Dummy agent not created."
    assert test_packages_filesystem, "Test packages filesystem not created."

    cmd = [
        "adev",
        "convert",
        "agent-to-service",
        str(agent_public_id),
        str(service_public_id),
        f"--number_of_agents={number_of_agents}",
    ]
    if force:
        cmd.append("--force")

    task = Task(command=" ".join(cmd), working_dir=Path(test_packages_filesystem).resolve()).work()
    assert not task.is_failed, task.client.output
    assert CONVERSION_COMPLETE_MSG in task.client.output, task.client.output
    assert (Path(test_packages_filesystem) / PACKAGES / DEFAULT_AUTHOR / SERVICES / service_public_id.name).exists()
