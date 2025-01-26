# ------------------------------------------------------------------------------
#
#   Copyright 2023-2024 Valory AG
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# ------------------------------------------------------------------------------
"""This script checks that the pipfile of the repository meets the requirements.

In particular:
- Avoid the usage of "*"

It is assumed the script is run from the repository root.
"""

import logging
import itertools
from typing import Any, Optional
from pathlib import Path
from collections import OrderedDict, OrderedDict as OrderedDictType
from collections.abc import Iterator

import toml
import click
from aea.package_manager.base import load_configuration
from aea.configurations.data_types import Dependency


ANY_SPECIFIER = "*"


class PathArgument(click.Path):
    """Path parameter for CLI."""

    def convert(self, value: Any, param: Optional[click.Parameter], ctx: Optional[click.Context]) -> Optional[Path]:
        """Convert path string to `pathlib.Path`."""
        path_string = super().convert(value, param, ctx)
        return None if path_string is None else Path(path_string)


class Pipfile:
    """Class to represent Pipfile config."""

    ignore = [
        "open-aea-flashbots",
        "open-aea-flashbots",
        "tomte",
    ]

    def __init__(
        self,
        sources: list[str],
        packages: OrderedDictType[str, Dependency],
        dev_packages: OrderedDictType[str, Dependency],
        file: Path,
    ) -> None:
        """Initialize object."""
        self.sources = sources
        self.packages = packages
        self.dev_packages = dev_packages
        self.file = file

    def __iter__(self) -> Iterator[Dependency]:
        """Iterate dependencies as from aea.configurations.data_types.Dependency object."""
        for name, dependency in itertools.chain(self.packages.items(), self.dev_packages.items()):
            if name.startswith("comment_") or name in self.ignore:
                continue
            yield dependency

    def update(self, dependency: Dependency) -> None:
        """Update dependency specifier."""
        if dependency.name in self.ignore:
            return
        if dependency.name in self.packages:
            if dependency.version == "":
                return
            self.packages[dependency.name] = dependency
        else:
            self.dev_packages[dependency.name] = dependency

    def check(self, dependency: Dependency) -> tuple[Optional[str], int]:
        """Check dependency specifier."""
        if dependency.name in self.ignore:
            return None, 0

        if dependency.name in self.packages:
            expected = self.packages[dependency.name]
            if expected != dependency:
                return (
                    f"in Pipfile {expected.get_pip_install_args()[0]}; " f"got {dependency.get_pip_install_args()[0]}"
                ), logging.WARNING
            return None, 0

        if dependency.name not in self.dev_packages:
            return f"{dependency.name} not found in Pipfile", logging.ERROR

        expected = self.dev_packages[dependency.name]
        if expected != dependency:
            return (
                f"in Pipfile {expected.get_pip_install_args()[0]}; " f"got {dependency.get_pip_install_args()[0]}"
            ), logging.WARNING

        return None, 0

    @classmethod
    def parse(cls, content: str) -> tuple[list[str], OrderedDictType[str, OrderedDictType[str, Dependency]]]:
        """Parse from string."""
        sources = []
        sections: OrderedDictType = OrderedDict()
        lines = list(content.split("\n"))
        comments = 0
        while len(lines) > 0:
            line = lines.pop(0)
            if "[[source]]" in line:
                source = line + "\n"
                while True:
                    line = lines.pop(0)
                    if line == "":
                        break
                    source += line + "\n"
                sources.append(source)
            if "[dev-packages]" in line or "[packages]" in line:
                section = line
                sections[section] = OrderedDict()
                while len(lines) > 0:
                    line = lines.pop(0).strip()
                    if line == "":
                        break
                    if line.startswith("#"):
                        sections[section][f"comment_{comments}"] = line
                        comments += 1
                    else:
                        dep = Dependency.from_pipfile_string(line)
                        sections[section][dep.name] = dep
        return sources, sections

    def compile(self) -> str:
        """Compile to Pipfile string."""
        content = ""
        for source in self.sources:
            content += source + "\n"

        content += "[packages]\n"
        for package, dep in self.packages.items():
            if package.startswith("comment"):
                content += str(dep) + "\n"
            else:
                content += dep.to_pipfile_string() + "\n"

        content += "\n[dev-packages]\n"
        for package, dep in self.dev_packages.items():
            if package.startswith("comment"):
                content += str(dep) + "\n"
            else:
                content += dep.to_pipfile_string() + "\n"
        return content

    @classmethod
    def load(cls, file: Path) -> "Pipfile":
        """Load from file."""
        sources, sections = cls.parse(
            content=file.read_text(encoding="utf-8"),
        )
        return cls(
            sources=sources,
            packages=sections.get("[packages]", OrderedDict()),
            dev_packages=sections.get("[dev-packages]", OrderedDict()),
            file=file,
        )

    def dump(self) -> None:
        """Write to Pipfile."""
        self.file.write_text(self.compile(), encoding="utf-8")


class PyProjectToml:
    """Class to represent pyproject.toml file."""

    ignore = [
        "python",
    ]

    def __init__(
        self,
        dependencies: OrderedDictType[str, Dependency],
        config: dict[str, dict],
        file: Path,
    ) -> None:
        """Initialize object."""
        self.dependencies = dependencies
        self.config = config
        self.file = file

    def __iter__(self) -> Iterator[Dependency]:
        """Iterate dependencies as from aea.configurations.data_types.Dependency object."""
        for dependency in self.dependencies.values():
            if dependency.name not in self.ignore:
                yield dependency

    def update(self, dependency: Dependency) -> None:
        """Update dependency specifier."""
        if dependency.name in self.ignore:
            return
        if dependency.name in self.dependencies and dependency.version == "":
            return
        self.dependencies[dependency.name] = dependency

    def check(self, dependency: Dependency) -> tuple[Optional[str], int]:
        """Check dependency specifier."""
        if dependency.name in self.ignore:
            return None, 0

        if dependency.name not in self.dependencies:
            return f"{dependency.name} not found in pyproject.toml", logging.ERROR

        expected = self.dependencies[dependency.name]
        if expected.name != dependency.name and expected.version != dependency.version:
            return (
                f"in pyproject.toml {expected.get_pip_install_args()[0]}; "
                f"got {dependency.get_pip_install_args()[0]}"
            ), logging.WARNING

        return None, 0

    @classmethod
    def load(cls, pyproject_path: Path) -> Optional["PyProjectToml"]:
        """Load pyproject.yaml dependencies."""
        config = toml.load(pyproject_path)
        dependencies = OrderedDict()
        try:
            config["tool"]["poetry"]["dependencies"]
        except KeyError:
            return None
        for name, version in config["tool"]["poetry"]["dependencies"].items():
            if isinstance(version, str):
                dependencies[name] = Dependency(
                    name=name,
                    version=version,
                )
            else:
                dependencies[name] = Dependency(
                    name=name,
                    version=version.get("version", ""),
                )
        return cls(
            dependencies=dependencies,
            config=config,
            file=pyproject_path,
        )

    def dump(self) -> None:
        """Write to pyproject.toml."""
        for name, dependency in self.dependencies.items():
            self.config["tool"]["poetry"]["dependencies"][name] = dependency.version
        toml.dump(self.config, self.file.open("w", encoding="utf-8"))


def load_packages_dependencies(packages_dir: Path) -> list[Dependency]:
    """Load packages dependencies."""
    return [
        dependency
        for package_path in packages_dir.glob("**/package.yaml")
        for dependency in load_configuration(package_path).dependencies
    ]


def _update(
    packages_dependencies: list[Dependency],
    pipfile: Optional[Pipfile] = None,
    pyproject: Optional[PyProjectToml] = None,
) -> None:
    """Update dependencies."""
    for dependency in packages_dependencies:
        if pipfile is not None:
            pipfile.update(dependency)
        if pyproject is not None:
            pyproject.update(dependency)


def _check(
    packages_dependencies: list[Dependency],
    pipfile: Optional[Pipfile] = None,
    pyproject: Optional[PyProjectToml] = None,
) -> None:
    """Check dependencies."""
    for dependency in packages_dependencies:
        if pipfile is not None:
            msg, level = pipfile.check(dependency)
            if msg is not None:
                logging.log(level, msg)
        if pyproject is not None:
            msg, level = pyproject.check(dependency)
            if msg is not None:
                logging.log(level, msg)


@click.command(name="dm")
@click.option(
    "--check",
    is_flag=True,
    help="Perform dependency checks.",
)
@click.option(
    "--packages",
    "packages_dir",
    type=PathArgument(
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    help="Path of the packages directory.",
)
@click.option(
    "--pipfile",
    "pipfile_path",
    type=PathArgument(
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    help="Pipfile path.",
)
@click.option(
    "--pyproject",
    "pyproject_path",
    type=PathArgument(
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    help="Pipfile path.",
)
def main(
    check: bool = False,
    packages_dir: Optional[Path] = None,
    pipfile_path: Optional[Path] = None,
    pyproject_path: Optional[Path] = None,
) -> None:
    """Run the script."""
    if packages_dir is None:
        packages_dir = Path("packages")
    if pipfile_path is None:
        pipfile_path = Path("Pipfile")
    if pyproject_path is None:
        pyproject_path = Path("pyproject.toml")

    packages_dependencies = load_packages_dependencies(packages_dir)
    pipfile = Pipfile.load(pipfile_path) if pipfile_path.exists() else None
    pyproject = PyProjectToml.load(pyproject_path) if pyproject_path.exists() else None

    if check:
        _check(packages_dependencies, pipfile, pyproject)
    else:
        _update(packages_dependencies, pipfile, pyproject)
        if pipfile is not None:
            pipfile.dump()
        if pyproject is not None:
            pyproject.dump()


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
