"""This module contains the service logic for publishing agents."""

import json
import shutil
from pathlib import Path

from aea.cli.eject import get_package_path
from aea.configurations.base import PublicId, _get_default_configuration_file_name_from_type  # noqa
from aea.configurations.constants import AGENTS, PACKAGES, ITEM_TYPE_TO_PLURAL, DEFAULT_AEA_CONFIG_FILE
from aea.configurations.data_types import PackageId, PackageType

from auto_dev.utils import get_logger, update_author, load_autonolas_yaml
from auto_dev.constants import DEFAULT_ENCODING, DEFAULT_IPFS_HASH
from auto_dev.exceptions import OperationError
from auto_dev.workflow_manager import Task
from auto_dev.services.runner.runner import DEFAULT_VERSION, DevAgentRunner


ALREADY_EXISTS_MSG = "Agent already exists at packages {path}"
INCORRECT_PATH_MSG = "Not in an agent directory. Please run this command from an agent directory."
PACKAGES_NOT_FOUND = (
    "Packages ../packages/packages.json Please run `autonomy packages init` to initialize the registry."
)

logger = get_logger()


class PackageManager:
    """Service for managing packages.

    Args:
    ----
        verbose: Whether to show verbose output during package operations.

    """

    def __init__(
        self,
        agent_runner: DevAgentRunner = None,
        verbose: bool = False,
    ):
        self.agent_runner = agent_runner
        self.verbose = verbose

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

    def _get_workspace_root(self) -> Path:
        """Get the workspace root.

        Returns
        -------
            Path to workspace root i.e. the parent directory of the agent directory.

        """
        priority_paths = [
            Path.cwd() / PACKAGES,
            Path.cwd() / ".." / PACKAGES,
        ]
        for path in priority_paths:
            if path.exists():
                return path.parent
        raise OperationError(PACKAGES_NOT_FOUND)

    def _run_publish_commands(self) -> None:
        """Run the AEA publish commands.

        Raises
        ------
            OperationError: If command execution fails

        """
        tasks = [
            Task(command="aea -s publish --push-missing --local"),
            Task(command="autonomy packages lock", working_dir=self._get_workspace_root()),
        ]
        for task in tasks:
            task.work()
            if task.is_failed:
                msg = f"Command failed: {task.command}"
                raise OperationError(msg)

    def _publish_internal(
        self,
        force: bool = False,
        new_public_id: PublicId | None = None,
    ) -> None:
        """Internal function to handle publishing logic.


        # Get package configuration

        Args:
        ----
            force: If True, remove existing package before publishing.
            new_public_id: Optional new public ID to publish as. Updating config as needed.
            component_type: Optional component type if publishing a component.

        Raises:
        ------
            OperationError: If publishing fails
            OSError: If file operations fail

        """
        if new_public_id:
            update_author(new_public_id)

        config, *_ = load_autonolas_yaml(PackageType.AGENT)

        (
            author,
            name,
        ) = config["author"], config["agent_name"]
        # Get package paths
        dev, third_party = self.get_all_packages()

        agent_package_id = PackageId(
            public_id=PublicId(
                author=author,
                name=name,
                version=DEFAULT_VERSION,
                package_hash=DEFAULT_IPFS_HASH,
            ),
            package_type=PackageType.AGENT,
        )
        dev[agent_package_id] = Path.cwd()

        expected_agent_path = get_package_path(
            self.packages_path,
            ITEM_TYPE_TO_PLURAL[PackageType.AGENT.value],
            agent_package_id.public_id,
            is_vendor=False,
        )
        if Path(expected_agent_path).exists():
            msg = ALREADY_EXISTS_MSG.format(path=expected_agent_path)
            logger.warning(msg)
            if force:
                logger.warning("Force flag set, removing existing agent.")
                shutil.rmtree(expected_agent_path)
            else:
                raise OperationError(msg)

        self.add_to_packages(dev, third_party, overwrite=force)
        if force:
            self.clear_if_force(dev, third_party)
        self._run_publish_commands()
        self._copy_test_files(agent_package_id)

    def _copy_test_files(self, agent_package_id) -> None:
        """Copy test files to the packages directory.

        Raises
        ------
            OSError: If file operations fail

        """
        test_files = Path.cwd() / "tests"
        expected_agent_path = (
            self.packages_path / agent_package_id.public_id.author / AGENTS / agent_package_id.public_id.name
        )
        test_files_dest = Path(expected_agent_path, "tests")
        shutil.copytree(test_files, test_files_dest)

    @property
    def packages_path(self) -> Path:
        """Get the packages directory path."""
        return self._get_workspace_root() / PACKAGES

    @property
    def packages_file(self) -> Path:
        """Get the packages file path."""
        return self.packages_path / "packages.json"

    def get_current_packages(self) -> tuple[list[PackageId], list[PackageId]]:
        """Get the current packages from the local registry."""
        if not self.packages_file.exists():
            raise OperationError(PACKAGES_NOT_FOUND)
        if not self.packages_file.is_file():
            msg = f"Invalid packages file at {self.packages_path}"
            raise OperationError(msg)
        return json.loads(self.packages_file.read_text(encoding=DEFAULT_ENCODING))

    def add_to_packages(
        self, dev_packages: list[PackageId], third_party_packages: list[PackageId], overwrite=True
    ) -> None:
        """Add packages to the local registry json file, using the package manager.

        Args:
        ----
            dev_packages: List of dev packages to add
            third_party_packages: List of third party packages to add

        Raises:
        ------
            OperationError: If package addition fails

        """
        data = self.get_current_packages()

        for package_id in dev_packages:
            key = package_id.to_uri_path
            if key in data["dev"] and not overwrite:
                logger.warning(f"Package already exists in dev packages: {key} skipping.")
                continue
            try:
                key_hash = DEFAULT_IPFS_HASH if not package_id.public_id._package_hash else package_id.package_hash  # noqa
                data["dev"][key] = key_hash
            except ValueError as e:
                logger.exception(f"Error adding package: {e}")
                msg = f"Error adding package {key} to registry. {package_id}"
                raise OperationError(msg) from e
        for package_id in third_party_packages:
            key = package_id.to_uri_path
            if key in data["third_party"] and not overwrite:
                logger.warning(f"Package already exists in third party packages: {key} skipping.")
                if package_id.package_hash != data["third_party"][key]:
                    logger.warning(f"Package hash mismatch: {package_id.package_hash} != {data['third_party'][key]}")
                continue
            data["third_party"][key] = package_id.package_hash

        self.packages_file.write_text(json.dumps(data, indent=2), encoding=DEFAULT_ENCODING)

    def get_all_packages(
        self,
    ) -> tuple[list[PackageId], list[PackageId]]:
        """Get all packages in the local registry.

        Returns
        -------
            Tuple of (dev, third_party) packages

        """
        dev, third_party = {}, {}

        config, *_ = load_autonolas_yaml(PackageType.AGENT)
        for package_type in PackageType:
            if package_type in {PackageType.SERVICE, PackageType.AGENT}:
                continue
            key = ITEM_TYPE_TO_PLURAL[package_type.value]
            for public_id_str in config.get(key, []):
                public_id = PublicId.from_str(public_id_str)
                package_id = PackageId(public_id=public_id, package_type=package_type)
                third_party_path = get_package_path(Path.cwd(), package_type.value, public_id, is_vendor=True)
                dev_path = get_package_path(Path.cwd(), package_type.value, public_id, is_vendor=False)
                if Path(third_party_path).exists():
                    third_party[package_id] = third_party_path
                elif Path(dev_path).exists():
                    dev[package_id] = dev_path
        return dev, third_party

    def clear_if_force(self, dev: dict[PackageId, Path], third_party: dict[PackageId, Path]) -> None:
        """Clear the package from the packages directory if set to force.

        Args:
        ----
            dev: Dev packages
            agent_package_id: Agent package ID

        Raises:
        ------
            OSError: If directory operations fail

        """
        for data in [dev, third_party]:
            for package_id in data:
                item_type_plural = ITEM_TYPE_TO_PLURAL[package_id.package_type.value]
                package_path = Path(
                    self.packages_path, package_id.public_id.author, item_type_plural, package_id.public_id.name
                )
                if package_path.exists():
                    shutil.rmtree(package_path)
                    logger.warning(f"Removed package at {package_path}")

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
        if not Path(DEFAULT_AEA_CONFIG_FILE).exists():
            msg = "Not in an agent directory. Please run this command from an agent directory."
            raise OperationError(msg)
        # we check if there are keys and remove them
        if self.agent_runner:
            self.agent_runner.remove_keys()
        # Publish from agent directory (we're already there)
        self._publish_internal(force, new_public_id=new_public_id)
