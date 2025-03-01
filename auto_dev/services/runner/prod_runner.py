"""Prod runner for running an agent."""

import os
import sys
import json
from copy import deepcopy
from typing import Any
from pathlib import Path
from contextlib import contextmanager, redirect_stdout
from dataclasses import dataclass

import rich
from aea.skills.base import PublicId
from aea.cli.push_all import push_all_packages
from aea.configurations.base import PackageType
from aea.cli.registry.settings import REGISTRY_REMOTE
from aea.configurations.constants import PACKAGES, SERVICES, DEFAULT_SERVICE_CONFIG_FILE
from autonomy.configurations.base import PACKAGE_TYPE_TO_CONFIG_CLASS

from auto_dev.utils import change_dir, load_autonolas_yaml
from auto_dev.exceptions import UserInputError
from auto_dev.cli_executor import CommandExecutor
from auto_dev.workflow_manager import Task
from auto_dev.services.runner.base import AgentRunner


TENDERMINT_RESET_TIMEOUT = 10
TENDERMINT_RESET_ENDPOINT = "http://localhost:8080/hard_reset"
TENDERMINT_RESET_RETRIES = 20


@contextmanager
def with_spinner():
    """Context manager to show spinner."""
    console = rich.get_console()
    with console.status("Please wait...", spinner="aesthetic"):
        yield


@dataclass
class ProdAgentRunner(AgentRunner):
    """Class to manage running an agent."""

    service_public_id: PublicId
    verbose: bool
    force: bool
    logger: Any
    fetch: bool = False
    keysfile: Path = "keys.json"
    number_of_agents: int = 1
    env_file: Path = Path(".env")

    def run(self) -> None:
        """Run the agent."""
        service_path = "." if not self.fetch else self.service_public_id.name
        if self.fetch:
            self.fetch_package()
        if not self.check_exists(locally=True, in_packages=False):
            self.logger.error(f"Local service package {self.service_public_id} does not exist.")
            sys.exit(1)

        self.push_all_packages()
        self.logger.debug(f"Changing to directory: {service_path}")
        with change_dir(service_path):
            self.setup()
            self.execute_agent()

    def check_exists(self, locally=False, in_packages=True) -> bool:
        """Check if the agent exists."""

        if locally and in_packages:
            msg = "Cannot check both locally and in packages."
            raise UserInputError(msg)
        if locally:
            return self._is_locally_fetched() or self.is_in_service_dir()
        if in_packages:
            return self._is_in_packages()
        return False

    def _is_locally_fetched(self):
        return Path(self.service_public_id.name).exists()

    def is_in_service_dir(self):
        """Check if the agent is in the agent directory."""
        return Path(DEFAULT_SERVICE_CONFIG_FILE).exists()

    def _is_in_packages(self):
        return Path(self.service_package_path).exists()

    @property
    def service_package_path(self):
        """Get the agent package path."""
        return Path(PACKAGES) / self.service_public_id.author / SERVICES / self.service_public_id.name

    @property
    def service_dir(self) -> Path:
        """Get the agent directory based on where it is found."""
        if self.is_in_service_dir():
            return Path()
        if self._is_locally_fetched():
            return Path(self.service_public_id.name)
        if self._is_in_packages():
            return self.service_package_path
        msg = f"Service not found. {self.service_public_id} not found in local packages or agent directory."
        raise UserInputError(msg)

    def fetch_package(self) -> None:
        """Fetch the package from registry if needed."""
        self.logger.info(f"Fetching service {self.service_public_id} from the local package registry...")

        if self.check_exists(locally=True, in_packages=False):
            if not self.force:
                self.logger.error(f"Agent `{self.service_public_id}` already exists. Use --force to overwrite.")
                sys.exit(1)
            self.logger.info(f"Removing existing service`{self.service_public_id}` due to --force option.")
            self.execute_command(f"rm -rf {self.service_public_id.name}")

        command = f"autonomy -s fetch {self.service_public_id} --local --service"
        if not self.execute_command(command):
            self.logger.error(f"Failed to fetch agent {self.service_public_id}.")
            sys.exit(1)

    def is_service_consensus(self) -> bool:
        """Process the service and determine if it requires consensus, i.e. tendermint."""
        _config, *_overrides = load_autonolas_yaml(PackageType.SERVICE, self.service_dir)

    def validate(self) -> None:
        """Validate the provided service to determine whether it can be built.

        Returns
        -------
            None
        Raises:
            UserInputError: If the service is not valid.

        """

        if not self.check_exists(locally=True, in_packages=False):
            self.logger.error(f"Service {self.service_public_id} not found.")
            sys.exit(1)
        _service, *_overrides = load_autonolas_yaml(PackageType.SERVICE, self.service_dir)
        # We need to check if the keyfile has the required keys for the service
        if not self.keysfile.exists():
            self.logger.error(f"Keys file {self.keysfile} not found.")
            sys.exit(1)
        if not self.keysfile.is_file():
            self.logger.error(f"Keys file {self.keysfile} is not a file.")
            sys.exit(1)

        available_keys = json.loads(self.keysfile.read_text())
        if len(available_keys) < 1:
            self.logger.error(f"Keys file {self.keysfile} does not contain any keys.")
            sys.exit(1)
        if len(available_keys) != self.number_of_agents:
            msg = (
                f"Number of keys in {self.keysfile} : {len(available_keys)} "
                + f"does not match the number of agents: {self.number_of_agents}"
            )
            self.logger.error(msg)
            sys.exit(1)

        # We now know we need to set the ALL_PARTICIPANTS key in the service configuration if it is present.

    def setup(self) -> None:
        """Setup the agent."""
        if not self.fetch:
            self.logger.info(f"Service author: {self.service_public_id.author}")
            self.logger.info(f"Service name: {self.service_public_id.name}")

        self.logger.info("Setting up the agent service...")
        self.validate()
        self.build_images()
        self.manage_keys()
        self.build_deployment()
        self.logger.info("Agent Service setup complete. 🎉")

    def build_images(self) -> None:
        """Build the deployment."""
        self.logger.info("Building the docker images...")
        self.execute_command("autonomy build-image --extra-dependency hypothesis", spinner=True)
        self.logger.info("Deployment images built successfully. 🎉")

    def push_all_packages(self) -> None:
        """Push all packages to the registry."""
        self.logger.info("Pushing all packages to the registry...")
        # We silence all output from click
        Task(command="make clean").work()
        Task(command="autonomy packages lock").work()
        with open(os.devnull, "w", encoding="utf-8") as f, redirect_stdout(f):
            push_all_packages(REGISTRY_REMOTE, retries=3, package_type_config_class=PACKAGE_TYPE_TO_CONFIG_CLASS)
        self.logger.info("All packages pushed successfully. 🎉")

    def build_deployment(self) -> None:
        """Build the deployment."""
        self.logger.info("Building the deployment...")
        env_vars = self.generate_env_vars()
        for key in env_vars:
            self.logger.info(f"Environment variable: {key} has been set!")
        self.execute_command(
            f"autonomy deploy build {self.keysfile} --o abci_build -ltm",
            env_vars=env_vars,
        )
        current_user = os.environ.get("USER")
        self.execute_command(f"sudo chown -R {current_user}: abci_build", shell=False)
        self.logger.info("Deployment built successfully. 🎉")

    def manage_keys(
        self,
    ) -> None:
        """Manage keys based on the services default ledger configuration."""
        with open(self.keysfile, encoding="utf-8") as file:
            self.all_participants = [f["address"] for f in json.load(file)]

    def generate_env_vars(self) -> dict:
        """Generate the environment variables for the deployment."""
        all_parts = {
            "ALL_PARTICIPANTS": json.dumps(self.all_participants),
        }
        # we read in the .env file and update the environment variables
        if (Path("..") / self.env_file).exists():
            with open(Path(".." / self.env_file), encoding="utf-8") as file:
                all_parts.update(dict(line.strip().split("=") for line in file if "=" in line))
        else:
            self.logger.warning(f"Environment file {self.env_file} not found.")
        return all_parts

    def execute_agent(
        self,
    ) -> None:
        """Execute the agent.
        - args: background (bool): Run the agent in the background.
        """
        self.logger.info("Starting agent execution...")

        task = Task(command="docker compose up -d --remove-orphans", working_dir="abci_build").work()
        if task.is_failed:
            msg = f"Agent execution failed. {task.client.output}"
            raise RuntimeError(msg)
        self.logger.info("Agent execution complete. 😎")

    def execute_command(self, command: str, verbose=None, env_vars=None, spinner=False, shell=False) -> None:
        """Execute a shell command."""
        current_vars = deepcopy(os.environ)
        if env_vars:
            current_vars.update(env_vars)
        cli_executor = CommandExecutor(command=command.split(" "))
        if spinner:
            with with_spinner():
                result = cli_executor.execute(stream=True, verbose=verbose, env_vars=current_vars, shell=shell)
        else:
            result = cli_executor.execute(stream=True, verbose=verbose, env_vars=current_vars, shell=shell)
        if not result:
            self.logger.error(f"Command failed: {command}")
            self.logger.error(f"Error: {cli_executor.stderr}")
            msg = f"Command failed: {command}"
            raise RuntimeError(msg)
        return result

    def get_version(self) -> str:
        """Get the version of the agent."""
        agent_config = load_autonolas_yaml(PackageType.SERVICE, self.service_dir)[0]
        return agent_config["version"]
