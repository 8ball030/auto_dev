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
@click.pass_context
def dev(ctx, agent_public_id: PublicId, verbose: bool, force: bool, fetch: bool) -> None:
    """Run an agent from the local packages registry or a local path.

    Example usage:
        adev run dev eightballer/my_agent  # Fetch and run from registry
        adev run dev eightballer/my_agent --no-fetch  # Run local agent package named my_agent
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
@click.pass_context
def prod(
    ctx,
    service_public_id: PublicId,
    verbose: bool,
    force: bool,
    fetch: bool,
    keysfile: click.File,
    number_of_agents: int,
) -> None:
    """Run an agent in production mode.

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
    )
    runner.run()
    logger.info("Agent run complete. 😎")


if __name__ == "__main__":
    cli()  # pylint: disable=no-value-for-parameter
