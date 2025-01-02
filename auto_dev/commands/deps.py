"""reads in 2 github repos.

One is the parent repo, the other is the child repo.

The child repo is dependent on the parent repo.

When there is a change in the parent repo, we want to update the child repo.

The dependencies are defined in a file called packages/packages.json

this is structures as follows:

{
    "dev": {
        "aea_dep1": "ipfshash",
        "aea_dep2": "ipfshash",
        },
    "third_party": {
        "aea_dep3": "ipfshash",
        "aea_dep4": "ipfshash",
        },
}

The ipfshash is the hash of the package.

We want to be able to update the hash of the package.

"""

import os
import sys
import shutil
import logging
import traceback
from enum import Enum
from typing import Dict, List
from pathlib import Path
from dataclasses import dataclass

import toml
import yaml
import requests
import rich_click as click
from rich import print_json
from rich.progress import track

from auto_dev.base import build_cli
from auto_dev.utils import FileType, FileLoader, write_to_file
from auto_dev.constants import DEFAULT_TIMEOUT, DEFAULT_ENCODING
from auto_dev.exceptions import AuthenticationError, NetworkTimeoutError


PARENT = Path("repo_1")
CHILD = Path("repo_2")


def get_package_json(repo: Path) -> dict[str, dict[str, str]]:
    """We get the package json."""
    package_json = repo / "packages" / "packages.json"
    with open(package_json, encoding=DEFAULT_ENCODING) as file_pointer:
        return yaml.safe_load(file_pointer)


def write_package_json(repo: Path, package_dict: dict[str, dict[str, str]]) -> None:
    """We write the package json."""
    package_json = repo / "packages" / "packages.json"
    write_to_file(str(package_json), package_dict, FileType.JSON, indent=4)


def get_package_hashes(repo: Path) -> dict[str, str]:
    """We get the package hashes."""
    package_dict = get_package_json(repo)
    package_hashes = {}
    for package_type_dict in package_dict.values():
        for package_name, package_hash in package_type_dict.items():
            package_hashes[package_name] = package_hash
    return package_hashes


def get_proposed_dependency_updates(parent_repo: Path, child_repo: Path) -> dict[str, str]:
    """We get the proposed dependency updates."""
    parent_package_hashes = get_package_hashes(parent_repo)
    child_package_hashes = get_package_hashes(child_repo)
    proposed_dependency_updates = {}
    for package_name, package_hash in parent_package_hashes.items():
        if package_name in child_package_hashes and package_hash != child_package_hashes[package_name]:
            proposed_dependency_updates[package_name] = package_hash
    return proposed_dependency_updates


def update_package_json(repo: Path, proposed_dependency_updates: dict[str, str]) -> None:
    """We update the package json."""
    package_dict = get_package_json(repo)
    for package_type, package_type_dict in package_dict.items():
        for package_name in package_type_dict:
            if package_name in proposed_dependency_updates:
                package_dict[package_type][package_name] = proposed_dependency_updates[package_name]
    write_package_json(repo, package_dict)


def from_key_to_path(key: str) -> Path:
    """We get the path from the key string some examples of the keys are;
    agent/eightballer/custom_balance_poller/0.1.0
    where the folder to be removed is;
    packages/eightballer/agents/custom_balance_poller.
    """
    parts = key.split("/")

    path_list = [
        "packages",
        parts[1],
        parts[0] + "s",
        parts[2],
    ]
    return Path(*path_list)


def remove_old_package(repo: Path, proposed_dependency_updates: dict[str, str]) -> None:
    """We remove the old package directories."""
    for package_name in proposed_dependency_updates:
        path = from_key_to_path(package_name)
        path = repo / path
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)


def main(
    parent_repo: Path,
    child_repo: Path,
    logger: logging.Logger,
    auto_confirm: bool = False,
) -> None:
    """We run the main function."""
    try:
        proposed = get_proposed_dependency_updates(parent_repo=parent_repo, child_repo=child_repo)
    except FileNotFoundError:
        logger.debug(traceback.format_exc())
        logger.exception("The packages.json file does not exist. Exiting. 😢")
        return False
    if not proposed:
        logger.info("No changes required. 😎")
        return False
    for package_name, package_hash in proposed.items():
        logger.info(f"Updating {package_name} to {package_hash}")
    if not auto_confirm:
        click.confirm("Do you want to update the package?", abort=True)
    logger.info("Updating the packages json... 📝")
    update_package_json(repo=child_repo, proposed_dependency_updates=proposed)
    logger.info("Removing the old packages directories... 🗑")
    remove_old_package(repo=child_repo, proposed_dependency_updates=proposed)
    # we now copy the new packages over.
    logger.info("Copying the new packages over... 📝")
    for package_name in proposed:
        path = from_key_to_path(package_name)
        parent_path = parent_repo / path
        child_path = child_repo / path
        shutil.copytree(parent_path, child_path)
    logger.info("Done. 😎")
    return True


cli = build_cli()


class DependencyType(Enum):
    """Type of dependency."""

    AUTONOMY = "autonomy"
    PYTHON = "python"
    GIT = "git"


class DependencyLocation(Enum):
    """Location of the dependency."""

    LOCAL = "local"
    REMOTE = "remote"


@dataclass
class Dependency:
    """A dependency."""

    name: str
    version: str
    location: DependencyLocation


@dataclass
class PythonDependency(Dependency):
    """A python dependency."""

    type: DependencyType.PYTHON


@dataclass
class AutonomyDependency(Dependency):
    """An autonomy dependency."""

    type: DependencyType.AUTONOMY


@dataclass
class GitDependency(Dependency):
    """A git dependency."""

    type = DependencyType.GIT
    autonomy_dependencies: Dict[str, Dependency] = None
    url: str = None
    plugins: List[str] = None
    extras: List[str] = None

    @property
    def headers(self) -> Dict[str, str]:
        """Get the headers."""
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Authorization": f"Bearer {os.getenv('GITHUB_TOKEN')}",
        }
        return headers

    def get_latest_version(self) -> str:
        """Get the latest version."""
        if self.location == DependencyLocation.LOCAL:
            return self.version
        return self._get_latest_remote_version()

    def _get_latest_remote_version(self) -> str:
        """Get the latest remote version."""
        tag_url = f"{self.url}/releases"
        res = requests.get(tag_url, headers=self.headers, timeout=DEFAULT_TIMEOUT)
        if res.status_code != 200:
            if res.status_code == 403:
                raise AuthenticationError("Error: Rate limit exceeded. Please add a github token.")
            raise NetworkTimeoutError(f"Error: {res.status_code} {res.text}")
        data = res.json()
        latest_version = data[0]["tag_name"]
        return latest_version

    def get_all_autonomy_packages(self):
        """Read in the autonomy packages. the are located in the remote url."""
        tag = self.get_latest_version()
        file_path = "packages/packages.json"
        remote_url = f"{self.url}/contents/{file_path}?ref={tag}"
        data = requests.get(remote_url, headers=self.headers, timeout=DEFAULT_TIMEOUT)

        if data.status_code != 200:
            raise NetworkTimeoutError(f"Error: {data.status_code} {data.text}")
        dl_url = data.json()["download_url"]
        data = requests.get(dl_url, headers=self.headers, timeout=DEFAULT_TIMEOUT).json()
        autonomy_packages = data["dev"]
        return autonomy_packages


@cli.group()
@click.pass_context
def deps(
    ctx: click.Context,  # noqa
) -> None:
    """Commands for managing dependencies.
    - update: Update both the packages.json from the parent repo and the packages in the child repo.
    - generate_gitignore: Generate the gitignore file from the packages.json file.
    """


@click.option(
    "-p",
    "--parent-repo",
    default=".",
    help="The parent repo.",
    type=Path,
    required=True,
)
@click.option(
    "-c",
    "--child-repo",
    help="The child repo.",
    type=Path,
    required=True,
    default=".",
)
@click.option(
    "--auto-confirm",
    default=False,
    help="Auto confirm the changes.",
)
@click.option(
    "--location",
    default=DependencyLocation.LOCAL,
    type=DependencyLocation,
    help="The location of the dependency.",
)
@deps.command()
@click.pass_context
def update(
    ctx: click.Context,
    parent_repo: Path,
    child_repo: Path,
    location: DependencyLocation = DependencyLocation.LOCAL,
    auto_confirm: bool = False,
) -> None:
    """We update aea packages.json dependencies from a parent repo.
    Example usage:
        adev deps update -p /path/to/parent/repo -c /path/to/child/repo.
    """
    logger = ctx.obj["LOGGER"]
    logger.info("Updating the dependencies... 📝")
    logger.info(f"Parent repo: {parent_repo}")
    logger.info(f"Child repo: {child_repo}")
    logger.info(f"Location: {location}")
    if parent_repo == DependencyLocation.REMOTE:
        parent_repo = Path("parent_repo")
    logger = ctx.obj["LOGGER"]
    logger.info("Updating the dependencies... 📝")

    result = main(parent_repo=parent_repo, child_repo=child_repo, auto_confirm=auto_confirm, logger=logger)
    if not result:
        sys.exit(1)
    logger.info("Done. 😎")


# We have a command to generate the gitignore file.
@deps.command()
@click.pass_context
def generate_gitignore(
    ctx: click.Context,
) -> None:
    """We generate the gitignore file from the packages.json file
    Example usage:
        adev deps generate_gitignore.
    """
    package_dict = get_package_json(repo=Path())
    third_party_packages = package_dict.get("third_party", {})
    third_party_paths = [from_key_to_path(key) for key in third_party_packages]
    current_gitignore = Path(".gitignore").read_text(encoding=DEFAULT_ENCODING)
    for path in third_party_paths:
        # we check if the path is in the gitignore file.
        if str(path) in current_gitignore:
            continue
        with open(".gitignore", "a", encoding=DEFAULT_ENCODING) as file_pointer:
            file_pointer.write(f"\n{path}")
    ctx.obj["LOGGER"].info("Done. 😎")


@dataclass
class AutonomyDependencies:
    """A set of autonomy versions."""

    upstream_dependency: List[GitDependency]

    def to_dict(self):
        """return a list of the upstream dependencies."""
        return [
            {
                "name": dependency.name,
                "version": dependency.version,
                "location": dependency.location.value,
                "url": dependency.url,
                "plugins": dependency.plugins,
                "extras": dependency.extras,
            }
            for dependency in self.upstream_dependency
        ]


@dataclass
class PoetryDependencies:
    """A set of poetry dependencies."""

    poetry_dependencies: List[GitDependency]

    def to_dict(self):
        """return a list of the poetry dependencies."""
        return [
            {
                "name": dependency.name,
                "version": dependency.version,
                "location": dependency.location.value,
                "url": dependency.url,
                "plugins": dependency.plugins,
                "extras": dependency.extras,
            }
            for dependency in self.poetry_dependencies
        ]


open_autonomy_repo = GitDependency(
    name="open-autonomy",
    version="0.15.2",
    location=DependencyLocation.REMOTE,
    url="https://api.github.com/repos/valory-xyz/open-autonomy",
    plugins=["open-aea-test-autonomy"],
)

open_aea_repo = GitDependency(
    name="open-aea",
    version="1.55.0",
    location=DependencyLocation.REMOTE,
    url="https://api.github.com/repos/valory-xyz/open-aea",
    plugins=[
        "open-aea-ledger-ethereum",
        "open-aea-ledger-solana",
        "open-aea-ledger-cosmos",
        "open-aea-cli-ipfs",
    ],
)

auto_dev_repo = GitDependency(
    name="autonomy-dev",
    version="0.2.79",
    location=DependencyLocation.REMOTE,
    url="https://api.github.com/repos/8ball030/auto_dev",
    extras=["all"],
)

autonomy_version_set = AutonomyDependencies(
    upstream_dependency=[
        open_autonomy_repo,
        open_aea_repo,
    ]
)

poetry_dependencies = PoetryDependencies(
    [
        auto_dev_repo,
        open_autonomy_repo,
        open_aea_repo,
    ]
)


# We then use this to construct a to_yaml function such that we can read in from a configfile.


DEFAULT_ADEV_CONFIG_FILE = Path("adev_config.yaml")
# yaml

"""
autonomy_dependencies:
  - name: open-autonomy
    version: 0.15.2
    location: remote
    url: https://api.github.com/repos/valory-xyz/open-autonomy
  - name: open-aea
    version: 1.55.0
    location: remote
    url: https://api.github.com/repos/valory-xyz/open-aea


poetry_dependencies:
  - name: autonomy-dev
    version: 0.2.73
    location: remote
    url: https://api.github.com/repos/8ball030/auto_dev
    extras:
      - all
  - name: open-autonomy
    version: 0.15.2
    location: remote
    url: https://api.github.com/repos/valory-xyz/open-autonomy
  - name: open-aea
    version: 1.55.0
    location: remote
    url: https://api.github.com/repos/valory-xyz/open-aea
    plugins:
      - open-aea-ledger-ethereum
      - open-aea-ledger-solana
      - open-aea-ledger-cosmos
      - open-aea-cli-ipfs   
"""


class VersionSetLoader:
    """We load the version set."""

    autonomy_dependencies: AutonomyDependencies
    poetry_dependencies: PoetryDependencies

    def __init__(self, config_file: Path = DEFAULT_ADEV_CONFIG_FILE):
        self.config_file = config_file

    def write_config(
        self,
    ):
        """Write the config file."""
        data = {
            "autonomy_dependencies": self.autonomy_dependencies.to_dict(),
            "poetry_dependencies": self.poetry_dependencies.to_dict(),
        }
        FileLoader(self.config_file, FileType.YAML).write(data)

    def load_config(self):
        """Load the config file."""
        with open(self.config_file, "r") as file_pointer:
            data = yaml.safe_load(file_pointer)
        self.autonomy_dependencies = AutonomyDependencies(
            upstream_dependency=[
                GitDependency(
                    name=dependency["name"],
                    version=dependency["version"],
                    location=DependencyLocation(dependency["location"]),
                    url=dependency["url"],
                    plugins=dependency.get("plugins"),
                    extras=dependency.get("extras"),
                )
                for dependency in data["autonomy_dependencies"]
            ]
        )

        self.poetry_dependencies = PoetryDependencies(
            poetry_dependencies=[
                GitDependency(
                    name=dependency["name"],
                    version=dependency["version"],
                    location=DependencyLocation(dependency["location"]),
                    url=dependency["url"],
                    plugins=dependency.get("plugins"),
                    extras=dependency.get("extras"),
                )
                for dependency in data["poetry_dependencies"]
            ]
        )


def handle_output(issues, changes) -> None:
    """Handle the output."""
    if issues:
        for issue in issues:
            print(issue)
        sys.exit(1)

    if changes:
        for change in changes:
            print(f"Updated {change} successfully. ✅")
        print("Please verify the proposed changes and commit them! 📝")
        sys.exit(1)
    print("No changes required. 😎")


def get_update_command(poetry_dependencies: Dependency) -> str:
    """Get the update command."""
    issues = []
    cmd = "poetry add "
    for dependency in track(poetry_dependencies):
        click.echo(f"   Verifying:   {dependency.name}")
        raw = toml.load("pyproject.toml")["tool"]["poetry"]["dependencies"]

        current_version = str(raw[dependency.name])
        expected_version = f"=={dependency.get_latest_version()[1:]}"
        if current_version.find(expected_version) == -1:
            issues.append(
                f"Update the poetry version of {dependency.name} from `{current_version}` to `{expected_version}`\n"
            )
            if dependency.extras is not None:
                extras = ",".join(dependency.extras)
                cmd += f"{dependency.name}[{extras}]@=={expected_version} "
            else:
                cmd += f"{dependency.name}@{expected_version} "
            if dependency.plugins:
                for plugin in dependency.plugins:
                    cmd += f"{plugin}@{expected_version} "
    return cmd, issues


@deps.command()
@click.option(
    "--auto-approve",
    default=False,
    help="Auto approve the changes.",
    is_flag=True,
)
@click.pass_context
def verify(
    ctx: click.Context,
    auto_approve: bool = False,
) -> None:
    """Verify the packages.json file.

    Requires GITHUB_TOKEN env variable to be set.

    Example usage:
        adev deps verify
    """

    if not os.getenv("GITHUB_TOKEN"):
        ctx.obj["LOGGER"].error("Error: GITHUB_TOKEN environment variable is not set.")
        ctx.obj["LOGGER"].error("Please set it with: export GITHUB_TOKEN=<your_token>")
        ctx.obj["LOGGER"].error("You can generate a token at: https://github.com/settings/tokens")
        sys.exit(1)

    ctx.obj["LOGGER"].info("Verifying the dependencies against the version set specified. 📝")
    issues = []
    changes = []
    click.echo("Verifying autonomy dependencies... 📝")

    version_set_loader = VersionSetLoader()
    version_set_loader.load_config()
    if (Path("packages") / "packages.json").exists():
        version_set_loader.load_config()
        for dependency in track(version_set_loader.autonomy_dependencies.upstream_dependency):
            click.echo(f"   Verifying:   {dependency.name}")
            remote_packages = dependency.get_all_autonomy_packages()
            local_packages = get_package_json(Path())["third_party"]
            diffs = {}
            for package_name, package_hash in remote_packages.items():
                if package_name in local_packages:
                    if package_hash != local_packages[package_name]:
                        diffs[package_name] = package_hash

            if diffs:
                print_json(data=diffs)
                if not auto_approve:
                    click.confirm("Do you want to update the package?\n", abort=True)
                update_package_json(repo=Path(), proposed_dependency_updates=diffs)
                remove_old_package(repo=Path(), proposed_dependency_updates=diffs)
                changes.append(dependency.name)

    click.echo("Verifying poetry dependencies... 📝")
    cmd, poetry_issues = get_update_command(version_set_loader.poetry_dependencies.poetry_dependencies)
    issues.extend(poetry_issues)

    if issues:
        click.echo(f"Please run the following command to update the poetry dependencies.")
        click.echo(f"{cmd}\n")
        if not auto_approve:
            click.confirm("Do you want to update the poetry dependencies now?", abort=True)
        os.system(cmd)  # noqa
        changes.append("poetry dependencies")

    handle_output(issues, changes)


if __name__ == "__main__":
    cli()  # pylint: disable=no-value-for-parameter
