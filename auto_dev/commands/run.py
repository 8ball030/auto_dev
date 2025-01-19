"""Command to run an agent."""

import os
import sys
import time
import platform
import subprocess
from copy import deepcopy
from enum import Enum
from typing import Any
from pathlib import Path
from dataclasses import dataclass

import docker
import rich_click as click
from docker.errors import NotFound
from aea.skills.base import PublicId

from auto_dev.base import build_cli
from auto_dev.utils import map_os_to_env_vars
from auto_dev.constants import DOCKERCOMPOSE_TEMPLATE_FOLDER
from auto_dev.cli_executor import CommandExecutor


cli = build_cli()


class SupportedLedger(Enum):
    """Supported ledger types."""

    ETHEREUM = "ethereum"
    COSMOS = "cosmos"
    SOLANA = "solana"


@dataclass
class AgentRunner:
    """Class to manage running an agent."""

    agent_name: PublicId
    verbose: bool
    force: bool
    logger: Any
    no_fetch: bool = False

    def run(self) -> None:
        """Run the agent."""
        if not self.no_fetch:
            self.fetch_agent()
        else:
            self.logger.info(f"Looking for local agent package in directory {self.agent_name.name}...")
            if not Path(self.agent_name.name).exists():
                self.logger.error(f"Local agent package {self.agent_name.name} does not exist.")
                sys.exit(1)
            self.logger.info(f"Found local agent package at {self.agent_name.name}")

        self.logger.info(f"Changing to directory: {self.agent_name.name}")
        self.change_directory(self.agent_name.name)
        self.check_tendermint()
        self.setup_agent()
        self.execute_agent()
        self.stop_tendermint()

    def stop_tendermint(self) -> None:
        """Stop Tendermint."""
        self.execute_command(f"docker compose -f {DOCKERCOMPOSE_TEMPLATE_FOLDER}/tendermint.yaml kill")
        self.execute_command(f"docker compose -f {DOCKERCOMPOSE_TEMPLATE_FOLDER}/tendermint.yaml down")
        self.logger.info("Tendermint stopped. 🛑")

    def check_tendermint(self, retries: int = 0) -> None:
        """Check if Tendermint is running."""
        self.logger.info("Checking Tendermint status...")
        docker_engine = docker.from_env()
        container_name = "tm_0"
        try:
            self.logger.info(f"Looking for Tendermint container: {container_name}")
            res = docker_engine.containers.get(container_name)
            self.logger.info(f"Found Tendermint container with status: {res.status}")

        except (subprocess.CalledProcessError, RuntimeError, NotFound) as e:
            self.logger.info(f"Tendermint container not found or error: {e}")
            if retries > 3:
                self.logger.error(f"Tendermint is not running. Please install and run Tendermint using Docker. {e}")
                sys.exit(1)
            self.logger.info("Starting Tendermint... 🚀")
            os_name = platform.system()
            tm_overrides = map_os_to_env_vars(os_name)
            self.start_tendermint(tm_overrides)
            time.sleep(2)
            return self.check_tendermint(retries + 1)

        if res.status != "running":
            self.logger.error("Tendermint is not healthy. Please check the logs.")
            sys.exit(1)

        self.logger.info("Tendermint is running and healthy ✅")

    def fetch_agent(self) -> None:
        """Fetch the agent from registry if needed."""
        self.logger.info(f"Fetching agent {self.agent_name} from the local package registry...")

        if Path(self.agent_name.name).exists():
            if not self.force:
                self.logger.error(f"Agent `{self.agent_name}` already exists. Use --force to overwrite.")
                sys.exit(1)
            self.logger.info(f"Removing existing agent `{self.agent_name}` due to --force option.")
            self.execute_command(f"rm -rf {self.agent_name.name}")

        command = f"aea -s fetch {self.agent_name} --local"
        if not self.execute_command(command):
            self.logger.error(f"Failed to fetch agent {self.agent_name}.")
            sys.exit(1)

    def setup_agent(self) -> None:
        """Setup the agent."""

        try:
            if not self.no_fetch:
                self.logger.info(f"Agent author: {self.agent_name.author}")
                self.logger.info(f"Agent name: {self.agent_name.name}")

            self.logger.info("Setting up agent keys...")
            self.manage_keys()

            self.logger.info("Installing dependencies...")
            self.install_dependencies()

            self.logger.info("Setting up certificates...")
            self.issue_certificates()

            self.logger.info("Agent setup complete. 🎉")
        except (subprocess.SubprocessError, OSError, RuntimeError) as e:
            self.logger.error(f"Failed to setup agent: {e}")
            sys.exit(1)

    def manage_keys(self) -> None:
        """Manage keys for supported ledgers."""
        for ledger in SupportedLedger:
            try:
                self.generate_key(ledger)
            except (subprocess.SubprocessError, OSError, RuntimeError) as e:
                self.logger.warning(f"Skipping {ledger.value} key generation: {e}")

    def generate_key(self, ledger: SupportedLedger) -> None:
        """Generate and manage keys for a specific ledger.

        Args:
            ledger: The ledger type to generate keys for
        """
        self.logger.info(f"Checking for existing {ledger.value} key...")

        try:
            result = subprocess.run(
                ["aea", "-s", "remove-key", ledger.value],
                capture_output=True,
                text=True,
            )
            if "no key registered" not in result.stderr.lower():
                self.logger.info(f"Removed existing {ledger.value} key")
        except (subprocess.SubprocessError, OSError) as e:
            self.logger.warning(f"Error while removing {ledger.value} key: {str(e)}")

        key_pattern = f"*{ledger.value}_private_key.txt"
        key_files = list(Path(".").glob(key_pattern)) + list(Path("..").glob(key_pattern))

        if key_files:
            key_file = key_files[0]
            if key_file.parent != Path("."):
                self.logger.info(f"Found {ledger.value} key in {key_file.parent}, copying...")
                try:
                    self.execute_command(f"cp {key_file} ./{ledger.value}_private_key.txt")
                except (subprocess.SubprocessError, OSError) as e:
                    self.logger.error(f"Failed to copy {ledger.value} key: {str(e)}")
                    raise
            else:
                self.logger.info(f"Found {ledger.value} key in current directory")

            try:
                self.execute_command(f"aea -s add-key {ledger.value} {ledger.value}_private_key.txt")
            except (subprocess.SubprocessError, OSError) as e:
                self.logger.error(f"Failed to add {ledger.value} key: {str(e)}")
                raise
        else:
            self.logger.info(f"No existing {ledger.value} key found, generating new one...")
            try:
                self.execute_command(f"aea -s generate-key {ledger.value}")
                self.execute_command(f"aea -s add-key {ledger.value} {ledger.value}_private_key.txt")
            except (subprocess.SubprocessError, OSError) as e:
                self.logger.error(f"Failed to generate and add {ledger.value} key: {str(e)}")
                raise

        self.logger.info(f"{ledger.value.capitalize()} key setup complete ✅")

    def install_dependencies(self) -> None:
        """Install agent dependencies."""
        self.execute_command("aea -s install")

    def issue_certificates(self) -> None:
        """Issue certificates for agent."""
        if not Path("../certs").exists():
            self.execute_command("aea -s issue-certificates")
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
                raise RuntimeError("Docker compose command failed to start Tendermint")
            self.logger.info("Tendermint started successfully")
        except FileNotFoundError:
            self.logger.error("Docker compose file not found. Please ensure Tendermint configuration exists.")
            sys.exit(1)
        except docker.errors.DockerException as e:
            self.logger.error(
                f"Docker error: {str(e)}. Please ensure Docker is running and you have necessary permissions."
            )
            sys.exit(1)
        except Exception as e:
            self.logger.error(f"Failed to start Tendermint: {str(e)}")
            self.logger.error("Please check that:")
            self.logger.error("1. Docker is installed and running")
            self.logger.error("2. Docker compose is installed")
            self.logger.error("3. You have necessary permissions to run Docker commands")
            self.logger.error("4. The Tendermint configuration file exists and is valid")
            sys.exit(1)

    def execute_agent(self) -> None:
        """Execute the agent."""
        self.logger.info("Starting agent execution...")
        try:
            subprocess.run(["aea", "-s", "run"], check=True)
            self.logger.info("Agent execution started.")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to start agent: {e}")
            sys.exit(1)

    def execute_command(self, command: str, verbose=None, env_vars=None) -> None:
        """Execute a shell command."""
        current_vars = deepcopy(os.environ)
        if env_vars:
            current_vars.update(env_vars)
        cli_executor = CommandExecutor(command=command.split(" "))
        result = cli_executor.execute(stream=True, verbose=verbose, env_vars=current_vars)
        if not result:
            self.logger.error(f"Command failed: {command}")
            self.logger.error(f"Error: {cli_executor.stderr}")
            sys.exit(1)
        return result

    def change_directory(self, directory: str) -> None:
        """Change the current working directory."""
        os.chdir(directory)


@cli.command()
@click.argument(
    "agent_public_id",
    type=PublicId.from_str,
    required=True,
)
@click.option("-v", "--verbose", is_flag=True, help="Verbose mode.", default=False)
@click.option("--force", is_flag=True, help="Force overwrite of existing agent", default=False)
@click.option("--fetch/--no-fetch", help="Fetch from registry or use local agent package", default=True)
@click.pass_context
def run(ctx, agent_public_id: PublicId, verbose: bool, force: bool, fetch: bool) -> None:
    """
    Run an agent from the local packages registry or a local path.

    Example usage:
        adev run eightballer/my_agent  # Fetch and run from registry
        adev run eightballer/my_agent --no-fetch  # Run local agent package named my_agent
    """
    logger = ctx.obj["LOGGER"]

    runner = AgentRunner(agent_name=agent_public_id, verbose=verbose, force=force, logger=logger, no_fetch=not fetch)
    runner.run()
    logger.info("Agent run complete. 😎")


if __name__ == "__main__":
    cli()  # pylint: disable=no-value-for-parameter
