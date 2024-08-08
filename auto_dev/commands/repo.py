"""
Module to assist with repo setup and management.
contains the following commands;
    - scaffold
        - all
        - .gitignore
        . .githubworkflows
        . .README.md
        . pyproject.toml
"""

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List

import rich_click as click
from aea.cli.utils.config import get_default_author_from_cli_config
from rich.progress import Progress

from auto_dev.base import build_cli
from auto_dev.cli_executor import CommandExecutor
from auto_dev.constants import DEFAULT_ENCODING, SAMPLE_PYTHON_CLI_FILE, SAMPLE_PYTHON_MAIN_FILE, TEMPLATE_FOLDER
from auto_dev.utils import change_dir


def execute_commands(*commands: str, verbose: bool, logger, shell: bool = False) -> None:
    """Execute commands."""
    for command in commands:
        cli_executor = CommandExecutor(command=command.split(" "))
        result = cli_executor.execute(stream=False, verbose=verbose, shell=shell)
        if not result:
            logger.error(f"Command failed: {command}")
            logger.error(f"{cli_executor.stdout}")
            logger.error(f"{cli_executor.stderr}")
            sys.exit(1)


cli = build_cli()

render_args = {
    "project_name": "test",
    "author": get_default_author_from_cli_config(),
    "email": "8ball030@gmail.com",
    "description": "",
    "version": "0.1.0",
}

TEMPLATES = {f.name: f for f in Path(TEMPLATE_FOLDER).glob("*")}


class RepoScaffolder:
    """Class to scaffold a new repo."""

    def __init__(self, type_of_repo, logger, verbose):
        self.type_of_repo = type_of_repo
        self.logger = logger
        self.verbose = verbose
        self.scaffold_kwargs = render_args

    def scaffold(self):
        """Scaffold files for a new repo."""

        new_repo_dir = Path.cwd()
        template_folder = TEMPLATES[self.type_of_repo]
        for file in template_folder.rglob("*"):
            if not file.is_file() or "__pycache__" in file.parts:
                continue

            rel_path = file.relative_to(template_folder)
            content = file.read_text(encoding=DEFAULT_ENCODING)

            if file.suffix == ".template":
                content = content.format(**self.scaffold_kwargs)
                target_file_path = new_repo_dir / rel_path.with_suffix("")
            else:
                target_file_path = new_repo_dir / rel_path
            self.logger.info(f"Scaffolding `{str(target_file_path)}`")
            target_file_path.parent.mkdir(parents=True, exist_ok=True)
            target_file_path.write_text(content)


# We create a new command group
@cli.group()
def repo():
    """Repository management commands."""


@repo.command()
@click.option(
    "-t",
    "--type-of-repo",
    help="Type of repo to scaffold",
    type=click.Choice(TEMPLATES),
    required=True,
)
@click.argument("name", type=str, required=True)
def scaffold(ctx, name, type_of_repo):
    """Create a new repo and scaffold necessary files."""

    logger = ctx.obj["LOGGER"]
    verbose = ctx.obj["VERBOSE"]
    logger.info(f"Creating a new {type_of_repo} repo.")

    # this is important, since repo is expected to contain a nested folder
    # with the same name in order to be listed in pyproject.toml under packages
    render_args["project_name"] = name
    Path(name).mkdir(exist_ok=False)

    with change_dir(name):
        execute_commands("git init", "git checkout -b main", verbose=verbose, logger=logger)
        assert (Path.cwd() / ".git").exists()

        scaffolder = RepoScaffolder(type_of_repo, logger, verbose)
        scaffolder.scaffold()
        if type_of_repo == "autonomy":
            logger.info("Installing host deps. This may take a while!")
            execute_commands(
                "bash ./install.sh",
                verbose=verbose,
                logger=logger,
            )
            logger.info("Initialising autonomy packages.")
            execute_commands("autonomy packages init", verbose=verbose, logger=logger)
        elif type_of_repo == "python":
            src_dir = Path(name)
            src_dir.mkdir(exist_ok=False)
            logger.info(f"Scaffolding `{str(src_dir)}`")
            (src_dir / "__init__.py").touch()
            (src_dir / "main.py").write_text(SAMPLE_PYTHON_MAIN_FILE)
            (src_dir / "cli.py").write_text(SAMPLE_PYTHON_CLI_FILE.format(project_name=name))
        else:
            raise NotImplementedError(f"Unsupported repo type: {type_of_repo}")

        logger.info(f"{type_of_repo.capitalize()} successfully setup.")


@dataclass(frozen=True)
class AutonomyVersionSet:
    """Class to represent a set of autonomy versions."""

    dependencies = {
        "open-autonomy": '==0.15.2',
        "open-aea-test-autonomy": '==0.15.2',
        "open-aea-ledger-ethereum": "==1.55.0",
        "open-aea-ledger-solana": "==1.55.0",
        "open-aea-ledger-cosmos": "==1.55.0",
        "open-aea-cli-ipfs": "==1.55.0",
    }


def update_against_version_set(logger, dry_run: bool = False) -> List[str]:
    """
    Update the dependencies in the pyproject.toml file against the version set.
    """
    pyproject = Path("pyproject.toml")
    if not pyproject.exists():
        logger.error("No pyproject.toml found in current directory.")
        sys.exit(1)
    # We read in the contents of the file
    content = pyproject.read_text(encoding=DEFAULT_ENCODING)
    # We split the content by lines
    lines = content.split("\n")
    # We find the index of the dependencies section
    start_index = lines.index("[tool.poetry.dependencies]") + 1
    # We find the index of the end of the dependencies section
    end_index = start_index + 1

    for i in range(start_index + 1, len(lines)):
        if lines[i].startswith("["):
            end_index = i
            break
    # We extract the dependencies section
    dependencies = lines[start_index:end_index]
    # We extract the dependencies
    dependencies = [dep.split("=")[0].strip() for dep in dependencies if dep.strip()]
    # We create a new set of dependencies
    new_dependencies = AutonomyVersionSet().dependencies
    # We update the dependencies
    updates = []
    for dep in dependencies:
        # We check if the dependency is in the new set of dependencies and if the version string is in the line.
        if dep in new_dependencies and new_dependencies[dep] not in lines[start_index + dependencies.index(dep)]:
            # We update the version string
            lines[start_index + dependencies.index(dep)] = f'{dep} = "{new_dependencies[dep]}"'
            updates.append(dep)
    if updates:
        logger.info("The following dependencies have been updated:")
        for dep in updates:
            logger.info(f"{dep} -> {new_dependencies[dep]}")
    if not dry_run:
        with open("pyproject.toml", "w", encoding=DEFAULT_ENCODING) as f:
            f.write("\n".join(lines))
    return updates


@repo.command()
@click.option(
    "--lock",
    is_flag=True,
    help="Lock the dependencies after updating.",
    default=False,
)
@click.pass_context
def update_deps(ctx, lock: bool):
    """
    Update dependencies in the current repo.
    """
    logger = ctx.obj["LOGGER"]
    verbose = ctx.obj["VERBOSE"]
    # We read in the pyproject.toml file
    logger.info("Locking dependency file to ensure consistency.")
    # We use rich to display a spinner / progress bar
    updates = update_against_version_set(
        logger,
        dry_run=False,
    )
    if not updates:
        logger.info("No dependencies to update... Checking for changes.")
    if not lock:
        logger.info("Dependencies updated.")
        return
    commands = [
        "poetry update",
        "poetry lock --no-cache",
        "git status --porcelain",
    ]
    commands_to_results = {}
    with Progress() as progress:
        task = progress.add_task("[cyan]Executing commands to lock upstream dependencies...", total=len(commands))
        for command in commands:
            cli_executor = CommandExecutor(command.split(" "))
            result = cli_executor.execute(stream=False, verbose=verbose)
            if not result:
                logger.error(f"Command failed: {command}")
                logger.error(f"{cli_executor.stdout}")
                logger.error(f"{cli_executor.stderr}")
                sys.exit(1)
            commands_to_results[command] = result
            progress.advance(task)
    logger.info("Dependencies locked.")
    # We check if there are differences in the file
    if commands_to_results["git status --porcelain"]:
        logger.info("Changes detected in the dependency file.")
        logger.info("Please commit the changes to ensure consistency.")
        sys.exit(1)
    else:
        logger.info("No changes detected in the dependency file.")
        logger.info("Dependency file is up to date.")


if __name__ == "__main__":
    cli()  # pylint: disable=no-value-for-parameter
