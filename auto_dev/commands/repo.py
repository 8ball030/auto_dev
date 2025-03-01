"""Module to assist with repo setup and management.
contains the following commands;
    - scaffold
        - all
        - .gitignore
        . .githubworkflows
        . .README.md
        . pyproject.toml.
"""

import os
import sys
import difflib
from shutil import rmtree
from pathlib import Path
from dataclasses import dataclass

import requests
import rich_click as click
from rich import print  # pylint: disable=W0622
from rich.prompt import Prompt
from rich.progress import Progress, track
from aea.cli.utils.config import get_default_author_from_cli_config

from auto_dev.base import build_cli
from auto_dev.enums import UserInput
from auto_dev.utils import change_dir
from auto_dev.constants import (
    DEFAULT_TIMEOUT,
    TEMPLATE_FOLDER,
    DEFAULT_ENCODING,
    SAMPLE_PYTHON_CLI_FILE,
    SAMPLE_PYTHON_MAIN_FILE,
    CheckResult,
)
from auto_dev.cli_executor import CommandExecutor


AGENT_PREFIX = "AutoDev: ->: {msg}"

SKIPS = [
    "poetry.lock",
    "pyproject.toml",
    ".gitignore",
    "README.md",
    "packages.json",
    "tbump.toml",
]


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

    def __init__(self, type_of_repo, logger, verbose, render_overrides=None) -> None:
        self.type_of_repo = type_of_repo
        self.logger = logger
        self.verbose = verbose
        self.scaffold_kwargs = render_args
        if render_overrides:
            self.scaffold_kwargs.update(render_overrides)

    @property
    def template_files(self):
        """Get template files."""
        all_files = TEMPLATES[self.type_of_repo].rglob("*")
        results = []
        for file in all_files:
            if not file.is_file() or "__pycache__" in file.parts:
                continue
            results.append(file)
        return results

    def scaffold(
        self,
        write_files=True,
    ) -> None:
        """Scaffold files for a new repo."""
        new_repo_dir = Path.cwd()
        template_folder = TEMPLATES[self.type_of_repo]
        for file in track(
            self.template_files,
            description=f"Scaffolding {self.type_of_repo} repo",
            total=len(self.template_files),
        ):
            self.logger.debug(f"Scaffolding `{file!s}`")
            if file.is_dir():
                rel_path = file.relative_to(template_folder)
                target_file_path = new_repo_dir / rel_path
                target_file_path.mkdir(parents=True, exist_ok=True)
                continue
            rel_path = file.relative_to(template_folder)
            content = file.read_text(encoding=DEFAULT_ENCODING)
            if file.suffix == ".template":
                try:
                    content = content.format(**self.scaffold_kwargs)
                except IndexError as e:
                    self.logger.exception(f"Error formatting {file}")
                    self.logger.exception(f"Error: {e}")
                    continue
                target_file_path = new_repo_dir / rel_path.with_suffix("")
            else:
                target_file_path = new_repo_dir / rel_path
            self.logger.debug(f"Scaffolding `{target_file_path!s}`")
            if write_files:
                target_file_path.parent.mkdir(parents=True, exist_ok=True)
                target_file_path.write_text(content)

    def verify(
        self,
        fix_differences=False,
        yes=False,
    ):
        """Scaffold files for a new repo."""
        template_folder = TEMPLATES[self.type_of_repo]
        results = []
        self.logger.info(f"Verifying scaffolded files for {self.type_of_repo} repo.")
        self.logger.info(f"Total number of files to verify: {len(self.template_files)}")

        for file in track(self.template_files):
            rel_path = file.relative_to(template_folder)
            content = file.read_text(encoding=DEFAULT_ENCODING)

            if file.suffix == ".template":
                content = content.format(**self.scaffold_kwargs)
                target_file_path = rel_path.with_suffix("")
            else:
                target_file_path = rel_path
            if target_file_path.name in SKIPS:
                results.append(CheckResult.SKIPPED)
                continue
            self.logger.debug(f"Scaffolding `{target_file_path!s}`")
            actual_file = Path(target_file_path)
            actual_content = ""
            if actual_file.exists():
                actual_content = actual_file.read_text(encoding=DEFAULT_ENCODING)
            if content == actual_content:
                results.append(CheckResult.PASS)

                self.logger.debug(f"File {target_file_path} is as expected. ✅")
            else:
                self.logger.error(f"File {target_file_path} is not as expected. ❌")
                diffs = list(difflib.unified_diff(actual_content.splitlines(), content.splitlines()))
                for diff in diffs if self.verbose else []:
                    print(diff)

                if fix_differences:
                    if yes or click.confirm("Do you want to fix the differences(y/n)?\n"):
                        self.logger.info(f"Fixing differences in {target_file_path}")
                        Path(target_file_path).write_text(content, encoding=DEFAULT_ENCODING)
                        results.append(CheckResult.MODIFIED)
                    else:
                        results.append(CheckResult.FAIL)
                else:
                    results.append(CheckResult.FAIL)
        return results


# We create a new command group
@cli.group()
def repo() -> None:
    r"""Repository management commands.

    Available Commands:

        scaffold: Create and initialize a new repository with template files
        update_deps: Update and lock repository dependencies
    """


@repo.command()
@click.argument("name", type=str, required=True)
@click.option("-t", "--type-of-repo", help="Type of repo to scaffold", type=click.Choice(TEMPLATES), default="autonomy")
@click.option("-f", "--force", is_flag=True, help="Force overwrite of existing repo", default=False)
@click.option("--auto-approve", is_flag=True, help="Automatically approve all prompts", default=False)
@click.option("--install/--no-install", is_flag=True, help="Do not install dependencies", default=True)
@click.option("--initial-commit/--no-commit", is_flag=True, help="Add the initial commit. Requires git", default=True)
@click.pass_context
def scaffold(ctx, name, type_of_repo, force, auto_approve, install, initial_commit) -> None:
    r"""Create a new repository and scaffold necessary files.

    Required Parameters:

        name: Name of the repository to create

    Optional Parameters:

        type_of_repo (-t): Type of repository to scaffold (autonomy, python). (Default: autonomy)
        force (-f): Overwrite existing repository if it exists. (Default: False)
        auto_approve (-aa): Skip confirmation prompts. (Default: False)
        install (--install/--no-install): Install dependencies after scaffolding. (Default: True)
        initial_commit (--initial-commit/--no-commit): Create initial git commit. (Default: True)

    Usage:
        Create basic autonomy repo:
            adev repo scaffold my_repo

        Create Python repo:
            adev repo scaffold my_repo -t python

        Force overwrite existing repo:
            adev repo scaffold my_repo -f

        Skip dependency installation:
            adev repo scaffold my_repo --no-install

    Notes
    -----
        - Creates a new git repository in the specified directory
        - For autonomy repos:
            - Installs host dependencies via install.sh
            - Initializes autonomy packages
        - For Python repos:
            - Creates src directory with __init__.py
            - Adds sample main.py and cli.py files

    """

    logger = ctx.obj["LOGGER"]
    logger.info(f"Creating a new {type_of_repo} repo.")
    verbose = ctx.obj["VERBOSE"]
    scaffold_new_repo(logger, name, type_of_repo, force, auto_approve, install, initial_commit, verbose)
    logger.info(f"Repository `{name}` successfully created.")


def scaffold_new_repo(logger, name, type_of_repo, force, auto_approve, install, initial_commit, verbose) -> None:
    """Scaffold a new repo."""
    render_args["project_name"] = name
    if Path(name).exists() and not force:
        logger.error(f"Repo `{name}` already exists.\n\tPlease choose a different name or use the --force flag.")
        sys.exit(1)
    if Path(name).exists() and force:
        if not auto_approve:
            warning_msg = f"Overwrite existing repo `{name}`? This will delete all existing files. 💀 "
            confirm = Prompt.ask(
                AGENT_PREFIX.format(msg=warning_msg), choices=[UserInput.YES.value, UserInput.NO.value]
            )
            if UserInput(confirm) is UserInput.NO:
                logger.info("Exiting. No changes made.")
                sys.exit(1)
        logger.info(f"Overwriting existing repo `{name}`.")
        rmtree(name)
    Path(name).mkdir(exist_ok=False, parents=True)
    with change_dir(name):
        execute_commands("git init", "git checkout -b main", verbose=verbose, logger=logger)
        assert (Path.cwd() / ".git").exists()

        scaffolder = RepoScaffolder(type_of_repo, logger, verbose)
        scaffolder.scaffold()
        if type_of_repo == "autonomy":
            logger.info("Installing host deps. This may take a while!")
            if install:
                execute_commands("bash ./install.sh", verbose=verbose, logger=logger)

            if initial_commit:
                git_commands = ["git init", "git add .", "git commit -m 'feat-first-commit-from-StationsStation'"]
                execute_commands(*git_commands, verbose=verbose, logger=logger)

            logger.info("Initialising autonomy packages.")

        elif type_of_repo == "python":
            src_dir = Path(name)
            src_dir.mkdir(exist_ok=False)
            logger.debug(f"Scaffolding `{src_dir!s}`")
            (src_dir / "__init__.py").touch()
            (src_dir / "main.py").write_text(SAMPLE_PYTHON_MAIN_FILE)
            (src_dir / "cli.py").write_text(SAMPLE_PYTHON_CLI_FILE.format(project_name=name))
        else:
            msg = f"Unsupported repo type: {type_of_repo}"
            raise NotImplementedError(msg)
        logger.info(f"{type_of_repo.capitalize()} successfully setup.")


@dataclass(frozen=True)
class AutonomyVersionSet:
    """Class to represent a set of autonomy versions."""

    dependencies = {
        "open-autonomy": "==0.15.2",
        "open-aea-test-autonomy": "==0.15.2",
        "open-aea-ledger-ethereum": "==1.55.0",
        "open-aea-ledger-solana": "==1.55.0",
        "open-aea-ledger-cosmos": "==1.55.0",
        "open-aea-cli-ipfs": "==1.55.0",
    }


def update_against_version_set(logger, dry_run: bool = False) -> list[str]:
    """Update the dependencies in the pyproject.toml file against the version set."""
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
def update_deps(ctx, lock: bool) -> None:
    r"""Update and lock repository dependencies.

    Optional Parameters:

        lock (--lock): Lock dependencies after updating. Default: False

    Usage:

        Update dependencies:
            adev repo update-deps

        Update and lock dependencies:
            adev repo update-deps --lock

    Notes
    -----
        - Updates dependencies in packages.json
        - Optionally locks dependency versions
        - Checks for changes in dependency files
        - Prompts to commit changes if detected
        - Exits with error if uncommitted changes exist

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
        task = progress.add_task("[cyan]Executing commands dependencies...", total=len(commands))
        for command in commands:
            print(f"Executing command:\n\n    `{command}`\n")
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


def create_github_repo(repo_name, token, user: str, private: bool = False, is_org: bool = False):
    """Create a new repository on Github."""
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    data = {
        "name": repo_name,
        "private": private,
        "auto_init": False,
    }
    if is_org:
        data["organization"] = user
        url = f"https://api.github.com/orgs/{user}/repos"
    else:
        url = "https://api.github.com/user/repos"
        data["owner"] = user
    print(f"Creating repository `{repo_name}` on Github. for user `{user}`")
    response = requests.post(url, headers=headers, json=data, timeout=DEFAULT_TIMEOUT)
    if response.status_code == 201:
        return response.json()
    return response.json()


@repo.command()
@click.option("--repo", type=str, required=False, help="Name of the repository to create")
@click.option("--user", help="Github user", type=str, required=True)
@click.option("--private", help="Make the repo private", is_flag=False, default=True)
@click.option("--token", help="Github token", type=str, required=False)
@click.option("--org", help="Create the repository under an organization", is_flag=True, default=False)
@click.pass_context
def create_remote(ctx, repo, token, user, private, org) -> None:
    r"""Create a new repository on Github.

    Required Parameters:

        user (--user): Github user. to create the repository under.

    Optional Parameters:

        repo_name: Name of the repository to create

        token (--token): Github token. (Default: None)

        private (--private): Make the repository private. (Default: False)

    Usage:
        Create a new repository:
            adev repo create-github-repo my_repo

        Create a new private repository:
            adev repo create-github-repo my_repo --private

    Notes
    -----
        - Creates a new repository on Github
        - Requires a Github token to authenticate
        - Optionally makes the repository private
        - Returns the response from the Github API

    """
    logger = ctx.obj["LOGGER"]
    if not repo:
        repo = Path.cwd().name
    if not token:
        token = os.environ.get("GITHUB_PAT")

    response = create_github_repo(repo, token, user, private, org)
    if "message" in response:
        logger.error(f"Error creating repository: {response}")
        logger.error(f"Error creating repository: {response['message']}")
        sys.exit(1)
    logger.info(f"Repository `{repo}` created successfully!")


if __name__ == "__main__":
    cli()  # pylint: disable=no-value-for-parameter
