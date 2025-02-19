"""This module contains the logic for the fmt command."""

import ast
import sys
import shutil
from pathlib import Path

import rich_click as click
from aea.configurations.base import PublicId

from auto_dev.base import build_cli
from auto_dev.utils import change_dir, get_packages, update_author
from auto_dev.constants import AUTO_DEV_FOLDER, AUTONOMY_PACKAGES_FILE
from auto_dev.exceptions import OperationError
from auto_dev.workflow_manager import WorkflowManager
from auto_dev.services.runner.runner import DevAgentRunner
from auto_dev.services.package_manager.index import PackageManager


cli = build_cli()


def update_tests(public_id: str, agent_runner: DevAgentRunner) -> None:
    """We read in the test files and update the agent name in the test files."""
    for test_file in agent_runner.agent_dir.glob("tests/test_*.py"):
        test_file = Path(test_file)
        test_file_content = test_file.read_text()
        test_file_ast = ast.parse(test_file_content)
        for node in test_file_ast.body:
            if isinstance(node, ast.Assign) and node.targets[0].id == "AGENT_NAME":
                node.value.s = public_id.name
            if isinstance(node, ast.Assign) and node.targets[0].id == "AUTHOR":
                node.value.s = public_id.author
        test_file.write_text(ast.unparse(test_file_ast))


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
    r"""Create a new agent from a template.

    Required Parameters:

        public_id: The public ID of the agent (author/name format).

        template (-t): The template to use for agent creation.

    Optional Parameters:

        force (-f): Force overwrite if agent exists locally. (Default: False)

        fetch (--fetch/--no-fetch): Whether to fetch agent from registry or use local package. (Default: True)

        clean_up (-c): Whether to clean up temporary files after creation. (Default: True)

    Examples
    --------
        Create with default template:
            adev create new_author/new_agent

        Create from specific template:
            adev create -t eightballer/frontend_agent new_author/new_agent

        Create with force overwrite:
            adev create -f new_author/new_agent

        Create without publishing:
            adev create --no-publish new_author/new_agent

        Create without cleanup:
            adev create --no-clean-up new_author/new_agent

    """
    verbose = ctx.obj["VERBOSE"]
    logger = ctx.obj["LOGGER"]
    agent_runner = DevAgentRunner(
        agent_name=public_id,
        logger=logger,
        verbose=verbose,
        force=force,
        ipfs_hash=available_agents[template],
    )
    for name in [
        agent_runner.agent_name.name,
        agent_runner.agent_package_path,
    ]:
        is_proposed_path_exists = Path(name).exists()
        if is_proposed_path_exists and not force:
            msg = f"Directory {name} already exists. " + "Please remove it or use the --force flag to overwrite it."
            click.secho(
                msg,
                fg="red",
            )
            sys.exit(1)

        if is_proposed_path_exists and force:
            shutil.rmtree(name)
            logger.info(
                f"Directory {name} removed successfully.",
            )

    logger.info(f"Creating agent {public_id} from template {template}")

    agent_runner.fetch_agent()

    with change_dir(agent_runner.agent_dir):
        update_author(public_id=public_id)
        update_tests(public_id=public_id, agent_runner=agent_runner)
        if publish:
            try:
                package_manager = PackageManager(verbose=verbose, agent_runner=agent_runner)
                # We're already in the agent directory after update_author
                package_manager.publish_agent(force=force)
                logger.info(
                    "Agent published successfully.",
                )
            except OperationError as e:
                click.secho(str(e), fg="red")
                raise click.Abort from e

    if clean_up:
        shutil.rmtree(agent_runner.agent_dir)
        logger.info(
            "Agent cleaned up successfully.",
        )
    logger.info(f"Agent {public_id!s} created successfully 🎉🎉🎉🎉")


@cli.command()
@click.argument(
    "public_id",
    type=PublicId.from_str,
)
@click.argument(
    "fsm_spec_file_path",
    type=click.Path(exists=True),
)
def create_from_fsm(public_id: PublicId, fsm_spec_file_path: str) -> None:
    """Create an agent from a finite state machine specification."""
    click.echo(f"Creating agent {public_id} from FSM specification {fsm_spec_file_path}")
    WorkflowManager()
