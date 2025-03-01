"""Command to run an agent."""

import sys
from pathlib import Path

import rich_click as click
from aea.skills.base import PublicId
from aea.configurations.base import PackageType

from auto_dev.base import build_cli
from auto_dev.utils import load_autonolas_yaml
from auto_dev.services.runner import DevAgentRunner, ProdAgentRunner


TENDERMINT_RESET_TIMEOUT = 10
TENDERMINT_RESET_ENDPOINT = "http://localhost:8080/hard_reset"
TENDERMINT_RESET_RETRIES = 20

cli = build_cli()


@cli.group()
def run() -> None:
    """Command group for running agents either in development mode or in production mode."""


@run.command()
@click.argument(
    "agent_public_id",
    type=PublicId.from_str,
    required=False,
)
@click.option("-v", "--verbose", is_flag=True, help="Verbose mode.", default=False)
@click.option("--force", is_flag=True, help="Force overwrite of existing agent", default=False)
@click.option("--fetch/--no-fetch", help="Fetch from registry or use local agent package", default=True)
@click.option("--use-tendermint/--no-use-tendermint", help="Use Tendermint for blockchain network", default=True)
@click.option("--install-deps/--no-install-deps", help="Install dependencies", default=True)
@click.option("--env-file", help="Path to the environment file.", type=str, default=".env")
@click.pass_context
def dev(
    ctx,
    agent_public_id: PublicId,
    verbose: bool,
    force: bool,
    fetch: bool,
    use_tendermint: bool,
    install_deps: bool,
    env_file: str,
) -> None:
    """Run an agent from the local packages registry or a local path.

    Required Parameters:

        agent_public_id: The public ID of the agent (author/name format).
            If not provided, uses the current directory's agent.

    Optional Parameters:

        verbose (-v): Enable verbose logging. Shows detailed output during execution. (Default: False)

        force (--force): Force overwrite if agent exists locally. (Default: False)

        fetch (--fetch/--no-fetch): Whether to fetch agent from registry or use local package. (Default: True)
            - If True: Fetches agent from local registry
            - If False: Uses agent from current directory or packages

        use-tendermint (--use-tendermint/--no-use-tendermint): Use Tendermint for blockchain network. (Default: True)
        install-deps (--install-deps/--no-install-deps): Install dependencies. (Default: True)

    Example usage:

        adev run dev eightballer/my_agent  # Fetch and run from registry

        adev run dev eightballer/my_agent --no-fetch

    Notes
    -----
        Prerequisites:
            - Docker for Tendermint
            - Valid agent configuration
            - Network connectivity

        Automatic Setup:
            - Agent setup and key generation
            - Dependency installation
            - Certificate management
            - Tendermint node management

        Features:
            - Supports multiple blockchain networks
            - Development and production modes
            - Automatic dependency resolution
            - Certificate management

        Error Handling:
            - Validates agent existence
            - Checks Tendermint health
            - Manages Docker containers
            - Handles network timeouts

    """

    if not agent_public_id:
        # We set fetch to false if the agent is not provided, as we assume the user wants to run the agent locally.
        fetch = False
        agent_config = load_autonolas_yaml(PackageType.AGENT)[0]
        name = agent_config["agent_name"]
        version = agent_config["version"]
        author = agent_config["author"]
        agent_public_id = PublicId.from_str(f"{author}/{name}:{version}")
    logger = ctx.obj["LOGGER"]

    runner = DevAgentRunner(
        agent_name=agent_public_id,
        verbose=verbose,
        force=force,
        logger=logger,
        fetch=fetch,
        use_tendermint=use_tendermint,
        install_deps=install_deps,
        env_file=Path(env_file),
    )
    runner.run()
    logger.info("Agent run complete. 😎")


@run.command()
@click.argument(
    "service_public_id",
    type=PublicId.from_str,
    required=False,
)
@click.option("-v", "--verbose", is_flag=True, help="Verbose mode.", default=False)
@click.option("--force/--no-force", is_flag=True, help="Force overwrite of existing service", default=False)
@click.option("--fetch/--no-fetch", help="Fetch from registry or use local service package", default=True)
@click.option("--keysfile", help="Path to the private keys file.", type=click.File(), default="keys.json")
@click.option("--number_of_agents", "-n", help="Number of agents to run.", type=int, default=1)
@click.option("--env-file", help="Path to the environment file.", type=str, default=".env")
@click.pass_context
def prod(
    ctx,
    service_public_id: PublicId,
    verbose: bool,
    force: bool,
    fetch: bool,
    keysfile: click.File,
    number_of_agents: int,
    env_file: click.File,
) -> None:
    """Run an agent in production mode.

    Required Parameters:

        service_public_id: The public ID of the service (author/name format).

    Optional Parameters:

        verbose (-v): Enable verbose logging. Shows detailed output during execution. (Default: False)

        force (--force/--no-force): Force overwrite if service exists locally. (Default: False)

        fetch (--fetch/--no-fetch): Whether to fetch service from registry or use local package. (Default: True)

        keysfile (--keysfile): Path to the private keys file. (Default: keys.json)

        number_of_agents (-n): Number of agents to run. (Default: 1)

    Example usage:

        adev run prod eightballer/my_service
    """

    logger = ctx.obj["LOGGER"]
    if not Path(keysfile.name).exists():
        logger.error(f"Keys file not found at {keysfile.name}")
        sys.exit(1)

    runner = ProdAgentRunner(
        service_public_id=service_public_id,
        verbose=verbose,
        logger=logger,
        force=force,
        fetch=fetch,
        keysfile=Path(keysfile.name).absolute(),
        number_of_agents=number_of_agents,
        env_file=Path(env_file),
    )
    runner.run()
    logger.info("Agent run complete. 😎")


if __name__ == "__main__":
    cli()  # pylint: disable=no-value-for-parameter
