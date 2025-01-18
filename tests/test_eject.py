"""Tests for the eject command."""

import os
import shutil
import subprocess
from pathlib import Path
from unittest.mock import call, patch

import yaml
import pytest
from click.testing import CliRunner
from aea.configurations.base import PublicId

from auto_dev.constants import COMPONENT_CONFIG_FILES
from auto_dev.commands.eject import cli


@pytest.fixture
def test_data_dir(tmp_path: Path) -> Path:
    """Create a test data directory with a mock AEA project."""
    # Create basic structure
    packages_dir = tmp_path / "packages"
    packages_dir.mkdir()

    # Create test skill
    skill_dir = packages_dir / "skills" / "author" / "test_skill"
    skill_dir.mkdir(parents=True)

    # Create skill.yaml
    skill_yaml = {
        "name": "test_skill",
        "author": "author",
        "version": "0.1.0",
        "type": "skill",
        "description": "Test skill",
        "license": "Apache-2.0",
        "dependencies": {
            "skill": ["other_author/dependent_skill:0.1.0"],
            "protocol": ["other_author/test_protocol:0.1.0"],
        },
    }
    skill_config_path = skill_dir / COMPONENT_CONFIG_FILES["skill"]
    skill_config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(skill_config_path, "w", encoding="utf-8") as f:
        yaml.dump(skill_yaml, f)

    # Create dependent skill
    dep_skill_dir = packages_dir / "skills" / "other_author" / "dependent_skill"
    dep_skill_dir.mkdir(parents=True)

    # Create dependent skill.yaml
    dep_skill_yaml = {
        "name": "dependent_skill",
        "author": "other_author",
        "version": "0.1.0",
        "type": "skill",
        "description": "Dependent skill",
        "license": "Apache-2.0",
        "dependencies": {},
    }
    dep_skill_config_path = dep_skill_dir / COMPONENT_CONFIG_FILES["skill"]
    dep_skill_config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(dep_skill_config_path, "w", encoding="utf-8") as f:
        yaml.dump(dep_skill_yaml, f)

    # Create dependent protocol
    dep_protocol_dir = packages_dir / "protocols" / "other_author" / "test_protocol"
    dep_protocol_dir.mkdir(parents=True)

    # Create protocol.yaml
    protocol_yaml = {
        "name": "test_protocol",
        "author": "other_author",
        "version": "0.1.0",
        "type": "protocol",
        "description": "Test protocol",
        "license": "Apache-2.0",
        "dependencies": {},
    }
    protocol_config_path = dep_protocol_dir / COMPONENT_CONFIG_FILES["protocol"]
    protocol_config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(protocol_config_path, "w", encoding="utf-8") as f:
        yaml.dump(protocol_yaml, f)

    yield tmp_path

    # Cleanup
    shutil.rmtree(tmp_path)


@patch("auto_dev.services.eject.index._eject_single_component")
@patch("subprocess.run")
def test_eject_command(mock_run, mock_eject_single, test_data_dir, caplog):
    """Test the eject command."""
    # Mock successful ejection
    mock_eject_single.return_value = True
    mock_run.return_value.returncode = 0

    # Create target directory structure
    packages_dir = test_data_dir / "packages" / "skills" / "new_author" / "better_skill"
    packages_dir.mkdir(parents=True, exist_ok=True)

    # Create skill.yaml in target directory
    skill_yaml = {
        "name": "better_skill",
        "author": "new_author",
        "version": "0.1.0",
        "type": "skill",
        "description": "Test skill",
        "license": "Apache-2.0",
        "dependencies": {},
    }
    with open(packages_dir / COMPONENT_CONFIG_FILES["skill"], "w", encoding="utf-8") as f:
        yaml.dump(skill_yaml, f)

    # Change to test directory
    os.chdir(test_data_dir)

    # Create CLI runner
    runner = CliRunner()

    # Run command with name change
    result = runner.invoke(
        cli,
        ["eject", "skill", "author/test_skill", "new_author/better_skill"],
        obj={"LOGGER": None},
    )

    # Check command succeeded
    assert result.exit_code == 0

    # Verify eject was called with correct arguments
    mock_eject_single.assert_has_calls(
        [call(PublicId(author="author", name="test_skill", version="latest"), "new_author", "better_skill", "skill")],
        any_order=True,
    )

    # Verify subprocess calls
    mock_run.assert_any_call(["./lock_packages.exp"], check=True)
    mock_run.assert_any_call(
        ["aea", "publish", "--push-missing", "--local"],
        check=True,
        capture_output=True,
        text=True,
    )

    # Check success messages in logs
    assert any("Successfully ejected 1 components:" in record.message for record in caplog.records)
    assert any("author/test_skill:latest" in record.message for record in caplog.records)


@patch("auto_dev.services.eject.index._eject_single_component")
@patch("subprocess.run")
def test_eject_command_with_skip_dependencies(mock_run, mock_eject_single, test_data_dir):
    """Test the eject command with skip_dependencies flag."""
    # Mock successful ejection
    mock_eject_single.return_value = True
    mock_run.return_value.returncode = 0

    # Create target directory structure
    packages_dir = test_data_dir / "packages" / "skills" / "new_author" / "better_skill"
    packages_dir.mkdir(parents=True, exist_ok=True)

    # Create skill.yaml in target directory
    skill_yaml = {
        "name": "better_skill",
        "author": "new_author",
        "version": "0.1.0",
        "type": "skill",
        "description": "Test skill",
        "license": "Apache-2.0",
        "dependencies": {},
    }
    with open(packages_dir / COMPONENT_CONFIG_FILES["skill"], "w", encoding="utf-8") as f:
        yaml.dump(skill_yaml, f)

    # Change to test directory
    os.chdir(test_data_dir)

    # Create CLI runner
    runner = CliRunner()

    # Run command with skip-dependencies flag
    result = runner.invoke(
        cli,
        ["eject", "skill", "author/test_skill", "new_author/better_skill", "--skip-dependencies"],
        obj={"LOGGER": None},
    )

    # Check command succeeded
    assert result.exit_code == 0

    # Verify only target component was ejected
    mock_eject_single.assert_called_once_with(
        PublicId(author="author", name="test_skill", version="latest"),
        "new_author",
        "better_skill",
        "skill",
    )

    # Verify subprocess calls
    mock_run.assert_any_call(["./lock_packages.exp"], check=True)
    mock_run.assert_any_call(
        ["aea", "publish", "--push-missing", "--local"],
        check=True,
        capture_output=True,
        text=True,
    )


@patch("auto_dev.services.eject.index._eject_single_component")
@patch("subprocess.run")
def test_eject_command_lock_failure(mock_run, mock_eject_single, test_data_dir):
    """Test the eject command when package locking fails."""
    # Mock successful ejection but failed locking
    mock_eject_single.return_value = True
    mock_run.side_effect = [
        subprocess.CompletedProcess(args=[], returncode=0),  # First call succeeds
        subprocess.CalledProcessError(1, cmd=["./lock_packages.exp"]),  # Second call fails
    ]

    # Create target directory structure
    packages_dir = test_data_dir / "packages" / "skills" / "new_author" / "better_skill"
    packages_dir.mkdir(parents=True, exist_ok=True)

    # Create skill.yaml in target directory
    skill_yaml = {
        "name": "better_skill",
        "author": "new_author",
        "version": "0.1.0",
        "type": "skill",
        "description": "Test skill",
        "license": "Apache-2.0",
        "dependencies": {},
    }
    with open(packages_dir / COMPONENT_CONFIG_FILES["skill"], "w", encoding="utf-8") as f:
        yaml.dump(skill_yaml, f)

    # Change to test directory
    os.chdir(test_data_dir)

    # Create CLI runner
    runner = CliRunner()

    # Run command
    result = runner.invoke(
        cli,
        ["eject", "skill", "author/test_skill", "new_author/better_skill"],
        obj={"LOGGER": None},
    )

    # Check command failed
    assert result.exit_code != 0
    assert "Failed to eject component" in str(result.output)


@patch("auto_dev.services.eject.index._eject_single_component")
@patch("subprocess.run")
def test_eject_command_skip_dependencies_missing(mock_run, mock_eject_single, test_data_dir, caplog):
    """Test the eject command fails when skipping dependencies that aren't ejected."""
    # Mock dependencies
    mock_eject_single.return_value = True
    mock_run.side_effect = subprocess.CalledProcessError(1, cmd=["aea", "publish", "--push-missing", "--local"])

    # Create target directory structure
    packages_dir = test_data_dir / "packages" / "skills" / "new_author" / "better_skill"
    packages_dir.mkdir(parents=True, exist_ok=True)

    # Create skill.yaml in target directory with dependencies
    skill_yaml = {
        "name": "better_skill",
        "author": "new_author",
        "version": "0.1.0",
        "type": "skill",
        "description": "Test skill",
        "license": "Apache-2.0",
        "dependencies": {
            "skill": ["other_author/dependent_skill:0.1.0"],
            "protocol": ["other_author/test_protocol:0.1.0"],
        },
    }
    with open(packages_dir / COMPONENT_CONFIG_FILES["skill"], "w", encoding="utf-8") as f:
        yaml.dump(skill_yaml, f)

    # Change to test directory
    os.chdir(test_data_dir)

    # Create CLI runner
    runner = CliRunner()

    # Run command with skip-dependencies flag but missing dependencies
    result = runner.invoke(
        cli,
        ["eject", "skill", "author/test_skill", "new_author/better_skill", "--skip-dependencies"],
        obj={"LOGGER": None},
    )

    # Check command failed
    assert result.exit_code != 0

    # Check error message in logs
    assert any("Failed to eject component" in record.message for record in caplog.records)
    assert any(
        "Command '['aea', 'publish', '--push-missing', '--local']' returned non-zero exit status 1" in record.message
        for record in caplog.records
    )


@patch("auto_dev.services.eject.index._eject_single_component")
def test_eject_command_failure(mock_eject_single, test_data_dir):
    """Test the eject command when ejection fails."""
    # Mock failed ejection
    mock_eject_single.return_value = False

    os.chdir(test_data_dir)

    runner = CliRunner()

    result = runner.invoke(
        cli, ["eject", "skill", "author/test_skill", "new_author/better_skill"], obj={"LOGGER": None}
    )

    assert "Failed to eject any components!" in result.output


@patch("auto_dev.services.eject.index._eject_single_component")
def test_eject_command_invalid_component(mock_eject_single, test_data_dir):
    """Test the eject command with an invalid component."""
    # Mock failed ejection
    mock_eject_single.return_value = False

    # Change to test directory
    os.chdir(test_data_dir)

    # Create CLI runner
    runner = CliRunner()

    # Run command with non-existent component
    result = runner.invoke(
        cli,
        ["eject", "skill", "nonexistent/skill", "new_author/better_skill"],
        obj={"LOGGER": None},
    )

    # Check command output indicates failure
    assert "Failed to eject any components!" in result.output

    # Verify eject was called with correct arguments
    mock_eject_single.assert_called_once_with(
        PublicId(author="nonexistent", name="skill", version="latest"), "new_author", "better_skill", "skill"
    )
