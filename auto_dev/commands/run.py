"""Command to run an agent."""

import rich_click as click
from aea.skills.base import PublicId
from aea.configurations.base import PackageType

from auto_dev.base import build_cli
from auto_dev.utils import load_autonolas_yaml
from auto_dev.services.runner.runner import AgentRunner


TENDERMINT_RESET_TIMEOUT = 10
TENDERMINT_RESET_ENDPOINT = "http://localhost:8080/hard_reset"
TENDERMINT_RESET_RETRIES = 20

cli = build_cli()


@cli.command()
@click.argument(
    "agent_public_id",
    type=PublicId.from_str,
    required=False,
)
@click.option("-v", "--verbose", is_flag=True, help="Verbose mode.", default=False)
@click.option("--force", is_flag=True, help="Force overwrite of existing agent", default=False)
@click.option("--fetch/--no-fetch", help="Fetch from registry or use local agent package", default=True)
@click.pass_context
def run(ctx, agent_public_id: PublicId, verbose: bool, force: bool, fetch: bool) -> None:
    """Run an agent from the local packages registry or a local path.

    Example usage:
        adev run eightballer/my_agent  # Fetch and run from registry
        adev run eightballer/my_agent --no-fetch  # Run local agent package named my_agent
    """
    if not agent_public_id:
        # We set fetch to false if the agent is not provided, as we assume the user wants to run the agent locally.
        fetch = False
        agent_config = load_autonolas_yaml(PackageType.AGENT)[0]
        agent_public_id = PublicId.from_json(agent_config)
    logger = ctx.obj["LOGGER"]

    runner = AgentRunner(
        agent_name=agent_public_id,
        verbose=verbose,
        force=force,
        logger=logger,
        fetch=fetch,
    )
    runner.run()
    logger.info("Agent run complete. 😎")


if __name__ == "__main__":
    cli()  # pylint: disable=no-value-for-parameter
