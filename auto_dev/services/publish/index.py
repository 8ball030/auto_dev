"""This module contains the service logic for publishing agents."""

import shutil
import subprocess
from typing import Optional
from pathlib import Path

from aea.configurations.base import PublicId
from aea.configurations.constants import DEFAULT_AEA_CONFIG_FILE
from aea.configurations.data_types import PackageType

from auto_dev.utils import change_dir, get_logger, load_autonolas_yaml
from auto_dev.exceptions import OperationError
from auto_dev.cli_executor import CommandExecutor


logger = get_logger()


class PublishService:
    """Service for publishing agents."""

    def __init__(self, verbose: bool = False):
        """Initialize the publish service.

        Args:
            verbose: whether to show verbose output.
        """
        self.verbose = verbose

    def ensure_local_registry(self) -> None:
        """Ensure a local registry exists.

        Raises:
            OperationError: if the command fails.
        """
        if not Path("packages").exists():
            logger.info("Initializing local registry")
            command = CommandExecutor(["poetry", "run", "autonomy", "packages", "init"])
            result = command.execute(verbose=self.verbose)
            if not result:
                msg = f"Command failed: {command.command}"
                raise OperationError(msg)

    def _publish_agent_internal(self, force: bool = False) -> None:
        """Internal function to handle agent publishing logic.

        Args:
            force: If True, remove existing package before publishing.

        Raises:
            OperationError: if the command fails.
        """
        # Load config to get agent details
        aea_config, *_ = load_autonolas_yaml(PackageType.AGENT)
        agent_name = aea_config["agent_name"]
        author = aea_config["author"]

        # Check if package exists and handle force flag
        # Package path should be relative to parent directory
        parent_dir = Path("..") if Path(DEFAULT_AEA_CONFIG_FILE).exists() else Path(".")
        package_path = parent_dir / "packages" / author / "agents" / agent_name
        logger.info(f"Package path: {package_path}")

        if package_path.exists():
            if force:
                logger.info(f"Removing existing package at {package_path}")
                shutil.rmtree(package_path)
            else:
                msg = f"Package already exists at {package_path}. Use --force to overwrite."
                raise OperationError(msg)

        publish_commands = ["aea publish --push-missing --local"]
        # we have to do a horrible hack here, regards to the customs as they are not being published.
        # please see issue.
        for package in aea_config["customs"]:
            custom_id = PublicId.from_str(package)
            # We need to copy the customs to the parent now.
            customs_path = Path("vendor") / custom_id.author / "customs" / custom_id.name
            package_path = parent_dir / "packages" / custom_id.author / "customs" / custom_id.name
            if not package_path.exists():
                shutil.copytree(
                    customs_path,
                    package_path,
                )

        for command in publish_commands:
            command = CommandExecutor(
                command.split(" "),
            )
            result = command.execute(verbose=self.verbose)
            if not result:
                msg = f"""
                Command failed: {command.command}
                Error: {command.stderr}
                stdout: {command.stdout}"""
                raise OperationError(msg)

    def publish_agent(
        self,
        force: bool = False,
    ) -> None:
        """Publish an agent.

        Args:
            force: If True, remove existing package before publishing.

        Raises:
            OperationError: if the command fails.
        """
        # First verify we're in the right place
        if not Path(DEFAULT_AEA_CONFIG_FILE).exists():
            raise OperationError("Not in an agent directory (aea-config.yaml not found)")

        # Save current directory as we'll need to return here for publishing
        current_dir = Path.cwd()
        parent_dir = current_dir.parent if "packages" not in str(current_dir) else current_dir.parent.parent

        # Initialize registry from parent directory
        with change_dir(parent_dir):
            self.ensure_local_registry()

        # Publish from agent directory (we're already there)
        self._publish_agent_internal(force)

        logger.info("Agent published!")
