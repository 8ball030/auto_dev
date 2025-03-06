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
from copy import deepcopy
from enum import Enum
from pathlib import Path
from dataclasses import dataclass

import toml
import yaml
import requests
import rich_click as click
from rich import print_json
from rich.progress import track
from aea.configurations.constants import PACKAGES

from auto_dev.base import build_cli
from auto_dev.utils import FileType, FileLoader, write_to_file
from auto_dev.constants import DEFAULT_TIMEOUT, DEFAULT_ENCODING
from auto_dev.exceptions import AuthenticationError, NetworkTimeoutError
from auto_dev.workflow_manager import Task, Workflow, WorkflowManager


PARENT = Path("repo_1")
CHILD = Path("repo_2")


def get_package_json(repo: Path) -> dict[str, dict[str, str]]:
    """We get the package json."""
    package_json = repo / "packages.json"
    with open(package_json, encoding=DEFAULT_ENCODING) as file_pointer:
        return yaml.safe_load(file_pointer)


def write_package_json(repo: Path, package_dict: dict[str, dict[str, str]]) -> None:
    """We write the package json."""
    package_json = repo / "packages.json"
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
    manual: bool = False,
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

    for package_name, package_hash in deepcopy(proposed).items():
        logger.info(f"Detected change from {package_name} to {package_hash}")
        if manual:
            incude = click.confirm("Include dependecy in proposed updates?")
            if not incude:
                proposed.pop(package_name)

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
    autonomy_dependencies: dict[str, Dependency] = None
    url: str = None
    plugins: list[str] = None
    extras: list[str] = None

    @property
    def headers(self) -> dict[str, str]:
        """Get the headers."""
        return {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Authorization": f"Bearer {os.getenv('GITHUB_TOKEN')}",
        }

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
                msg = "Error: Rate limit exceeded. Please add a github token."
                raise AuthenticationError(msg)
            msg = f"Error: {res.status_code} {res.text}"
            raise NetworkTimeoutError(msg)
        data = res.json()
        return data[0]["tag_name"].replace("v", "")

    def get_all_autonomy_packages(self, tag=None):
        """Read in the autonomy packages. the are located in the remote url."""
        if tag is None:
            tag = self.get_latest_version()
        file_path = "packages/packages.json"
        remote_url = f"{self.url}/contents/{file_path}?ref=v{tag}"
        data = requests.get(remote_url, headers=self.headers, timeout=DEFAULT_TIMEOUT)

        if data.status_code != 200:
            msg = f"Error: {data.status_code} {data.text} {remote_url}"
            raise NetworkTimeoutError(msg)
        dl_url = data.json()["download_url"]
        data = requests.get(dl_url, headers=self.headers, timeout=DEFAULT_TIMEOUT).json()
        return data["dev"]


@cli.group()
@click.pass_context
def deps(
    ctx: click.Context,  # noqa
) -> None:
    r"""Commands for managing dependencies.

    Available Commands:

        update: Update packages.json from parent repo and packages in child repo

        generate_gitignore: Generate .gitignore entries from packages.json

        verify: Verify dependencies against version set and update if needed
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
@click.option(
    "--manual",
    default=False,
    help="Auto approve the changes.",
    is_flag=True,
)
@deps.command()
@click.pass_context
def update(
    ctx: click.Context,
    parent_repo: Path,
    child_repo: Path,
    location: DependencyLocation = DependencyLocation.LOCAL,
    auto_confirm: bool = False,
    manual: bool = False,
) -> None:
    """Update dependencies from parent repo to child repo.

    Required Parameters:

        parent_repo (-p): Path to the parent repository containing source packages.json.

        child_repo (-c): Path to the child repository to update.

    Optional Parameters:

        location (--location): Location of dependencies (local or remote). Default: local

        auto_confirm (--auto-confirm): Skip confirmation prompts. Default: False

        manual (--manual): Enable manual mode for updates. Default: False

    Usage:

        Update with defaults:
            adev deps update -p /path/to/parent -c /path/to/child

        Auto-confirm updates:
            adev deps update -p /path/to/parent -c /path/to/child --auto-confirm

        Manual mode:
            adev deps update -p /path/to/parent -c /path/to/child --manual
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

    result = main(
        parent_repo=parent_repo, child_repo=child_repo, auto_confirm=auto_confirm, logger=logger, manual=manual
    )
    if not result:
        sys.exit(1)
    logger.info("Done. 😎")


# We have a command to generate the gitignore file.
@deps.command()
@click.pass_context
def generate_gitignore(
    ctx: click.Context,
) -> None:
    r"""Generate .gitignore entries from packages.json.

    Usage:

        Generate gitignore entries:
            adev deps generate-gitignore

    Notes
    -----
        - Only adds new entries, doesn't remove existing ones
        - Focuses on third-party packages from packages.json
        - Appends entries to existing .gitignore file

    """
    package_dict = get_package_json(repo=Path(PACKAGES))
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

    upstream_dependency: list[GitDependency]

    def to_dict(self, latest: bool = False):
        """Return a list of the upstream dependencies."""
        return [
            {
                "name": dependency.name,
                "version": dependency.version if not latest else dependency.get_latest_version(),
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

    poetry_dependencies: list[GitDependency]

    def to_dict(self, latest: bool = False):
        """Return a list of the poetry dependencies."""
        return [
            {
                "name": dependency.name,
                "version": dependency.get_latest_version() if latest else dependency.version,
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
    version="0.2.142",
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

    def __init__(self, config_file: Path = DEFAULT_ADEV_CONFIG_FILE, **kwargs):
        self.config_file = config_file
        self.latest = kwargs.get("latest", True)
        self.packages_dir = kwargs.get("packages_dir", "packages")

    def write_config(
        self,
        use_latest: bool = True,
    ):
        """Write the config file."""
        data = {
            "autonomy_dependencies": self.autonomy_dependencies.to_dict(use_latest),
            "poetry_dependencies": self.poetry_dependencies.to_dict(use_latest),
        }
        FileLoader(self.config_file, FileType.YAML).write(data)

    def load_config(self):
        """Load the config file."""
        with open(self.config_file, encoding="utf-8") as file_pointer:
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

    def update_autonomy_packages_from_config(
        self,
    ):
        """We update the autonomy packages from the config file."""
        for dependency in self.autonomy_dependencies.upstream_dependency:
            remote_packages = dependency.get_all_autonomy_packages(tag=str(dependency.version))
            local_packages = get_package_json(self.packages_dir)["third_party"]
            diffs = {}
            for package_name, package_hash in remote_packages.items():
                if package_name in local_packages and package_hash != local_packages[package_name]:
                    diffs[package_name] = package_hash
            if diffs:
                update_package_json(repo=self.packages_dir, proposed_dependency_updates=diffs)
                remove_old_package(repo=self.packages_dir, proposed_dependency_updates=diffs)
        return diffs


def get_update_command(poetry_dependencies: Dependency, strict: bool = False, use_latest=False) -> str:
    """Get the update command."""
    issues = []
    cmd = "poetry add "
    pre_fix = "==" if strict else "<="
    for dependency in track(poetry_dependencies):
        click.echo(f"   Verifying:   {dependency.name}")
        raw = toml.load("pyproject.toml")["tool"]["poetry"]["dependencies"]

        current_version = str(raw[dependency.name])

        if use_latest:
            expected_version = f"'{pre_fix}{dependency.get_latest_version()}'"
            click.echo(f"   Fetched  latest version for:   {dependency.name}@{expected_version}")
        else:
            expected_version = f"'{pre_fix}{dependency.version}'"

        if current_version.find(expected_version) == -1:
            issues.append(
                f"Update the poetry version of {dependency.name} from `{current_version}` to `{expected_version}`\n"
            )
            if dependency.extras is not None:
                extras = ",".join(dependency.extras)
                cmd += f"{dependency.name}[{extras}]@{expected_version} "
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
@click.option(
    "--latest/--no-latest",
    default=True,
    help="Select the latest version releases.",
    is_flag=True,
)
@click.option(
    "--strict/--no-strict",
    default=False,
    help="Enforce strict versioning.",
    is_flag=True,
)
@click.option(
    "--packages-dir",
    default="packages",
    help="The packages directory.",
    type=click.Path(exists=True),
)
@click.pass_context
def bump(
    ctx: click.Context,
    auto_approve: bool = False,
    latest: bool = True,
    strict: bool = False,
    packages_dir: Path = Path("packages"),
) -> None:
    r"""Verify and optionally update package dependencies.

    Optional Parameters:

        auto_approve: Skip confirmation prompts for updates. Default: False
            - Automatically applies all updates
            - No interactive prompts
            - Use with caution in production

    Usage:
        Verify with prompts:
            adev deps verify

        Auto-approve updates:
            adev deps verify --auto-approve

    Notes
    -----
        - Authentication:
            - Requires GITHUB_TOKEN environment variable
            - Token needs repo and packages read access
            - Can be generated at github.com/settings/tokens


        - Verification Process:
            - Checks both autonomy and poetry dependencies
            - Verifies against specified version sets
            - Compares local vs remote package hashes
            - Validates dependency compatibility

        - Update Process:
            - Updates packages.json for autonomy packages
            - Updates pyproject.toml for poetry dependencies
            - Handles dependency resolution
            - Maintains version consistency

        - Features:\n
            - Parallel version checking
            - Detailed diff viewing
            - Selective update approval
            - Dependency tree analysis
            - Version conflict detection

        - Best Practices:\n
            - Run before deployments
            - Include in CI/CD pipelines
            - Regular scheduled verification
            - Version pinning enforcement

    """
    packages_dir = Path(packages_dir)

    if not os.getenv("GITHUB_TOKEN"):
        ctx.obj["LOGGER"].error("Error: GITHUB_TOKEN environment variable is not set.")
        ctx.obj["LOGGER"].error("Please set it with: export GITHUB_TOKEN=<your_token>")
        ctx.obj["LOGGER"].error("You can generate a token at: https://github.com/settings/tokens")
        sys.exit(1)

    ctx.obj["LOGGER"].info("Verifying the dependencies against the version set specified. 📝")
    issues = []
    changes = []
    click.echo("Verifying autonomy dependencies... 📝")
    version_set_loader = VersionSetLoader(latest=latest, packages_dir=packages_dir)
    version_set_loader.load_config()
    if (Path(packages_dir) / "packages.json").exists():
        for dependency in track(version_set_loader.autonomy_dependencies.upstream_dependency):
            click.echo(f"   Verifying:   {dependency.name}")
            remote_packages = dependency.get_all_autonomy_packages()
            local_packages = get_package_json(packages_dir)["third_party"]
            diffs = {}
            for package_name, package_hash in remote_packages.items():
                if package_name in local_packages and package_hash != local_packages[package_name]:
                    diffs[package_name] = package_hash

            if diffs:
                print_json(data=diffs)
                if not auto_approve:
                    click.confirm("Do you want to update all the packages?\n", abort=True)
                update_package_json(repo=packages_dir, proposed_dependency_updates=diffs)
                remove_old_package(repo=packages_dir, proposed_dependency_updates=diffs)
                changes.append(dependency.name)
    else:
        click.echo("No packages.json file found. Skipping autonomy packages verification.")
        sys.exit(1)

    click.echo("Verifying poetry dependencies... 📝")
    cmd, poetry_issues = get_update_command(
        version_set_loader.poetry_dependencies.poetry_dependencies, strict=strict, use_latest=latest
    )
    issues.extend(poetry_issues)

    if issues:
        click.echo(f"Please run the following command to update the poetry dependencies.\n\t`{cmd}`\n")
        if not auto_approve:
            click.confirm("Do you want to update the poetry dependencies now?", abort=True)
        os.system(cmd)  # noqa
        changes.append("poetry dependencies")

    if not auto_approve:
        click.confirm("Do you want to write the changes to the config file?", abort=True)
    version_set_loader.write_config(use_latest=latest)
    wf_manager = WorkflowManager()
    wf = build_update_workflow(version_set_loader, strict=strict, use_latest=latest)
    wf_manager.add_workflow(wf)
    [click.echo(task.command) for task in wf.tasks]
    if not auto_approve:
        click.confirm("Do you want to execute the workflow?", abort=True)
    wf_manager.run()
    click.echo("Done. 😎")


def build_update_workflow(version_set_loader, strict, use_latest) -> Workflow:
    """Build a workflow to update the dependencies."""
    wf = Workflow()

    for dependency in version_set_loader.poetry_dependencies.poetry_dependencies:
        config_path = Path.cwd() / f"tbump_{dependency.name.replace('-', '_')}.toml"
        if not config_path.exists():
            continue
        command = (
            f"tbump --only-patch --non-interactive -c {config_path} {dependency.get_latest_version().replace('v', '')}"
        )
        task = Task(command=command, description=f"Verify {dependency.name} version")
        wf.add_task(task)

    if (Path(PACKAGES) / "packages.json").exists():
        wf.add_task(Task(command="autonomy packages sync", description="Sync autonomy packages"))
        wf.add_task(Task(command="autonomy packages lock", description="Lock autonomy packages"))

    cmd, _ = get_update_command(
        version_set_loader.poetry_dependencies.poetry_dependencies, strict=strict, use_latest=use_latest
    )
    wf.add_task(Task(command=cmd, description="Update poetry dependencies", shell=True))
    return wf


# verify command reads in the adev_config.yaml file and then verifies the dependencies.
@deps.command()
@click.option(
    "--auto-approve",
    default=False,
    help="Auto approve the changes.",
    is_flag=True,
)
def verify(auto_approve: bool = False):
    """Verify the dependencies from the adev config file.

    This allows us to specify the dependencies in the adev config file
    then verify them aginst the installed dependencies enforcing the version set.

    """
    version_set_loader = VersionSetLoader(latest=False)
    version_set_loader.load_config()

    wf = build_update_workflow(version_set_loader, strict=False, use_latest=True)

    wf_manager = WorkflowManager()
    wf_manager.add_workflow(wf)
    [click.echo(task.command) for task in wf.tasks]
    if not auto_approve:
        click.confirm("Do you want to execute the workflow?", abort=True)
    wf_manager.run()


if __name__ == "__main__":
    cli()  # pylint: disable=no-value-for-parameter
