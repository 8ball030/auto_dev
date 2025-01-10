"""This module contains the logic for the fmt command."""

import shutil
from pathlib import Path

import rich_click as click
from aea.configurations.base import PublicId

from auto_dev.base import build_cli
from auto_dev.enums import FileType
from auto_dev.utils import change_dir, get_packages, write_to_file, load_aea_config
from auto_dev.constants import AUTO_DEV_FOLDER, AUTONOMY_PACKAGES_FILE
from auto_dev.exceptions import OperationError
from auto_dev.cli_executor import CommandExecutor


cli = build_cli()


def get_available_agents() -> list[str]:
    """Get the available agents."""
    packages = get_packages(Path(AUTO_DEV_FOLDER) / AUTONOMY_PACKAGES_FILE, "third_party", check=False, hashmap=True)
    return {f"{str(agent.parent.parent.stem)}/{str(agent.stem)}": ipfs_hash for agent, ipfs_hash in packages.items()}


available_agents = get_available_agents()


def update_author(public_id: PublicId) -> None:
    """Update the author in the recently created agent"""

    with change_dir(public_id.name):
        agent_config_yaml = load_aea_config()
        if agent_config_yaml["author"] != public_id.author:
            click.secho(
                f"Updating author in aea-config.yaml from {agent_config_yaml['author']} to {public_id.author}",
                fg="yellow",
            )
            agent_config_yaml["author"] = public_id.author
            write_to_file("aea-config.yaml", agent_config_yaml, FileType.YAML)


def publish_agent(public_id: PublicId, verbose: bool) -> None:
    """Publish an agent.
    :param public_id: the public_id of the agent.
    """
    publish_commands = [
        "aea publish --push-missing --local",
    ]
    with change_dir(public_id.name):
        # we have to do a horrible hack here, regards to the customs as they are not being published.
        # please see issue.
        agent_config_yaml = load_aea_config()
        for package in agent_config_yaml["customs"]:
            custom_id = PublicId.from_str(package)
            # We need to copy the customs to the parent now.
            customs_path = Path("vendor") / custom_id.author / "customs" / custom_id.name
            package_path = Path("..") / "packages" / custom_id.author / "customs" / custom_id.name
            if not package_path.exists():
                shutil.copytree(
                    customs_path,
                    package_path,
                )

        for command in publish_commands:
            command = CommandExecutor(
                command.split(" "),
            )
            click.secho(f"Executing command: {command.command}", fg="yellow")
            result = command.execute(verbose=verbose)
            if not result:
                msg = f"""
                Command failed: {command.command}
                Error: {command.stderr}
                stdout: {command.stdout}"""
                click.secho(msg, fg="red")
                raise OperationError(msg)
            click.secho("Agent published successfully.", fg="yellow")


@cli.command()
@click.argument(
    "public_id",
    type=PublicId.from_str,
)
@click.option("-t", "--template", type=click.Choice(available_agents), required=True)
@click.option("-f", "--force", is_flag=True, help="Force the operation.", default=False)
@click.option("-p", "--publish", is_flag=True, help="Publish the agent to the local registry.", default=True)
@click.option("-c", "--clean-up/--no-clean-up", is_flag=True, help="Clean up the agent after creation.", default=True)
@click.pass_context
def create(ctx, public_id: str, template: str, force: bool, publish: bool, clean_up: bool) -> None:
    """
    Create a new agent from a template.

    :param public_id: the public_id of the agent in the open-autonmy format i.e. `author/agent`
    :flag  template: the template to use.

    example usage:
        `adev create -t eightballer/frontend_agent new_author/new_agent`
    """
    name = public_id.name

    is_proposed_path_exists = Path(name).exists()
    if is_proposed_path_exists and not force:
        msg = (f"Directory {name} already exists. Please remove it or use the --force flag to overwrite it.",)
        click.secho(
            msg,
            fg="red",
        )
        raise FileExistsError(msg)

    if is_proposed_path_exists and force:
        click.secho(
            f"Directory {name} already exists. Removing it.",
            fg="yellow",
        )

        command = CommandExecutor(
            [
                "rm",
                "-rf",
                name,
            ]
        )
        click.secho(f"Executing command: {command.command}", fg="yellow")
        result = command.execute(verbose=ctx.obj["VERBOSE"])
        if not result:
            msg = f"Command failed: {command.command}"
            click.secho(msg, fg="red")
            raise OperationError(msg)
        click.secho("Command executed successfully.", fg="green")

    verbose = ctx.obj["VERBOSE"]
    logger = ctx.obj["LOGGER"]


    click.secho("Checking Python 3.11 availability...", fg="blue")
    command = CommandExecutor(
        [
            "python3.11",
            "--version"
        ]
    )
    result = command.execute(verbose=True)
    if not result:
        msg = "Python 3.11 is not installed. Please install it before proceeding."
        click.secho(msg, fg="red")
        return OperationError()


    click.secho("Removing existing Python environment...", fg="blue")
    command = CommandExecutor(
        [
            "poetry",
            "env",
            "remove",
            "python"
        ]
    )
    result = command.execute(verbose=True)
    if not result:
        click.secho("No existing Python environment to remove.", fg="yellow")


    click.secho("Initializing Poetry environment with Python 3.11...", fg="blue")
    command = CommandExecutor(
        [
            "poetry",
            "env",
            "use",
            "python3.11"
        ]
    )
    result = command.execute(verbose=True)
    if not result:
        msg = f"Command failed: {command.command}. Ensure Python 3.11 is installed and accessible."
        click.secho(msg, fg="red")
        return OperationError()
    click.secho("Poetry environment initialized successfully.", fg="green")

    # The poetry install step has been removed

    logger.info(f"Creating agent {name} from template {template}")

    ipfs_hash = available_agents[template]

    create_commands = [
        f"poetry run autonomy fetch {ipfs_hash} --alias {name}",
    ]

    for command in create_commands:
        command = CommandExecutor(
            command.split(" "),
        )
        click.secho(f"Executing command: {command.command}", fg="yellow")
        result = command.execute(verbose=verbose)
        if not result:
            msg = f"Command failed: {command.command}  failed to create agent {public_id!s}"
            click.secho(msg, fg="red")
            return OperationError(msg)
        click.secho("Command executed successfully.", fg="yellow")

    update_author(public_id=public_id)
    if publish:


        if not Path("packages").exists():
            command = CommandExecutor(["poetry", "run", "autonomy", "packages", "init"])
            result = command.execute(verbose=verbose)
            if not result:
                msg = f"Command failed: {command.command}"
                click.secho(msg, fg="red")
                return OperationError()
        publish_agent(public_id, verbose)

    if clean_up:
        command = CommandExecutor(
            [
                "rm",
                "-rf",
                name,
            ]
        )
        result = command.execute(verbose=verbose)
        if not result:
            msg = f"Command failed: {command.command}"
            click.secho(msg, fg="red")
            return OperationError()
        click.secho(f"Agent {name} cleaned up successfully.", fg="green")

    click.secho(f"Agent {name} created successfully.", fg="green")


    command = CommandExecutor(
        [
            "sh",
            "-c",
            "yes 'third_party' | autonomy packages lock"
        ]
    )
    result = command.execute(verbose=verbose)
    if not result:
        msg = f"Command failed: {command.command}"
        click.secho(msg, fg="red")
        return OperationError()
    click.secho("Packages locked successfully.", fg="green")
