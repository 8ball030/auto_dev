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
from pathlib import Path

import rich_click as click
from aea.cli.utils.config import get_default_author_from_cli_config

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


@cli.command()
@click.option(
    "-t",
    "--type-of-repo",
    help="Type of repo to scaffold",
    type=click.Choice(TEMPLATES),
    required=True,
)
@click.argument("name", type=str, required=True)
@click.pass_context
def repo(ctx, name, type_of_repo):
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
                verbose=True,
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


if __name__ == "__main__":
    cli()  # pylint: disable=no-value-for-parameter
