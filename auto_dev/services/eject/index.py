# ruff: noqa: PLR1702
"""Service functions for the eject command."""

import shutil
import logging
from typing import Set, Dict, List, Tuple, Optional
from pathlib import Path
from dataclasses import field, dataclass

from aea.configurations.base import (
    PublicId,
    ComponentType,
    _get_default_configuration_file_name_from_type,  # noqa
)
from aea.configurations.constants import DEFAULT_AEA_CONFIG_FILE

from auto_dev.utils import FileType, change_dir, get_logger, write_to_file, load_autonolas_yaml
from auto_dev.exceptions import ConfigUpdateError, DependencyTreeError
from auto_dev.cli_executor import CommandExecutor
from auto_dev.services.dependencies.index import DependencyBuilder


@dataclass
class EjectConfig:
    """Configuration for ejection."""

    component_type: str
    public_id: PublicId
    fork_id: PublicId
    base_path: Path = field(default_factory=Path.cwd)
    skip_dependencies: bool = False


class ComponentEjector:
    """Class to handle component ejection."""

    def __init__(self, config: EjectConfig):
        """Initialize the ejector with configuration."""
        self.config = config
        self.executor = CommandExecutor([""])  # Placeholder, will be set per command
        self.logger = get_logger(__name__)
        self.processed_deps: Set[str] = set()  # Track processed dependencies to avoid duplicates

    def _get_dep_key(self, dep: PublicId, component_type: str) -> str:
        """Get a unique key for a dependency to track processing."""
        return f"{component_type}/{dep.author}/{dep.name}"

    def _convert_dependency_to_public_id(self, dependency: str) -> PublicId:
        """Convert a dependency string to a PublicId object.

        Args:
            dependency: Dependency string in format "author/name:version:hash" or "author/name:version" or "author/name"

        Returns:
            PublicId object
        """
        # Split by : and take the first part (before version and hash)
        base_dep = dependency.split(":")[0]
        author, name = base_dep.split("/")
        return PublicId(author, name)

    def _update_dependency_string(self, dep: str, new_author: str) -> str:
        """Update a single dependency string with new author while preserving version and hash.

        Args:
            dep: Dependency string in format "author/name:version:hash" or "author/name:version" or "author/name"
            new_author: New author to use

        Returns:
            Updated dependency string
        """
        if not isinstance(dep, str) or "/" not in dep:
            return dep

        parts = dep.split(":")  # Split into [author/name, version, hash]
        base_dep = parts[0]
        old_author, name = base_dep.split("/")

        # Reconstruct with new author but keep version and hash
        new_dep = f"{new_author}/{name}"
        if len(parts) > 1:
            new_dep = ":".join([new_dep] + parts[1:])
        return new_dep

    def _update_dependency_list(self, deps: list, new_author: str) -> list:  # noqa: PLR1702
        """Update a list of dependencies with new author.

        Args:
            deps: List of dependency strings
            new_author: New author to use

        Returns:
            Updated list of dependencies
        """
        # Filter and update valid dependencies
        valid_deps = [dep for dep in deps if isinstance(dep, str) and "/" in dep]
        if not valid_deps:
            return deps

        updated_deps = [self._update_dependency_string(dep, new_author) for dep in valid_deps]
        return updated_deps if updated_deps != valid_deps else deps

    def _update_yaml_dependencies(self, config_path: Path, component_type: str, new_author: str) -> None:
        """Update dependencies in a component's YAML file to use the new author.

        Args:
            config_path: Path to the component's config file
            component_type: Type of the component
            new_author: New author to use for dependencies
        """
        try:
            config = load_autonolas_yaml(component_type, config_path.parent)[0]

            # Update dependencies in each field
            for field in ["dependencies", "protocols", "contracts", "connections", "skills"]:
                if field not in config:
                    continue

                if field == "dependencies":
                    # Handle dependencies field which might be a dict
                    if isinstance(config[field], dict):
                        for dep_type, deps in config[field].items():
                            config[field][dep_type] = self._update_dependency_list(deps, new_author)
                else:
                    # Handle direct component fields
                    config[field] = self._update_dependency_list(config[field], new_author)

            write_to_file(config_path, config, file_type=FileType.YAML)

        except Exception as e:
            raise ConfigUpdateError(f"Failed to update dependencies in YAML: {e}") from e

    def _eject_single_component(
        self, component_id: PublicId, component_type: str, is_root: bool = False
    ) -> Tuple[bool, Dict[str, Set[str]]]:  # noqa: PLR1702
        """Eject a single component and its dependencies.

        Args:
            component_id: ID of the component to eject
            component_type: Type of the component
            is_root: Whether this is the root component being ejected

        Returns:
            Tuple of (success, dependencies)
        """
        dep_key = self._get_dep_key(component_id, component_type)
        if dep_key in self.processed_deps:
            self.logger.debug(f"Skipping already processed dependency: {dep_key}")
            return True, {}

        self.processed_deps.add(dep_key)

        try:
            # Run the eject command
            if not self._run_eject_command(component_id, component_type):
                return False, {}

            component_dir = self._get_and_verify_component_dir(component_id, component_type)

            # Get dependencies before any modifications
            dependencies = DependencyBuilder.build_dependency_tree_for_component(component_dir, component_type)

            # Process dependencies recursively
            for dep_type, deps in dependencies.items():
                dep_type_singular = dep_type[:-1] if dep_type.endswith("s") else dep_type
                for dep_str in deps:
                    dep_id = self._convert_dependency_to_public_id(dep_str)
                    self._eject_single_component(dep_id, dep_type_singular)

            # Update the component's configuration
            config_path = component_dir / _get_default_configuration_file_name_from_type(component_type)

            # Update dependencies in YAML to use new author
            self._update_yaml_dependencies(config_path, component_type, self.config.fork_id.author)

            # Clean up packages before publishing
            self.cleanup_directories()

            # Run publish to make changes available
            success, _ = self.run_command("aea publish --push-missing --local")
            if not success:
                raise ConfigUpdateError("Failed to publish after updating dependencies")

            # For root component, use new name; for dependencies, keep original name
            new_name = self.config.fork_id.name if is_root else component_id.name

            # Update the component's own config
            self.update_config(config_path, self.config.fork_id.author, new_name, component_type)

            # Rename directory if needed
            if is_root and new_name != component_id.name:
                new_dir = component_dir.parent / new_name
                component_dir.rename(new_dir)

            if not self._fingerprint_component(PublicId(self.config.fork_id.author, new_name), component_type):
                raise ValueError(f"Failed to fingerprint component {self.config.fork_id.author}/{new_name}")

            self.logger.info(
                f"Successfully ejected and fingerprinted {component_id} to {self.config.fork_id.author}/{new_name}"
            )
            return True, dependencies

        except Exception as e:
            raise ValueError(f"Failed to eject component {component_id}: {e}") from e

    def eject(self) -> List[PublicId]:
        """Eject a component and all its dependencies recursively."""
        try:
            success, dependencies = self._eject_single_component(
                self.config.public_id, self.config.component_type, is_root=True
            )
            if not success:
                return []

            self._update_and_cleanup()

            # Do a final publish to ensure everything is up to date
            success, _ = self.run_command("aea publish --push-missing --local")
            if not success:
                raise ValueError("Failed to do final publish")

            return [self.config.public_id]

        except Exception as e:
            raise ValueError(f"Failed to eject components: {e}") from e

    def run_command(self, command: str, shell: bool = False) -> Tuple[bool, int]:
        """Run a command using the executor and return success and exit code."""
        self.executor.command = command if shell else command.split()
        success = self.executor.execute(verbose=True, shell=shell)
        return success, self.executor.return_code or 0

    def update_config(self, config_path: Path, new_author: str, new_name: str, component_type: str) -> None:
        """Update a component's configuration with new author and name."""
        try:
            config = load_autonolas_yaml(component_type, config_path.parent)[0]
            config["author"] = new_author
            config["name"] = new_name

            config_file = _get_default_configuration_file_name_from_type(component_type)
            write_to_file(config_path.parent / config_file, config, file_type=FileType.YAML)
        except (FileNotFoundError, ValueError) as e:
            raise ValueError(f"Failed to update component configuration: {e}") from e

    def _run_eject_command(self, component_id: PublicId, component_type: str) -> bool:
        """Run the aea eject command."""
        success, _ = self.run_command(
            f"yes | aea -s eject {component_type} {component_id.author}/{component_id.name}", shell=True
        )
        return success

    def _get_and_verify_component_dir(self, component_id: PublicId, component_type: str) -> Path:
        """Get and verify the component directory exists."""
        # Check in vendor directory first
        vendor_dir = Path.cwd() / "vendor" / f"{component_type}s" / component_id.author / component_id.name
        if vendor_dir.exists():
            return vendor_dir

        # If not in vendor, check in root directory (where it goes after ejection)
        root_dir = Path.cwd() / f"{component_type}s" / component_id.name
        if root_dir.exists():
            return root_dir

        raise ValueError(f"Component directory not found in vendor ({vendor_dir}) or root ({root_dir})")

    def _fingerprint_component(self, component_id: PublicId, component_type: str) -> bool:
        """Run fingerprint command for a component."""
        success, _ = self.run_command(f"aea -s fingerprint {component_type} {component_id.author}/{component_id.name}")
        return success

    def _update_and_cleanup(self) -> None:
        """Update agent config and cleanup directories."""
        agent_config_path = Path.cwd() / DEFAULT_AEA_CONFIG_FILE
        self.update_agent_config(agent_config_path)
        self.cleanup_directories()

    def update_agent_config(self, agent_config_path: Path) -> None:
        """Update agent configuration with new component references."""
        if not agent_config_path.exists():
            return

        agent_config = load_autonolas_yaml("agent", agent_config_path.parent)[0]
        if f"{self.config.component_type}s" not in agent_config:
            return

        old_component = f"{self.config.fork_id.author}/{self.config.public_id.name}"
        new_component = f"{self.config.fork_id.author}/{self.config.fork_id.name}"

        agent_config[f"{self.config.component_type}s"] = [
            x.replace(old_component, new_component).replace(f"{old_component}:", f"{new_component}:")
            if old_component in x and new_component != old_component
            else x
            for x in agent_config[f"{self.config.component_type}s"]
        ]

        write_to_file(agent_config_path, agent_config, file_type=FileType.YAML)

    def cleanup_directories(self) -> None:
        """Clean up package directories."""
        packages_base = Path("..") / "packages"

        # Clean up all component directories for this author
        component_types = ["agents", "protocols", "contracts", "connections", "skills"]
        for component_type in component_types:
            author_dir = packages_base / self.config.fork_id.author / component_type
            if author_dir.exists():
                self.logger.info(f"Cleaning up directory: {author_dir}")
                shutil.rmtree(author_dir)

        # Ensure packages directory exists
        packages_base.mkdir(parents=True, exist_ok=True)

    def publish_and_lock(self) -> bool:
        """Publish packages and run lock command."""
        # Clean up packages before publishing
        self.cleanup_directories()

        success, _ = self.run_command("aea publish --push-missing --local")
        if not success:
            raise ValueError("Failed to publish packages")

        with change_dir(".."):
            _, exit_code = self.run_command("yes dev | autonomy packages lock", shell=True)
            if exit_code not in [0, 1]:
                raise ValueError(f"Packages lock failed with exit code {exit_code}")
        return True


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
    ejector = ComponentEjector(config)
    return ejector.eject()
