"""Runner service to manage agent execution."""

import os
import sys
import time
import shutil
import platform
import subprocess
from copy import deepcopy
from typing import Any
from pathlib import Path
from textwrap import dedent
from dataclasses import dataclass

import docker
import requests
from docker.errors import NotFound
from aea.skills.base import PublicId
from aea_ledger_ethereum import EthereumCrypto
from aea.helpers.env_vars import is_env_variable
from aea.configurations.base import PackageId, PackageType
from aea.configurations.constants import DEFAULT_AEA_CONFIG_FILE

from auto_dev.utils import change_dir, map_os_to_env_vars, load_autonolas_yaml
from auto_dev.constants import DOCKERCOMPOSE_TEMPLATE_FOLDER
from auto_dev.exceptions import UserInputError
from auto_dev.workflow_manager import Task
from auto_dev.services.runner.base import AgentRunner


TENDERMINT_RESET_TIMEOUT = 10
TENDERMINT_RESET_ENDPOINT = "http://localhost:8080/hard_reset"
TENDERMINT_RESET_RETRIES = 20

DEFAULT_VERSION = "0.1.0"


@dataclass
class DevAgentRunner(AgentRunner):
    """Class to manage running an agent."""

    agent_name: PublicId
    verbose: bool
    force: bool
    logger: Any
    fetch: bool = False
    ipfs_hash: str | None = None
    use_tendermint: bool = True
    install_deps: bool = True
    ethereum_address: str | None = None
    env_file: str = ".env"

    def __post_init__(
        self,
    ):
        """Post init method to set the agents package_hash if needed."""
        if self.ipfs_hash:
            self.agent_name = PublicId(
                author=self.agent_name.author,
                name=self.agent_name.name,
                version=DEFAULT_VERSION,
                package_hash=self.ipfs_hash,
            )

    def run(self) -> None:
        """Run the agent."""
        agent_path = "." if not self.fetch else self.agent_name.name
        if self.fetch:
            self.fetch_agent()
        if not self.check_exists(locally=True, in_packages=False):
            self.logger.error(f"Local agent package {self.agent_name.name} does not exist.")
            sys.exit(1)
        self.logger.info(f"Changing to directory: {agent_path}")
        with change_dir(agent_path):
            self.check_tendermint() if self.use_tendermint else None
            self.setup()
            self.execute_agent()
        self.stop_tendermint() if self.use_tendermint else None

    def check_exists(self, locally=False, in_packages=True) -> bool:
        """Check if the agent exists."""

        if locally and in_packages:
            msg = "Cannot check both locally and in packages."
            raise UserInputError(msg)
        if locally:
            return self._is_locally_fetched() or self.is_in_agent_dir()
        if in_packages:
            return self._is_in_packages()
        return False

    def _is_locally_fetched(self):
        return Path(self.agent_name.name).exists()

    def is_in_agent_dir(self):
        """Check if the agent is in the agent directory."""
        return Path(DEFAULT_AEA_CONFIG_FILE).exists()

    def _is_in_packages(self):
        return Path(self.agent_package_path).exists()

    @property
    def agent_package_path(self):
        """Get the agent package path."""
        return Path("packages") / self.agent_name.author / "agents" / self.agent_name.name

    @property
    def agent_dir(self) -> Path:
        """Get the agent directory based on where it is found."""
        if self.is_in_agent_dir():
            return Path()
        if self._is_locally_fetched():
            return Path(self.agent_name.name)
        if self._is_in_packages():
            return self.agent_package_path
        msg = f"Agent not found. {self.agent_name} not found in local packages or agent directory."
        raise UserInputError(msg)

    def stop_tendermint(self) -> None:
        """Stop Tendermint."""
        self.execute_command(f"docker compose -f {DOCKERCOMPOSE_TEMPLATE_FOLDER}/tendermint.yaml kill")
        self.execute_command(f"docker compose -f {DOCKERCOMPOSE_TEMPLATE_FOLDER}/tendermint.yaml down")
        self.logger.info("Tendermint stopped. 🛑")

    def check_tendermint(self, retries: int = 0) -> None:
        """Check if Tendermint is running."""
        self.logger.info("Checking Tendermint status...")
        docker_engine = docker.from_env()
        os_name = platform.system()
        container_name = "tm_0"
        tm_overrides = map_os_to_env_vars(os_name)
        try:
            self.logger.debug(f"Looking for Tendermint container: {container_name}")
            res = docker_engine.containers.get(container_name)
            self.logger.info(f"Found Tendermint container with status: {res.status}")
            if res.status == "exited":
                res.remove()
                time.sleep(0.2)
                self.check_tendermint(retries + 1)
            if res.status == "running":
                self._attempt_hard_reset()
        except (subprocess.CalledProcessError, RuntimeError, NotFound) as e:
            self.logger.info(f"Tendermint container not found or error: {e}")
            if retries > 3:
                self.logger.exception(f"Tendermint is not running. Please install and run Tendermint using Docker. {e}")
                sys.exit(1)
            self.logger.info("Starting Tendermint... 🚀")
            self.start_tendermint(tm_overrides)
            time.sleep(2)
            return self.check_tendermint(retries + 1)
        if res.status != "running":
            self.logger.error("Tendermint is not healthy. Please check the logs.")
            sys.exit(1)

        self.logger.info("Tendermint is running and healthy ✅")
        return None

    def _attempt_hard_reset(self, attempts: int = 0) -> None:
        """Attempt to hard reset Tendermint."""
        if attempts >= TENDERMINT_RESET_RETRIES:
            self.logger.error(f"Failed to reset Tendermint after {TENDERMINT_RESET_RETRIES} attempts.")
            sys.exit(1)

        self.logger.info("Tendermint is running, executing hard reset...")
        try:
            response = requests.get(TENDERMINT_RESET_ENDPOINT, timeout=TENDERMINT_RESET_TIMEOUT)
            if response.status_code == 200:
                self.logger.info("Tendermint hard reset successful.")
                return
        except requests.RequestException as e:
            self.logger.info(f"Failed to execute hard reset: {e}")

        self.logger.info(f"Tendermint not ready (attempt {attempts + 1}/{TENDERMINT_RESET_RETRIES}), waiting...")
        time.sleep(1)
        self._attempt_hard_reset(attempts + 1)

    def fetch_agent(self) -> None:
        """Fetch the agent from registry if needed."""
        msg = "Fetching from the local package registry..."
        msg = "Fetching agent from local package registry..." if not self.ipfs_hash else "Fetching agent from IPFS..."

        self.logger.info(msg)

        if self.check_exists(locally=True, in_packages=False):
            if not self.force:
                self.logger.error(f"Agent `{self.agent_name}` already exists. Use --force to overwrite.")
                sys.exit(1)
            self.logger.info(f"Removing existing agent `{self.agent_name}` due to --force option.")
            self.execute_command(f"rm -rf {self.agent_name.name}")

        command = f"aea -s fetch {self.agent_name}"
        if not self.ipfs_hash:
            command += " --local"
        if not self.execute_command(command):
            self.logger.error(f"Failed to fetch agent {self.agent_name}.")
            sys.exit(1)
        if self.ipfs_hash:
            self.logger.info(f"Agent {self.agent_name} fetched successfully from IPFS.")

    def setup(self) -> None:
        """Setup the agent."""
        if not self.fetch:
            self.logger.info(f"Agent author: {self.agent_name.author}")
            self.logger.info(f"Agent name: {self.agent_name.name}")

        self.logger.info("Setting up agent keys...")
        self.manage_keys()

        self.logger.info("Detecting Necessary Overrides. ")
        self.extract_magic_overrides()

        self.logger.info("Installing dependencies...")
        self.install_dependencies() if self.install_deps else None

        self.logger.info("Setting up certificates...")
        self.issue_certificates()
        self.logger.info("Agent setup complete. 🎉")

    def extract_magic_overrides(self):
        """Extract the magic overrides necessary for concensus."""

        magic_overrides = {
            ".models.params.args.setup.all_participants": lambda: f'["{self.ethereum_address}"]',
        }

        _config, *overrides = load_autonolas_yaml(PackageType.AGENT, self.agent_dir)

        dotted_paths = {}
        # we go through each override and check if it is an imputed value

        def recurse_dictionary(dictionary, path=""):
            for key, value in dictionary.items():
                if isinstance(value, dict):
                    recurse_dictionary(value, path=f"{path}.{key}")
                elif is_env_variable(value):
                    dotted_paths[path + f".{key}"] = value

        for override in overrides:
            _type = override["type"]
            public_id = PublicId.from_str(override["public_id"])
            package_id = PackageId(package_type=PackageType(_type), public_id=public_id)
            path = f"{package_id.package_type.value}.{public_id.name}"
            recurse_dictionary(override, path=path)

        overrides = {}
        for key in dotted_paths:
            for magic_var, getter in magic_overrides.items():
                if magic_var in key:
                    _key = key.upper().replace(".", "_")
                    overrides[_key] = getter()

        def generate_env_vars(self) -> dict:
            """Generate the environment variables for the deployment."""
            # we read in the .env file and update the environment variables
            all_parts = {}
            if (Path("..") / self.env_file).exists():
                with open((Path("..") / self.env_file), encoding="utf-8") as file:
                    all_parts.update(dict(line.strip().split("=") for line in file if "=" in line))
            else:
                self.logger.warning(f"Environment file {self.env_file} not found.")
            return all_parts

        self._env_vars = overrides
        self._env_vars.update(generate_env_vars(self))

    def manage_keys(
        self,
        generate_keys: bool = True,
    ) -> None:
        """Manage keys based on the agent's default ledger configuration."""
        config = load_autonolas_yaml(PackageType.AGENT)[0]
        required_ledgers = config["required_ledgers"]
        if not required_ledgers:
            self.logger.error("No ledgers found in the agent configuration.")
            sys.exit(1)
        for ledger in required_ledgers:
            self.logger.info(f"Processing ledger: {ledger}")
            # We check if a key already exists for the ledger
            new_key_file = Path(f"{ledger}_private_key.txt")
            if new_key_file.exists():
                self.logger.info(f"Key file {new_key_file} already exists. Skipping key generation.")
                continue
            key_file = Path("..") / new_key_file
            if key_file.exists():
                self.setup_ledger_key(ledger, generate_keys=False, existing_key_file=key_file)
            else:
                self.setup_ledger_key(ledger, generate_keys)

        self.ethereum_address = EthereumCrypto().load_private_key_from_path("ethereum_private_key.txt").address

    def remove_keys(self) -> None:
        """Remove keys from the agent."""
        self.logger.info("Removing keys...")
        config = load_autonolas_yaml(PackageType.AGENT)[0]
        required_ledgers = config["private_key_paths"]
        for ledger in required_ledgers:
            cmd = f"aea -s remove-key {ledger}"
            self.execute_command(cmd)

        self.logger.info("Keys removed. 🔑")

    def setup_ledger_key(self, ledger: str, generate_keys, existing_key_file: Path | None = None) -> None:
        """Setup the agent with the ledger key."""
        key_file = Path(f"{ledger}_private_key.txt")
        commands_to_errors = []
        if existing_key_file:
            self.logger.info(f"Copying existing key file {existing_key_file} to {key_file}")
            shutil.copy(existing_key_file, key_file)
        elif key_file.exists():
            self.logger.error(f"Key file {key_file} already exists.")
        elif generate_keys:
            self.logger.info(f"Generating key for {ledger}...")
            commands_to_errors.append([f"aea -s generate-key {ledger}", f"Key generation failed for {ledger}"])
        commands_to_errors.append([f"aea -s add-key {ledger}", f"Key addition failed for {ledger}"])

        for command, error in commands_to_errors:
            result = self.execute_command(command)
            if not result:
                self.logger.error(error)
        self.logger.info(f"{ledger} key setup complete ✅")

    def install_dependencies(self) -> None:
        """Install agent dependencies."""
        self.execute_command("aea -s install")

    def issue_certificates(self) -> None:
        """Issue certificates for agent if needed."""
        if not Path("../certs").exists():
            self.execute_command("aea -s issue-certificates", verbose=True)
        else:
            self.execute_command("cp -r ../certs ./")

    def start_tendermint(self, env_vars=None) -> None:
        """Start Tendermint."""
        self.logger.info("Starting Tendermint with docker-compose...")
        try:
            result = self.execute_command(
                f"docker compose -f {DOCKERCOMPOSE_TEMPLATE_FOLDER}/tendermint.yaml up -d --force-recreate",
                env_vars=env_vars,
            )
            if not result:
                msg = "Docker compose command failed to start Tendermint"
                raise RuntimeError(msg)
            self.logger.info("Tendermint started successfully")
        except FileNotFoundError:
            self.logger.exception("Docker compose file not found. Please ensure Tendermint configuration exists.")
            sys.exit(1)
        except docker.errors.DockerException as e:
            self.logger.exception(
                f"Docker error: {e!s}. Please ensure Docker is running and you have necessary permissions."
            )
            sys.exit(1)
        except Exception as e:
            self.logger.exception(f"Failed to start Tendermint: {e!s}")

            msg = dedent("""
                         Please check that:
                         1. Docker is installed and running
                         2. Docker compose is installed
                         3. You have necessary permissions to run Docker commands
                         4. The Tendermint configuration file exists and is valid
                         """)
            self.logger.exception(msg)
            sys.exit(1)

    def execute_agent(
        self,
    ) -> None:
        """Execute the agent.
        - args: background (bool): Run the agent in the background.
        """
        self.logger.info("Starting agent execution...")
        try:
            result = self.execute_command("aea -s run --env ../.env", verbose=True, env_vars=self._env_vars)
            if result:
                self.logger.info("Agent execution completed successfully. 😎")
            else:
                self.logger.error("Agent execution failed.")
                sys.exit(1)
        except RuntimeError as error:
            self.logger.exception(f"Agent ended with error: {error}")
        except KeyboardInterrupt:
            self.logger.info("Agent execution interrupted.")
        self.logger.info("Agent execution complete. 😎")

    def execute_command(self, command: str, verbose=False, env_vars=None) -> None:
        """Execute a shell command."""
        current_vars = deepcopy(os.environ)
        if env_vars:
            current_vars.update(env_vars)
        task = Task(
            command=command,
            env_vars=current_vars,
            stream=verbose,
            verbose=verbose,
        ).work()
        if task.is_failed:
            self.logger.error(f"Command failed: {task.client.output}")
            msg = f"Command failed: {command}"
            if "KeyboardInterrupt" in str(task.client.exception):
                raise KeyboardInterrupt(msg)
            raise RuntimeError(msg)
        return task

    def get_version(self) -> str:
        """Get the version of the agent."""
        agent_config = load_autonolas_yaml(PackageType.AGENT, self.agent_dir)[0]
        return agent_config["version"]
