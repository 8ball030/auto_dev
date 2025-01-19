"""Service functions for the eject command."""

import os
import shutil
import subprocess
from typing import Set, Dict, List
from pathlib import Path
from contextlib import contextmanager
from dataclasses import field, dataclass

import yaml
from aea.configurations.base import (
    PublicId,
    ComponentType,
    _get_default_configuration_file_name_from_type,  # noqa
)
from aea.configurations.loader import ConfigLoader
from aea.configurations.constants import DEFAULT_AEA_CONFIG_FILE

from auto_dev.utils import FileType, change_dir, write_to_file, load_autonolas_yaml, build_dependency_tree_for_component


@dataclass
class EjectConfig:
    """Configuration for ejection."""

    component_type: str
    public_id: PublicId
    fork_id: PublicId
    base_path: Path = field(default_factory=Path.cwd)
    skip_dependencies: bool = False


def _run_command(cmd: str) -> bool:
    """Run a shell command safely."""
    try:
        subprocess.run(cmd.split(), check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError:
        return False


def _update_component_config(config_path: Path, new_author: str, new_name: str, component_type: str) -> None:
    """Update the component's configuration with new author and name."""
    try:
        # Load and verify config
        config = load_autonolas_yaml(component_type, config_path.parent)[0]
        # Update author and name
        config["author"] = new_author
        config["name"] = new_name

        # Write back to file
        config_file = _get_default_configuration_file_name_from_type(component_type)
        write_to_file(config_path.parent / config_file, config, file_type=FileType.YAML)

    except (FileNotFoundError, ValueError) as e:
        raise ValueError(f"Failed to update component configuration: {e}") from e


def _eject_single_component(component_id: PublicId, new_author: str, new_name: str, component_type: str) -> bool:
    """
    Eject a single component by running the aea eject command and updating configurations.

    Args:
        component_id: ID of the component to eject
        new_author: New author name for the ejected component
        new_name: New name for the ejected component
        component_type: Type of the component

    Returns:
        bool: True if ejection was successful
    """
    try:
        # Run aea eject command
        if not _run_command(f"aea -s eject {component_type} {component_id.author}/{component_id.name}"):
            return False

        # Get paths - use plural form (skills, protocols, etc.)
        component_dir = Path.cwd() / f"{component_type}s" / component_id.name
        if not component_dir.exists():
            raise ValueError(f"Component directory not found at {component_dir}")

        if not _run_command(f"aea fingerprint {component_type} {component_id.author}/{component_id.name}"):
            raise ValueError(f"Failed to fingerprint component {component_id}")

        # First update config with new author and name
        config_path = component_dir / _get_default_configuration_file_name_from_type(component_type)
        _update_component_config(config_path, new_author, new_name, component_type)

        # Then rename directory to new name (keeping plural form)
        new_dir = component_dir.parent / new_name
        component_dir.rename(new_dir)

        if not _run_command(f"aea fingerprint {component_type} {new_author}/{new_name}"):
            raise ValueError(f"Failed to fingerprint component {new_author}/{new_name}")

        print(f"Successfully ejected and fingerprinted {component_id} to {new_author}/{new_name}")

        return True
    except Exception as e:
        raise ValueError(f"Failed to eject component {component_id}: {e}") from e


def _handle_agent_config(config: EjectConfig, agent_config_path: Path) -> None:
    """Handle agent configuration updates."""
    if not agent_config_path.exists():
        return

    agent_config = load_autonolas_yaml("agent", agent_config_path.parent)[0]
    if f"{config.component_type}s" not in agent_config:
        return

    old_component = f"{config.fork_id.author}/{config.public_id.name}"
    new_component = f"{config.fork_id.author}/{config.fork_id.name}"

    agent_config[f"{config.component_type}s"] = [
        x.replace(old_component, new_component).replace(f"{old_component}:", f"{new_component}:")
        if old_component in x and new_component != old_component
        else x
        for x in agent_config[f"{config.component_type}s"]
    ]

    write_to_file(agent_config_path, agent_config, file_type=FileType.YAML)


def _cleanup_package_directories(config: EjectConfig) -> None:
    """Clean up existing package directories."""
    packages_base = Path("..") / "packages"
    possible_paths = [
        packages_base / config.fork_id.author / "agents" / config.fork_id.name,
        packages_base / "agents" / config.fork_id.author / config.fork_id.name,
        packages_base / config.component_type / config.fork_id.author / config.fork_id.name,
        packages_base / config.fork_id.author / "agents" / Path.cwd().name,
    ]

    for path in possible_paths:
        if path.exists():
            print(f"Cleaning up existing directory: {path}")
            shutil.rmtree(path)

    packages_base.mkdir(parents=True, exist_ok=True)


def _run_packages_lock() -> None:
    """Run the packages lock command."""
    expect_script = """#!/usr/bin/expect -f
set timeout -1
spawn autonomy packages lock
while {1} {
    expect {
        "Select package type (dev, third_party):" {
            send "dev\\r"
            exp_continue
        }
        eof {
            break
        }
    }
}
"""
    script_path = Path("lock_packages.exp")
    script_path.write_text(expect_script)
    script_path.chmod(0o755)

    try:
        subprocess.run(["./lock_packages.exp"], check=True)
    finally:
        script_path.unlink()


def _handle_dependencies(config: EjectConfig, component_dir: Path, ejected: List[PublicId]) -> List[PublicId]:
    """Handle dependency ejection."""
    if config.skip_dependencies:
        return ejected

    deps = build_dependency_tree_for_component(component_dir, config.component_type)
    for dep in deps:
        for component_type in ComponentType:
            component_path = config.base_path / "packages" / component_type.value / dep.author / dep.name
            if not component_path.exists():
                continue
            if _eject_single_component(dep, config.fork_id.author, dep.name, component_type.value):
                ejected.append(dep)
            break

    return ejected


def eject_component(config: EjectConfig) -> List[PublicId]:
    """
    Eject a component and its dependents.

    Args:
        config: EjectConfig object containing ejection parameters

    Returns:
        List of ejected component IDs

    Raises:
        ValueError: If dependencies are skipped but not already ejected
    """
    try:
        component_dir = Path.cwd() / config.component_type / config.public_id.name
        deps = build_dependency_tree_for_component(component_dir, config.component_type)

        _eject_dependencies(deps, config.fork_id.author, config.base_path)

        if not _eject_single_component(
            config.public_id, config.fork_id.author, config.fork_id.name, config.component_type
        ):
            return []

        ejected = [config.public_id]
        ejected = _handle_dependencies(config, component_dir, ejected)

        agent_config_path = Path.cwd() / DEFAULT_AEA_CONFIG_FILE
        _handle_agent_config(config, agent_config_path)
        _cleanup_package_directories(config)

        subprocess.run(
            ["aea", "publish", "--push-missing", "--local"],
            check=True,
            capture_output=True,
            text=True,
        )

        with change_dir(".."):
            _run_packages_lock()

        return ejected
    except Exception as e:
        raise ValueError(f"Failed to eject components: {e}") from e


def _eject_dependencies(dependencies: Set[PublicId], author: str, base_path: Path) -> None:
    """Eject dependencies to the new author."""
    for dep in dependencies:
        for component_type in ComponentType:
            component_path = base_path / f"{component_type.value}s" / dep.author / dep.name
            if component_path.exists():
                if _eject_single_component(dep, author, dep.name, component_type.value):
                    print(f"Successfully ejected dependency {dep}")
                break
