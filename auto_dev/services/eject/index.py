# ruff: noqa: PLR1702
"""Service functions for the eject command."""

import shutil
from pathlib import Path
from dataclasses import field, dataclass

from aea.configurations.base import (
    PublicId,
    _get_default_configuration_file_name_from_type,
)
from aea.configurations.constants import DEFAULT_AEA_CONFIG_FILE

from auto_dev.utils import FileType, get_logger, write_to_file, read_from_file, load_autonolas_yaml
from auto_dev.exceptions import ConfigUpdateError
from auto_dev.cli_executor import CommandExecutor
from auto_dev.services.dependencies.index import DependencyBuilder
from auto_dev.services.runner.prod_runner import with_spinner
from auto_dev.services.package_manager.index import PackageManager


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
        self.processed_deps: set[str] = set()  # Track processed dependencies to avoid duplicates
        self.package_manager = PackageManager(verbose=True)

    def _get_dep_key(self, dep: PublicId, component_type: str) -> str:
        """Get a unique key for a dependency to track processing."""
        return f"{component_type}/{dep.author}/{dep.name}"

    def _convert_dependency_to_public_id(self, dependency: str) -> PublicId:
        """Convert a dependency string to a PublicId object.

        Args:
        ----
            dependency: Dependency string in format "author/name:version:hash" or "author/name:version" or "author/name"

        Returns:
        -------
            PublicId object

        """
        # Split by : and take the first part (before version and hash)
        base_dep = dependency.split(":")[0]
        author, name = base_dep.split("/")
        return PublicId(author, name)

    def _update_single_dependency(self, dep: str, new_author: str) -> str:
        """Update a single dependency string with new author.

        Args:
        ----
            dep: Dependency string
            new_author: New author to use

        Returns:
        -------
            Updated dependency string

        """
        if not isinstance(dep, str) or "/" not in dep:
            return dep

        parts = dep.split(":")  # Split into [author/name, version, hash]
        base_dep = parts[0]
        old_author, name = base_dep.split("/")

        # Only update if the old author matches the one we're ejecting
        if old_author == self.config.public_id.author:
            # Reconstruct with new author but keep version and hash
            new_dep = f"{new_author}/{name}"
            if len(parts) > 1:
                new_dep = ":".join([new_dep] + parts[1:])
            return new_dep
        return dep

    def _update_dependency_field(self, deps: list, new_author: str) -> list:
        """Update a list of dependencies with new author.

        Args:
        ----
            deps: List of dependencies
            new_author: New author to use

        Returns:
        -------
            Updated list of dependencies

        """
        valid_deps = [dep for dep in deps if isinstance(dep, str) and "/" in dep]
        if not valid_deps:
            return deps

        updated_deps = [self._update_single_dependency(dep, new_author) for dep in valid_deps]
        return updated_deps if updated_deps != valid_deps else deps

    def _update_yaml_dependencies(self, config_path: Path, component_type: str, new_author: str) -> None:
        """Update dependencies in a component's YAML file to use the new author.

        Args:
        ----
            config_path: Path to the component's config file
            component_type: Type of the component
            new_author: New author to use

        """
        try:
            # Load both main config and overrides
            configs = load_autonolas_yaml(component_type, config_path.parent)
            if not configs:
                return

            main_config = configs[0]
            overrides = configs[1:]

            def update_config(config):
                """Update a single config object."""
                for field in ["dependencies", "protocols", "contracts", "connections", "skills", "customs"]:
                    if field not in config:
                        continue

                    if field == "dependencies":
                        # Handle dependencies field which might be a dict
                        if isinstance(config[field], dict):
                            for dep_type, deps in config[field].items():
                                config[field][dep_type] = self._update_dependency_field(deps, new_author)
                    else:
                        # Handle direct component fields
                        config[field] = self._update_dependency_field(config[field], new_author)

            # Update main config and overrides
            update_config(main_config)
            for override in overrides:
                update_config(override)

            # Write back main config and overrides
            config_file = _get_default_configuration_file_name_from_type(component_type)
            write_to_file(config_path.parent / config_file, main_config, file_type=FileType.YAML)

            # Write overrides if they exist
            for i, override in enumerate(overrides, 1):
                override_path = config_path.parent / f"{config_file}.{i}"
                write_to_file(override_path, override, file_type=FileType.YAML)

        except Exception as e:
            msg = f"Failed to update dependencies in YAML: {e}"
            raise ConfigUpdateError(msg) from e

    def _update_python_imports(self, component_dir: Path, old_name: str, new_name: str) -> None:
        """Update Python imports in all Python files to use the new component name.

        Args:
        ----
            component_dir: Directory containing the component files
            old_name: Old component name
            new_name: New component name

        Raises:
        ------
            IOError: If there are issues reading/writing files
            ValueError: If there are issues with file content manipulation

        """
        # Find all Python files in the component directory

        with with_spinner():
            for py_file in component_dir.rglob("*.py"):
                relative = py_file.relative_to(component_dir)
                try:
                    self.logger.debug(f"Processing file: {relative}")
                    content = read_from_file(py_file, file_type=FileType.PYTHON)

                    # Update imports using the old name to use the new name
                    old_import_path = (
                        f"packages.{self.config.public_id.author}.{self.config.component_type}s.{old_name}"
                    )
                    new_import_path = f"packages.{self.config.fork_id.author}.{self.config.component_type}s.{new_name}"

                    self.logger.debug(f"Looking to replace: {old_import_path} with {new_import_path}")

                    # Also handle relative imports
                    old_relative_path = f"{old_name}."
                    new_relative_path = f"{new_name}."

                    if old_import_path in content or old_relative_path in content:
                        # Update both absolute and relative imports
                        updated_content = content.replace(old_import_path, new_import_path)
                        updated_content = updated_content.replace(old_relative_path, new_relative_path)

                        self.logger.debug(f"Found matches in {relative}, updating imports")
                        self.logger.debug(f"Original content:\n{content}")
                        self.logger.debug(f"Updated content:\n{updated_content}")

                        write_to_file(py_file, updated_content, file_type=FileType.PYTHON)
                    else:
                        self.logger.debug(f"No matching imports found in {relative}")
                except (OSError, ValueError) as e:
                    self.logger.warning(f"Failed to update imports in {py_file}: {e}")

        # Also check for any .yaml files that might reference the old name
        with with_spinner():
            for yaml_file in component_dir.rglob("*.yaml"):
                try:
                    content = read_from_file(yaml_file)
                    old_ref = f"{self.config.public_id.author}/{old_name}"
                    new_ref = f"{self.config.fork_id.author}/{new_name}"

                    if old_ref in content:
                        updated_content = content.replace(old_ref, new_ref)
                        write_to_file(yaml_file, updated_content, file_type=FileType.YAML)
                        self.logger.info(f"Updated references in YAML file: {yaml_file}")
                except (OSError, ValueError) as e:
                    self.logger.warning(f"Failed to update references in {yaml_file}: {e}")

    def _update_dependency_reference(self, dep_str: str, old_id: PublicId, new_id: PublicId) -> str:
        """Update a single dependency reference.

        Args:
        ----
            dep_str: Original dependency string
            old_id: Original component ID
            new_id: New component ID

        Returns:
        -------
            Updated dependency string

        """
        if dep_str.startswith(f"{old_id.author}/{old_id.name}"):
            # Keep version and hash if present
            parts = dep_str.split(":")
            new_dep = f"{new_id.author}/{new_id.name}"
            if len(parts) > 1:
                new_dep = ":".join([new_dep] + parts[1:])
            return new_dep
        return dep_str

    def _update_dependency_list_references(self, deps: list, old_id: PublicId, new_id: PublicId) -> list:
        """Update references in a list of dependencies.

        Args:
        ----
            deps: List of dependencies
            old_id: Original component ID
            new_id: New component ID

        Returns:
        -------
            Updated list of dependencies

        """
        updated_deps = []
        for dep in deps:
            dep_str = str(dep)
            updated_deps.append(self._update_dependency_reference(dep_str, old_id, new_id))
        return updated_deps

    def _update_component_references(
        self, component_dir: Path, component_type: str, old_id: PublicId, new_id: PublicId
    ) -> None:
        """Update references to an ejected component within another component's configuration.

        Args:
        ----
            component_dir: Directory of the component to update
            component_type: Type of the component
            old_id: Original PublicId of the ejected component
            new_id: New PublicId of the ejected component

        """
        config_path = component_dir / _get_default_configuration_file_name_from_type(component_type)
        if not config_path.exists():
            return

        try:
            configs = load_autonolas_yaml(component_type, component_dir)
            if not configs:
                return

            main_config = configs[0]
            overrides = configs[1:]

            def update_config_references(config):
                """Update references in a single config object."""
                for field in ["dependencies", "protocols", "contracts", "connections", "skills", "customs"]:
                    if field not in config:
                        continue

                    if field == "dependencies" and isinstance(config[field], dict):
                        for dep_type, deps in config[field].items():
                            config[field][dep_type] = self._update_dependency_list_references(deps, old_id, new_id)
                    elif isinstance(config[field], list):
                        config[field] = self._update_dependency_list_references(config[field], old_id, new_id)

            # Update main config and overrides
            update_config_references(main_config)
            for override in overrides:
                update_config_references(override)

            # Write back the updated configs
            write_to_file(config_path, main_config, file_type=FileType.YAML)
            for i, override in enumerate(overrides, 1):
                override_path = config_path.parent / f"{config_path.name}.{i}"
                write_to_file(override_path, override, file_type=FileType.YAML)

            self.logger.info(f"Updated references in {config_path} from {old_id} to {new_id}")

        except Exception as e:
            self.logger.warning(f"Failed to update references in {config_path}: {e}")
            msg = f"Failed to update references: {e}"
            raise ConfigUpdateError(msg) from e

    def _check_dependency_field(self, deps: any, target_str: str) -> bool:
        """Check if a dependency field contains the target string.

        Args:
        ----
            deps: Dependency field value (dict or list)
            target_str: Target dependency string to find

        Returns:
        -------
            True if target is found, False otherwise

        """
        if isinstance(deps, dict):
            # Handle nested dependencies
            for dep_list in deps.values():
                for dep in dep_list:
                    dep_parts = str(dep).split(":")
                    if dep_parts[0] == target_str:
                        return True
        elif isinstance(deps, list):
            # Handle direct dependencies
            for dep in deps:
                dep_parts = str(dep).split(":")
                if dep_parts[0] == target_str:
                    return True
        return False

    def _check_component_for_dependency(self, component_dir: Path, component_type: str, target_str: str) -> bool:
        """Check if a component depends on the target.

        Args:
        ----
            component_dir: Component directory to check
            component_type: Type of component
            target_str: Target dependency string to find

        Returns:
        -------
            True if dependency is found, False otherwise

        Raises:
        ------
            IOError: If there are issues reading the config file
            ValueError: If there are issues parsing the config file

        """
        config_path = component_dir / _get_default_configuration_file_name_from_type(component_type.rstrip("s"))
        if not config_path.exists():
            return False

        try:
            config = load_autonolas_yaml(component_type.rstrip("s"), component_dir)[0]

            # Check all possible dependency fields
            for field in ["dependencies", "protocols", "contracts", "connections", "skills", "customs"]:
                if field not in config:
                    continue

                if self._check_dependency_field(config[field], target_str):
                    log_msg = (
                        f"Found dependency in {component_type}/{component_dir.parent.name}/"
                        f"{component_dir.name} under {field}"
                    )
                    self.logger.info(log_msg)
                    return True

            return False

        except (OSError, ValueError) as e:
            self.logger.warning(f"Error checking dependencies in {config_path}: {e}")
            return False

    def _find_dependent_components(self, target_id: PublicId) -> list[tuple[PublicId, str]]:
        """Find all components that depend on the target component.

        Args:
        ----
            target_id: The PublicId of the component to find dependents for

        Returns:
        -------
            List of tuples containing (component_id, component_type) for each dependent

        """
        dependents = []
        vendor_dir = Path.cwd() / "vendor"
        if not vendor_dir.exists():
            return dependents

        # Component types to check
        component_types = ["agents", "protocols", "contracts", "connections", "skills", "customs"]
        target_str = f"{target_id.author}/{target_id.name}"

        self.logger.info(f"Searching for components that depend on {target_str}")

        # Search through all components in vendor directory
        for component_type in component_types:
            type_dir = vendor_dir / component_type
            if not type_dir.exists():
                continue

            # Check each author's directory
            for author_dir in type_dir.iterdir():
                if not author_dir.is_dir():
                    continue

                # Check each component
                for component_dir in author_dir.iterdir():
                    if not component_dir.is_dir():
                        continue

                    # Skip if this is our target component
                    if author_dir.name == target_id.author and component_dir.name == target_id.name:
                        continue

                    # Check if this component depends on our target
                    if self._check_component_for_dependency(component_dir, component_type, target_str):
                        component_id = PublicId(author_dir.name, component_dir.name)
                        if (component_id, component_type.rstrip("s")) not in dependents:
                            dependents.append((component_id, component_type.rstrip("s")))

        return dependents

    def _clean_component_directories(self, component_id: PublicId, component_type: str) -> None:
        """Clean up existing component directories.

        Args:
        ----
            component_id: ID of the component
            component_type: Type of the component

        Raises:
        ------
            OSError: If directory cleanup fails

        """
        for possible_dir in [
            Path.cwd() / f"{component_type}s" / component_id.name,  # Local dir
            Path.cwd() / f"{component_type}s" / self.config.fork_id.name,  # New name local dir
            # Vendor dir
            Path.cwd() / "vendor" / f"{component_type}s" / component_id.author / component_id.name,
        ]:
            if possible_dir.exists():
                self.logger.info(f"Cleaning up existing directory: {possible_dir}")
                shutil.rmtree(possible_dir)

    def _handle_root_component(self, component_dir: Path, component_id: PublicId, new_name: str) -> Path:
        """Handle root component specific operations.

        Args:
        ----
            component_dir: Current component directory
            component_id: ID of the component
            new_name: New name for the component

        Returns:
        -------
            Updated component directory path

        Raises:
        ------
            OSError: If directory operations fail

        """
        new_dir = component_dir.parent / new_name
        if component_dir != new_dir:
            if new_dir.exists():
                shutil.rmtree(new_dir)
            component_dir.rename(new_dir)
            component_dir = new_dir

        # Update Python imports to use new component name
        self._update_python_imports(new_dir, component_id.name, new_name)
        return component_dir

    def _process_dependencies(self, dependencies: dict) -> None:
        """Process component dependencies recursively.

        Args:
        ----
            dependencies: Dictionary of dependencies

        """
        for dep_type, deps in dependencies.items():
            dep_type_singular = dep_type[:-1] if dep_type.endswith("s") else dep_type
            for dep_str in deps:
                dep_id = self._convert_dependency_to_public_id(dep_str)
                # Only eject if this dependency references our target component
                if dep_str.startswith(f"{self.config.public_id.author}/{self.config.public_id.name}"):
                    self._eject_single_component(dep_id, dep_type_singular)

    def _eject_single_component(
        self, component_id: PublicId, component_type: str, is_root: bool = False
    ) -> tuple[bool, dict[str, set[str]]]:
        """Eject a single component and its dependencies.

        Args:
        ----
            component_id: ID of the component to eject
            component_type: Type of the component
            is_root: Whether this is the root component being ejected

        Returns:
        -------
            Tuple of (success, dependencies)

        Raises:
        ------
            ValueError: If component ejection fails
            ConfigUpdateError: If configuration update fails
            OSError: If file operations fail

        """
        dep_key = self._get_dep_key(component_id, component_type)
        if dep_key in self.processed_deps:
            self.logger.debug(f"Skipping already processed dependency: {dep_key}")
            return True, {}

        self.processed_deps.add(dep_key)

        try:
            # Clean up existing directories
            self._clean_component_directories(component_id, component_type)

            # Run the eject command first to create the directory structure
            if not self._run_eject_command(component_id, component_type):
                return False, {}

            # Get the component directory after ejection
            component_dir = self._get_and_verify_component_dir(component_id, component_type)

            # For root component, use new name; for dependencies, keep original name
            new_name = self.config.fork_id.name if is_root else component_id.name

            # Handle root component specific operations
            if is_root:
                component_dir = self._handle_root_component(component_dir, component_id, new_name)

            # Get the config path
            config_path = component_dir / _get_default_configuration_file_name_from_type(component_type)

            # Get dependencies from the config
            dependencies = DependencyBuilder.build_dependency_tree_for_component(component_dir, component_type)

            # Process dependencies if needed
            if not is_root and not self.config.skip_dependencies:
                self._process_dependencies(dependencies)

            # Update the component's configuration
            self.update_config(config_path, self.config.fork_id.author, new_name, component_type)

            # Update references if this is a dependent component
            if not is_root:
                self._update_component_references(
                    component_dir,
                    component_type,
                    self.config.public_id,  # Original component
                    PublicId(self.config.fork_id.author, self.config.fork_id.name),  # New ID
                )

            # Fingerprint the component
            if not self._fingerprint_component(PublicId(self.config.fork_id.author, new_name), component_type):
                msg = f"Failed to fingerprint component {self.config.fork_id.author}/{new_name}"
                raise ValueError(msg)

            self.logger.info(
                f"Successfully ejected and fingerprinted {component_id} to " f"{self.config.fork_id.author}/{new_name}"
            )
            return True, dependencies

        except (OSError, shutil.Error) as e:
            msg = f"Failed to handle component files: {e}"
            raise ValueError(msg) from e
        except ConfigUpdateError as e:
            msg = f"Failed to update component configuration: {e}"
            raise ValueError(msg) from e
        except Exception as e:
            msg = f"Failed to eject component {component_id}: {e}"
            raise ValueError(msg) from e

    def eject(self) -> list[PublicId]:
        """Eject a component and all its dependencies recursively.

        Returns
        -------
            List of ejected component IDs

        Raises
        ------
            ValueError: If component ejection fails
            ConfigUpdateError: If configuration update fails
            OSError: If file operations fail

        """
        try:
            ejected_components = []

            # First find all components that depend on this one
            dependent_components = self._find_dependent_components(self.config.public_id)
            if dependent_components:
                self.logger.info(f"Found {len(dependent_components)} components depending on {self.config.public_id}:")
                for comp_id, comp_type in dependent_components:
                    self.logger.info(f"  - {comp_type}/{comp_id}")

                # Create a temporary config for each dependent component
                for comp_id, comp_type in dependent_components:
                    self.logger.info(f"Ejecting dependent component {comp_type}/{comp_id}")
                    # Create a new config for the dependent component, keeping its original name
                    dep_config = EjectConfig(
                        component_type=comp_type,
                        public_id=comp_id,
                        fork_id=PublicId(self.config.fork_id.author, comp_id.name),
                        base_path=self.config.base_path,
                        skip_dependencies=True,  # Skip to avoid circular dependencies
                    )
                    dep_ejector = ComponentEjector(dep_config)
                    success, _ = dep_ejector._eject_single_component(comp_id, comp_type, is_root=True)
                    if success:
                        # After ejecting the dependent component, update its references
                        component_dir = Path.cwd() / f"{comp_type}s" / comp_id.name
                        self._update_component_references(
                            component_dir,
                            comp_type,
                            self.config.public_id,
                            self.config.fork_id,
                        )
                        ejected_components.append(comp_id)
                    else:
                        self.logger.warning(f"Failed to eject dependent component {comp_type}/{comp_id}")

            # Then eject the target component
            success, _dependencies = self._eject_single_component(
                self.config.public_id, self.config.component_type, is_root=True
            )
            if success:
                ejected_components.append(self.config.public_id)
            else:
                return []
            return ejected_components

        except (OSError, shutil.Error) as e:
            msg = f"Failed to handle component files: {e}"
            raise ValueError(msg) from e
        except ConfigUpdateError as e:
            msg = f"Failed to update component configuration: {e}"
            raise ValueError(msg) from e
        except ValueError as e:
            msg = f"Failed to eject components: {e}"
            raise ValueError(msg) from e

    def run_command(self, command: str, shell: bool = False) -> tuple[bool, int]:
        """Run a command using the executor and return success and exit code."""
        self.executor.command = command if shell else command.split()
        success = self.executor.execute(verbose=True, shell=shell)
        return success, self.executor.return_code or 0

    def _update_references_recursively(self, data: any, new_author: str) -> any:
        """Recursively update references to ejected components in any data structure.

        Args:
        ----
            data: The data structure to update (dict, list, or scalar)
            new_author: The new author to use for references

        Returns:
        -------
            Updated data structure

        """
        if isinstance(data, dict):
            return {k: self._update_references_recursively(v, new_author) for k, v in data.items()}
        if isinstance(data, list):
            return [self._update_references_recursively(item, new_author) for item in data]
        if isinstance(data, str) and "/" in data:
            # Split into base reference and version/hash parts
            parts = data.split(":")
            base_ref = parts[0]
            version_hash = parts[1:] if len(parts) > 1 else []

            # Split the base reference into author/name
            if "/" in base_ref:
                _author, name = base_ref.split("/")

                # Only proceed if this is the component we're ejecting
                if name == self.config.public_id.name:
                    # Check both old and new dependency keys
                    old_dep_key = f"{self.config.component_type}/{self.config.public_id.author}/{name}"
                    new_dep_key = f"{self.config.component_type}/{new_author}/{self.config.fork_id.name}"

                    if old_dep_key in self.processed_deps or new_dep_key in self.processed_deps:
                        # Update to new author and new name
                        new_ref = f"{new_author}/{self.config.fork_id.name}"
                        # Add back version and hash if they existed
                        if version_hash:
                            new_ref = ":".join([new_ref, *version_hash])
                        return new_ref

            return data
        return data

    def update_config(self, config_path: Path, new_author: str, new_name: str, component_type: str) -> None:
        """Update a component's configuration with new author and name.

        Args:
        ----
            config_path: Path to the config file
            new_author: New author to use
            new_name: New name to use
            component_type: Type of component being updated

        """
        try:
            # Load the main config file
            config_file = _get_default_configuration_file_name_from_type(component_type)
            config_path = config_path.parent / config_file

            all_configs = load_autonolas_yaml(component_type, config_path.parent)

            if not all_configs:
                msg = f"Config file not found for {component_type} at {config_path}"
                raise FileNotFoundError(msg)

            main_config = all_configs[0]
            overrides = all_configs[1:] if len(all_configs) > 1 else []

            # Update main config
            if component_type == "agent":
                # For agent config, update all component lists
                component_lists = ["protocols", "contracts", "connections", "skills", "customs"]

                # Update references in all component lists
                for component_list in component_lists:
                    if component_list in main_config:
                        main_config[component_list] = [
                            self._update_references_recursively(comp, new_author)
                            for comp in main_config[component_list]
                        ]

                # Recursively update any other references in the config
                main_config = self._update_references_recursively(main_config, new_author)
            else:
                main_config["name"] = new_name
                main_config["author"] = new_author

            # Recursively update all references in overrides
            updated_overrides = [self._update_references_recursively(override, new_author) for override in overrides]

            # Write all configs back to the file
            write_to_file(config_path, [main_config, *updated_overrides], file_type=FileType.YAML)

            self.logger.info(f"Updated {component_type} configuration at {config_path}")

        except (FileNotFoundError, ValueError) as e:
            msg = f"Failed to update configuration: {e}"
            raise ValueError(msg) from e

    def _run_eject_command(self, component_id: PublicId, component_type: str) -> bool:
        """Run the aea eject command."""
        if component_type == "custom":
            # For customs, just copy from vendor to customs directory
            vendor_path = Path.cwd() / "vendor" / component_id.author / "customs" / component_id.name
            customs_path = Path.cwd() / "customs" / component_id.name
            if vendor_path.exists() and not customs_path.exists():
                customs_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(vendor_path, customs_path)
            return True
        success, _ = self.run_command(
            f"yes | aea -s eject {component_type} {component_id.author}/{component_id.name}", shell=True
        )
        return success

    def _get_and_verify_component_dir(self, component_id: PublicId, component_type: str) -> Path:
        """Get and verify the component directory exists."""
        # For custom components, check in customs directory with simplified path
        if component_type == "custom":
            # Just use the name for customs directory
            customs_dir = Path.cwd() / "customs" / component_id.name
            if customs_dir.exists():
                return customs_dir

            # If not found in customs, check vendor with full path
            vendor_dir = Path.cwd() / "vendor" / component_id.author / "customs" / component_id.name
            if vendor_dir.exists():
                return vendor_dir

        # For other components, check vendor directory first
        vendor_dir = Path.cwd() / "vendor" / f"{component_type}s" / component_id.author / component_id.name
        if vendor_dir.exists():
            return vendor_dir

        # If not in vendor, check in root directory (where it goes after ejection)
        root_dir = Path.cwd() / f"{component_type}s" / component_id.name
        if root_dir.exists():
            return root_dir

        msg = f"Component directory not found for {component_type}/{component_id}"
        raise ValueError(msg)

    def _fingerprint_component(self, component_id: PublicId, component_type: str) -> bool:
        """Run fingerprint command for a component.

        For custom components, we use by-path fingerprinting
        For other components, we use the standard fingerprint command.
        """
        if component_type == "custom":
            # For custom components, use by-path fingerprinting
            component_dir = self._get_and_verify_component_dir(component_id, component_type)
            success, _ = self.run_command(f"aea -s fingerprint by-path {component_dir}")
        else:
            # For other components, use standard fingerprinting
            success, _ = self.run_command(
                f"aea -s fingerprint {component_type} {component_id.author}/{component_id.name}"
            )
        return success

    def _update_and_cleanup(self) -> None:
        """Update agent config and cleanup directories."""
        agent_config_path = Path.cwd() / DEFAULT_AEA_CONFIG_FILE
        self.update_config(agent_config_path, self.config.fork_id.author, self.config.fork_id.name, "agent")
        self.cleanup_directories()


def eject_component(config: EjectConfig) -> list[PublicId]:
    """Eject a component and its dependents.

    Args:
    ----
        config: EjectConfig object containing ejection parameters

    Returns:
    -------
        List of ejected component IDs

    Raises:
    ------
        ValueError: If dependencies are skipped but not already ejected

    """
    ejector = ComponentEjector(config)
    return ejector.eject()
