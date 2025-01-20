"""Service functions for the eject command."""

import shutil
from typing import List, Tuple, Optional
from pathlib import Path
from dataclasses import field, dataclass

from aea.configurations.base import (
    PublicId,
    ComponentType,
    _get_default_configuration_file_name_from_type,  # noqa
)
from aea.configurations.constants import DEFAULT_AEA_CONFIG_FILE

from auto_dev.utils import FileType, change_dir, write_to_file, load_autonolas_yaml
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

    def eject_component(self, component_id: PublicId, new_author: str, new_name: str, component_type: str) -> bool:
        """Eject a single component and update its configuration."""
        try:
            if not self._run_eject_command(component_id, component_type):
                return False

            component_dir = self._get_and_verify_component_dir(component_id, component_type)

            if not self._fingerprint_component(component_id, component_type):
                raise ValueError(f"Failed to fingerprint component {component_id}")

            config_path = component_dir / _get_default_configuration_file_name_from_type(component_type)
            self.update_config(config_path, new_author, new_name, component_type)

            new_dir = component_dir.parent / new_name
            component_dir.rename(new_dir)

            if not self._fingerprint_component(PublicId(new_author, new_name), component_type):
                raise ValueError(f"Failed to fingerprint component {new_author}/{new_name}")

            print(f"Successfully ejected and fingerprinted {component_id} to {new_author}/{new_name}")
            return True

        except Exception as e:
            raise ValueError(f"Failed to eject component {component_id}: {e}") from e

    def _run_eject_command(self, component_id: PublicId, component_type: str) -> bool:
        """Run the aea eject command."""
        success, _ = self.run_command(f"aea -s eject {component_type} {component_id.author}/{component_id.name}")
        return success

    def _get_and_verify_component_dir(self, component_id: PublicId, component_type: str) -> Path:
        """Get and verify the component directory exists."""
        component_dir = Path.cwd() / f"{component_type}s" / component_id.name
        if not component_dir.exists():
            raise ValueError(f"Component directory not found at {component_dir}")
        return component_dir

    def _fingerprint_component(self, component_id: PublicId, component_type: str) -> bool:
        """Run fingerprint command for a component."""
        success, _ = self.run_command(f"aea -s fingerprint {component_type} {component_id.author}/{component_id.name}")
        return success

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
        possible_paths = [
            packages_base / self.config.fork_id.author / "agents" / self.config.fork_id.name,
            packages_base / "agents" / self.config.fork_id.author / self.config.fork_id.name,
            packages_base / self.config.component_type / self.config.fork_id.author / self.config.fork_id.name,
            packages_base / self.config.fork_id.author / "agents" / Path.cwd().name,
        ]

        for path in possible_paths:
            if path.exists():
                print(f"Cleaning up existing directory: {path}")
                shutil.rmtree(path)

        packages_base.mkdir(parents=True, exist_ok=True)

    def handle_dependencies(self, deps: List[PublicId]) -> List[PublicId]:
        """Handle component dependencies."""
        if self.config.skip_dependencies:
            return []

        ejected_deps = []
        for dep in deps:
            ejected_dep = self._try_eject_dependency(dep)
            if ejected_dep:
                ejected_deps.append(ejected_dep)
        return ejected_deps

    def _try_eject_dependency(self, dep: PublicId) -> Optional[PublicId]:
        """Try to eject a single dependency."""
        for component_type in ComponentType:
            component_path = self.config.base_path / f"{component_type.value}s" / dep.author / dep.name
            if not component_path.exists():
                continue

            if self.eject_component(dep, self.config.fork_id.author, dep.name, component_type.value):
                print(f"Successfully ejected dependency {dep}")
                return dep
        return None

    def publish_and_lock(self) -> bool:
        """Publish packages and run lock command."""
        # need to implement publish service function and use here
        success, _ = self.run_command("aea publish --push-missing --local")
        if not success:
            raise ValueError("Failed to publish packages")

        with change_dir(".."):
            _, exit_code = self.run_command("yes dev | autonomy packages lock", shell=True)
            if exit_code not in [0, 1]:
                raise ValueError(f"Packages lock failed with exit code {exit_code}")
        return True

    def eject(self) -> List[PublicId]:
        """
        Eject a component and its dependents.

        Returns:
            List of ejected component IDs

        Raises:
            ValueError: If dependencies are skipped but not already ejected
        """
        try:
            ejected_deps = self._handle_component_dependencies()

            # Eject main component
            if not self.eject_component(
                self.config.public_id, self.config.fork_id.author, self.config.fork_id.name, self.config.component_type
            ):
                return []

            self._update_and_cleanup()
            self.publish_and_lock()

            return [self.config.public_id] + ejected_deps

        except Exception as e:
            raise ValueError(f"Failed to eject components: {e}") from e

    def _handle_component_dependencies(self) -> List[PublicId]:
        """Build and handle component dependencies."""
        component_dir = Path.cwd() / self.config.component_type / self.config.public_id.name
        builder = DependencyBuilder(component_dir, self.config.component_type)
        deps = builder.build()
        return self.handle_dependencies(deps)

    def _update_and_cleanup(self) -> None:
        """Update agent config and cleanup directories."""
        agent_config_path = Path.cwd() / DEFAULT_AEA_CONFIG_FILE
        self.update_agent_config(agent_config_path)
        self.cleanup_directories()


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
