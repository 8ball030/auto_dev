"""
We release the package.
"""
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import rich_click as click
import toml

from auto_dev.base import build_cli
from auto_dev.cli_executor import CommandExecutor
from auto_dev.constants import DEFAULT_ENCODING


@dataclass
class Releaser:
    """
    class to mamange the versions
    """

    logger: Any
    dep_path: str = "pyproject.toml"
    verbose: bool = True

    def current_version(self):
        """
        We get the current version.
        """
        with open(self.dep_path, "r", encoding=DEFAULT_ENCODING) as file_pointer:
            data = toml.load(file_pointer)
        return data["tool"]["poetry"]["version"]

    def get_new_version(self):
        """
        We get the new version by incrementing the current version.
        if we are at v0.1.0 we will get v0.1.1
        current version is in the format v0.1.0
        """
        current_version = self.current_version()
        parts = current_version.split(".")
        parts[-1] = str(int(parts[-1]) + 1)
        return ".".join(parts)

    def update_version(self, new_version):
        """
        We update the version.
        """
        command = f"bumpversion {self.dep_path} --new-version {new_version}"
        self.logger.info(f"Running command:\n `{command}`")

        cli_tool = CommandExecutor(
            command=command.split(" "),
        )
        return cli_tool.execute(verbose=True, stream=True)

    def post_release(self, version):
        """
        We run the post release.
        """
        command = f"git push --set-upstream origin heads/v{version}"
        self.logger.info(f"Run command:\n {command}")
        result = subprocess.run(command, check=True, shell=True, env=os.environ)
        if not result.returncode == 0:
            self.logger.error("Failed to push the branch. 😭")
            return False
        command = "git push --tags"
        self.logger.info(f"Run command:\n {command}")
        result = subprocess.run(command, check=True, shell=True)
        if not result:
            self.logger.error("Failed to push the tag. 😭")
            return False
        return True

    def release(self):
        """
        We run the release.
        """
        self.logger.info("Running the release... 🚀")
        self.logger.info(f"Current version is {self.current_version()}. 🚀")
        self.logger.info(f"New version will be {self.get_new_version()}. 🚀")
        new_version = self.get_new_version()
        confirmation = input(f"Are you sure you want to release {new_version}? [y/N]")
        if confirmation.lower() != "y":
            self.logger.info("Release aborted. 😎")
            return False
        if not self.pre_release():
            self.logger.error("Pre release failed. 😭")
            return False
        self.update_version(new_version)
        if not self.post_release(new_version):
            self.logger.error("Post release failed. 😭")
            return False
        self.logger.info(f"New version is {new_version} 🎉")
        return True

    def pre_release(self):
        """
        We run the pre release.
        """
        # we checkout to a new branch for the release
        self.logger.info("Running the pre release... 🚀")
        if not self.is_repo_clean():
            self.logger.error("Repo is not clean. 😭 We will not release!")
            return False
        new_version = self.get_new_version()
        cli_tool = CommandExecutor(
            command=f"git checkout -b v{new_version}".split(" "),
        )
        result = cli_tool.execute(verbose=True, stream=True)
        if not result:
            self.logger.error("Failed to create the branch. 😭")
        return result

    def is_repo_clean(self):
        """
        We check the project is clean using a command to check if there are ANY changes.
        """
        self.logger.info("Checking the tree is clean... 🚀")
        result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True, check=False)
        # we check there are no changes
        return result.stdout == ""


cli = build_cli()


@cli.command()
@click.option(
    "-p",
    "--dep-path",
    default="pyproject.toml",
    help="The dependency path.",
    type=Path,
    required=True,
)
@click.option(
    "--verbose",
    default=False,
    help="Verbose mode.",
)
@click.pass_context
def release(
    ctx: click.Context,
    dep_path: Path,
    verbose: bool = False,
) -> None:
    """
    We release the package.
    """
    logger = ctx.obj["LOGGER"]
    logger.info("Releasing the package... 🚀")
    releaser = Releaser(dep_path=dep_path, verbose=verbose, logger=logger)
    if not releaser.release():
        logger.error("Release failed. 😭")
        raise click.Abort()
    logger.info("Done. 😎")


if __name__ == "__main__":
    cli()  # pylint: disable=no-value-for-parameter
