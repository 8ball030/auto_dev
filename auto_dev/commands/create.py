"""This module contains the logic for the fmt command."""

import sys
from pathlib import Path

import rich_click as click
from aea.configurations.base import PublicId

from auto_dev.base import build_cli
from auto_dev.utils import change_dir, get_packages, update_author
from auto_dev.constants import AUTO_DEV_FOLDER, AUTONOMY_PACKAGES_FILE
from auto_dev.exceptions import OperationError
from auto_dev.cli_executor import CommandExecutor
from auto_dev.services.package_manager.index import PackageManager


cli = build_cli()


def get_available_agents() -> list[str]:
    """Get the available agents."""
    packages = get_packages(Path(AUTO_DEV_FOLDER) / AUTONOMY_PACKAGES_FILE, "third_party", check=False, hashmap=True)
    return {f"{agent.parent.parent.stem!s}/{agent.stem!s}": ipfs_hash for agent, ipfs_hash in packages.items()}


available_agents = get_available_agents()


@cli.command()
@click.argument(
    "public_id",
    type=PublicId.from_str,
)
@click.option(
    "-t", "--template", type=click.Choice(available_agents), required=True, default=list(available_agents.keys())[1]
)
@click.option("-f", "--force", is_flag=True, help="Force the operation.", default=False)
@click.option(
    "-p", "--publish/--no-publish", is_flag=True, help="Publish the agent to the local registry.", default=True
)
@click.option("-c", "--clean-up/--no-clean-up", is_flag=True, help="Clean up the agent after creation.", default=True)
@click.pass_context
def create(ctx, public_id: str, template: str, force: bool, publish: bool, clean_up: bool) -> None:
    """Create a new agent from a template.

    :param public_id: the public_id of the agent in the open-autonmy format i.e. `author/agent`
    :flag  template: the template to use.

    example usage:
        `adev create -t eightballer/frontend_agent new_author/new_agent`
    """
    agent_name = public_id.name
    verbose = ctx.obj["VERBOSE"]
    logger = ctx.obj["LOGGER"]
    package_path = str(Path("packages") / public_id.author / "agents" / public_id.name)
    for name in [
        agent_name,
        package_path,
    ]:
        is_proposed_path_exists = Path(name).exists()
        if is_proposed_path_exists and not force:
            msg = f"Directory {name} already exists. " "Please remove it or use the --force flag to overwrite it."
            click.secho(
                msg,
                fg="red",
            )
            sys.exit(1)

        if is_proposed_path_exists and force:
            command = CommandExecutor(
                [
                    "rm",
                    "-rf",
                    name,
                ]
            )
            logger.info(
                f"Directory {name} already exists. Removing with: {command.command}",
            )
            result = command.execute(verbose=ctx.obj["VERBOSE"])
            if not result:
                msg = f"Command failed: {command.command}"
                click.secho(msg, fg="red")
                raise OperationError(msg)
            logger.info(
                "Command executed successfully.",
            )

    logger.info(f"Creating agent {public_id} from template {template}")

    ipfs_hash = available_agents[template]

    create_commands = [
        f"poetry run autonomy fetch {ipfs_hash} --alias {agent_name}",
    ]

    for command in create_commands:
        command = CommandExecutor(
            command.split(" "),
        )
        logger.debug(
            f"Executing command: {command.command}",
        )
        result = command.execute(verbose=verbose)
        if not result:
            msg = f"Command failed: {command.command}  failed to create agent {public_id!s}"
            click.secho(msg, fg="red")
            return OperationError(msg)
        logger.debug(
            "Command executed successfully.",
        )

    with change_dir(agent_name):
        update_author(public_id=public_id)
        if publish:
            try:
                package_manager = PackageManager(verbose=verbose)
                # We're already in the agent directory after update_author
                package_manager.publish_agent(force=force)
                logger.info(
                    "Agent published successfully.",
                )
            except OperationError as e:
                click.secho(str(e), fg="red")
                raise click.Abort from e

    if clean_up:
        command = CommandExecutor(
            [
                "rm",
                "-rf",
                agent_name,
            ]
        )
        result = command.execute(verbose=verbose)
        if not result:
            msg = f"Command failed: {command.command}"
            click.secho(msg, fg="red")
            return OperationError(msg)
        logger.info(
            "Agent cleaned up successfully.",
        )
    logger.info(f"Agent {public_id!s} created successfully 🎉🎉🎉🎉")
    return None
