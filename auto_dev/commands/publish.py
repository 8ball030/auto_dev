"""This module contains the logic for the publish command."""

import rich_click as click
from aea.configurations.base import PublicId

from auto_dev.base import build_cli
from auto_dev.constants import AGENT_PUBLISHED_SUCCESS_MSG
from auto_dev.exceptions import OperationError
from auto_dev.commands.run import DevAgentRunner
from auto_dev.services.package_manager.index import PackageManager


cli = build_cli()


@cli.command()
@click.argument(
    "public_id",
    type=PublicId.from_str,
    required=True,
)
@click.option(
    "--force/--no-force",
    is_flag=True,
    help="Force overwrite if package already exists",
    default=False,
)
@click.pass_context
def publish(ctx, public_id: PublicId = None, force: bool = False) -> None:
    r"""Publish an agent to the local registry.

    Required Parameters:

        public_id: The public ID of the agent (author/name format).

    Optional Parameters:

        force (--force/--no-force): Force overwrite if package exists. (Default: False)

    Usage:
        Basic publish:
            adev publish author/new_agent

        Publish with force overwrite:
            adev publish author/new_agent --force

        Publish without force:
            adev publish author/new_agent --no-force

        Publish from agent directory:
            cd my_agent
            adev publish author/new_agent
    """
    verbose = ctx.obj["VERBOSE"]
    logger = ctx.obj["LOGGER"]

    try:
        agent_runner = DevAgentRunner(
            agent_name=public_id,
            logger=logger,
            verbose=verbose,
            force=force,
        )
        if not agent_runner.is_in_agent_dir():
            msg = "Not in an agent directory (aea-config.yaml not found) Please enter the agent directory to publish"
            raise OperationError(msg)
        package_manager = PackageManager(verbose=verbose, agent_runner=agent_runner)
        package_manager.publish_agent(force=force, new_public_id=public_id)
        click.secho(AGENT_PUBLISHED_SUCCESS_MSG, fg="green")
        logger.info("Agent published successfully.")
    except OperationError as e:
        click.secho(str(e), fg="red")
        ctx.exit(1)
    except Exception as e:
        logger.exception(str(e))
        logger.exception("Agent publish failed. Please consider running with --verbose flag for more information.")
        ctx.exit(1)


if __name__ == "__main__":
    cli()  # pylint: disable=no-value-for-parameter
