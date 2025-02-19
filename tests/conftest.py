"""Conftest for testing command-line interfaces."""
# pylint: disable=W0135

import os
from pathlib import Path

import pytest

from auto_dev.utils import isolated_filesystem
from auto_dev.constants import (
    DEFAULT_PUBLIC_ID,
)
from auto_dev.cli_executor import CommandExecutor
from auto_dev.workflow_manager import Task
from scripts.generate_command_docs import generate_docs
from auto_dev.services.package_manager.index import PackageManager


@pytest.fixture
def generated_docs(test_filesystem):
    """Fixture to ensure documentation is generated before tests."""
    # Generate the documentation
    (Path(test_filesystem) / "docs").mkdir(parents=True, exist_ok=True)
    generate_docs()

    # Return the docs directory path
    return Path("docs/commands")


OPENAPI_TEST_CASES = [
    ("uspto.yaml", ["handle_get_", "handle_get_dataset_version_fields", "handle_post_dataset_version_records"]),
    ("petstore.yaml", ["handle_get_pets", "handle_post_pets", "handle_get_pets_petId"]),
    ("petstore-expanded.yaml", ["handle_get_pets", "handle_post_pets", "handle_get_pets_id", "handle_delete_pets_id"]),
    ("dummy_openapi.yaml", ["handle_get_users", "handle_post_users", "handle_get_users_userId"]),
    (
        "innovation_station.yaml",
        [
            "handle_get_protocol",
            "handle_post_protocol",
            "handle_get_protocol_id",
            "handle_get_connection",
            "handle_post_connection",
            "handle_get_connection_id",
            "handle_get_contract",
            "handle_post_contract",
            "handle_get_contract_id",
            "handle_get_skill",
            "handle_post_skill",
            "handle_get_skill_id",
            "handle_get_agent",
            "handle_post_agent",
            "handle_get_agent_id",
            "handle_get_service",
            "handle_post_service",
            "handle_get_service_id",
            "handle_post_generate",
        ],
    ),
]


@pytest.fixture(params=OPENAPI_TEST_CASES)
def openapi_test_case(request):
    """Fixture for openapi test cases."""
    return request.param


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
    """Fixure for testing packages."""
    Task(command="autonomy packages init").work()
    return test_filesystem


@pytest.fixture
def cli_runner():
    """Fixture for invoking command-line interfaces."""
    return CommandExecutor


@pytest.fixture
def dummy_agent_tim(test_packages_filesystem) -> Path:
    """Fixture for dummy agent tim."""
    assert Path.cwd() == Path(test_packages_filesystem)
    agent = DEFAULT_PUBLIC_ID
    task = Task(
        command=f"adev create {agent!s} -t eightballer/base --no-clean-up", working_dir=Path(test_packages_filesystem)
    )
    task.work()
    if not task.is_done or task.is_failed:
        raise ValueError(task.client.output)
    os.chdir(agent.name)
    return True


@pytest.fixture
def dummy_agent_default(test_packages_filesystem) -> Path:
    """Fixture for dummy agent default."""
    assert Path.cwd() == Path(test_packages_filesystem)
    agent = DEFAULT_PUBLIC_ID
    command = f"adev create {agent!s} -t eightballer/base --no-clean-up --no-publish"
    command_executor = CommandExecutor(command)
    result = command_executor.execute(verbose=True, shell=True)
    if not result:
        msg = f"CLI command execution failed: `{command}`"
        raise ValueError(msg)
    os.chdir(agent.name)
    return True


@pytest.fixture
def package_manager():
    """Fixture for PackageManager."""

    return PackageManager(verbose=True)
