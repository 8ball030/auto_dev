"""This module contains the service logic for publishing agents."""

import shutil
from pathlib import Path

from aea.configurations.base import PublicId, _get_default_configuration_file_name_from_type  # noqa
from aea.configurations.constants import DEFAULT_AEA_CONFIG_FILE
from aea.configurations.data_types import PackageType

from auto_dev.utils import change_dir, get_logger, update_author, load_autonolas_yaml
from auto_dev.exceptions import OperationError
from auto_dev.cli_executor import CommandExecutor


logger = get_logger()


class PackageManager:
    """Service for managing packages.

    Args:
    ----
        verbose: Whether to show verbose output during package operations.

    """

    def __init__(
        self,
        verbose: bool = False,
    ):
        self.verbose = verbose

    def ensure_local_registry(self) -> None:
        """Ensure a local registry exists.

        Raises
        ------
            OperationError: if the command fails.

        """
        if not Path("packages").exists():
            logger.info("Initializing local registry")
            command = CommandExecutor(["poetry", "run", "autonomy", "packages", "init"])
            result = command.execute(verbose=self.verbose)
            if not result:
                msg = f"Command failed: {command.command}"
                raise OperationError(msg)

    def _get_workspace_root(self) -> Path:
        """Get the workspace root directory (where packages directory should be).

        Returns
        -------
            Path to the workspace root directory.

        """
        current = Path.cwd()
        while current != current.parent:
            if (current / "packages").exists() or (current / "pyproject.toml").exists():
                return current
            current = current.parent
        return Path.cwd().parent

    def _get_package_config(self, component_type: str | None) -> tuple[str, str, dict]:
        """Get package configuration details.

        Args:
        ----
            component_type: Optional component type if publishing a component.

        Returns:
        -------
            Tuple of (package_type, config_file, config)

        Raises:
        ------
            OperationError: If not in correct directory or config file not found.

        """
        package_type = PackageType.AGENT if component_type is None else component_type
        config_file = (
            DEFAULT_AEA_CONFIG_FILE
            if component_type is None
            else _get_default_configuration_file_name_from_type(component_type)
        )

        if not Path(config_file).exists():
            msg = f"Not in correct directory ({config_file} not found)"
            raise OperationError(msg)

        config, *_ = load_autonolas_yaml(package_type)
        return package_type, config_file, config

    def _update_config_with_new_id(
        self, config: dict, new_public_id: PublicId | None, component_type: str | None
    ) -> tuple[str, str]:
        """Update config with new public ID if provided.

        Args:
        ----
            config: Package configuration
            new_public_id: Optional new public ID
            component_type: Optional component type

        Returns:
        -------
            Tuple of (name, author)

        """
        if new_public_id:
            update_author(new_public_id)
            if component_type is None:
                config["agent_name"] = new_public_id.name
            else:
                config["name"] = new_public_id.name
            config["author"] = new_public_id.author

        name = config.get("agent_name") or config.get("name")
        author = config["author"]
        return name, author

    def _get_package_path(self, author: str, name: str, component_type: str | None) -> Path:
        """Get the path where the package will be published.

        Args:
        ----
            author: Package author
            name: Package name
            component_type: Optional component type

        Returns:
        -------
            Path where package will be published

        """
        workspace_root = self._get_workspace_root()

        # For custom components, use simplified path structure
        if component_type == "custom":
            return workspace_root / "packages" / author / "customs" / name

        # For other components, use standard path structure
        package_type_dir = "agents" if component_type is None else f"{component_type}s"
        return workspace_root / "packages" / author / package_type_dir / name

    def _handle_custom_component(self, package_path: Path) -> None:
        """Handle publishing of custom components.

        Args:
        ----
            package_path: Path where component will be published

        Raises:
        ------
            OSError: If directory operations fail

        """
        # Create parent directories if they don't exist
        package_path.parent.mkdir(parents=True, exist_ok=True)
        # Copy the entire component directory to packages
        shutil.copytree(Path.cwd(), package_path, dirs_exist_ok=True)
        logger.debug(f"Copied custom component to {package_path}")

    def _handle_agent_customs(self, config: dict) -> None:
        """Handle customs when publishing an agent.

        Args:
        ----
            config: Agent configuration

        Raises:
        ------
            OSError: If directory operations fail

        """
        if "customs" not in config:
            return

        workspace_root = self._get_workspace_root()
        for package in config["customs"]:
            custom_id = PublicId.from_str(package)
            # For customs, use simplified path structure
            customs_path = Path("customs") / custom_id.name
            package_path = workspace_root / "packages" / custom_id.author / "customs" / custom_id.name
            if customs_path.exists() and not package_path.exists():
                package_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(customs_path, package_path)

    def _run_publish_commands(self) -> None:
        """Run the AEA publish commands.

        Raises
        ------
            OperationError: If command execution fails

        """
        publish_commands = ["aea publish --push-missing --local"]
        for command in publish_commands:
            cmd_executor = CommandExecutor(command.split(" "))
            result = cmd_executor.execute(verbose=self.verbose)
            if not result:
                msg = f"""
                Command failed: {cmd_executor.command}
                Error: {cmd_executor.stderr}
                stdout: {cmd_executor.stdout}"""
                raise OperationError(msg)

    def _publish_internal(
        self,
        force: bool = False,
        new_public_id: PublicId | None = None,
        component_type: str | None = None,
    ) -> None:
        """Internal function to handle publishing logic.

        Args:
        ----
            force: If True, remove existing package before publishing.
            new_public_id: Optional new public ID to publish as.
            component_type: Optional component type if publishing a component.

        Raises:
        ------
            OperationError: If publishing fails
            OSError: If file operations fail

        """
        # Get package configuration
        _package_type, _config_file, config = self._get_package_config(component_type)

        # Update config with new public ID if provided
        name, author = self._update_config_with_new_id(config, new_public_id, component_type)

        # Get package path
        package_path = self._get_package_path(author, name, component_type)
        logger.debug(f"Package path: {package_path}")

        # Handle existing package
        if package_path.exists():
            if force:
                logger.info(f"Removing existing package at {package_path}")
                shutil.rmtree(package_path)
            else:
                msg = f"Package already exists at {package_path}. Use --force to overwrite."
                raise OperationError(msg)

        # For custom components, just copy the directory
        if component_type == "custom":
            self._handle_custom_component(package_path)
            return

        # For other components, handle customs if this is an agent
        if component_type is None:
            self._handle_agent_customs(config)

        # Run AEA publish commands
        self._run_publish_commands()

    def publish_agent(
        self,
        force: bool = False,
        new_public_id: PublicId | None = None,
    ) -> None:
        """Publish an agent.

        Args:
        ----
            force: If True, remove existing package before publishing.
            new_public_id: Optional new public ID to publish as.

        Raises:
        ------
            OperationError: if the command fails.

        """
        # Initialize registry in workspace root
        workspace_root = self._get_workspace_root()
        with change_dir(workspace_root):
            self.ensure_local_registry()

        # Publish from agent directory (we're already there)
        self._publish_internal(force, new_public_id=new_public_id)

        logger.debug("Agent published!")

    def publish_component(
        self,
        component_type: str,
        force: bool = False,
        new_public_id: PublicId | None = None,
    ) -> None:
        """Publish a component.

        Args:
        ----
            component_type: Type of component to publish (e.g., 'skill', 'connection', etc.)
            force: If True, remove existing package before publishing.
            new_public_id: Optional new public ID to publish as.

        Raises:
        ------
            OperationError: if the command fails.

        """
        # Initialize registry in workspace root
        workspace_root = self._get_workspace_root()
        with change_dir(workspace_root):
            self.ensure_local_registry()

        # Publish from component directory
        self._publish_internal(force, new_public_id=new_public_id, component_type=component_type)

        logger.debug(f"Component {component_type} published!")
