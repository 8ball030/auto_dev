# ruff: noqa: PLR1702
"""Service functions for the eject command."""

import shutil
from copy import deepcopy
from pathlib import Path
from dataclasses import field, dataclass

from rich.table import Table
from rich.console import Console
from aea.configurations.base import (
    PublicId,
    PackageId,
    PackageType,
)
from aea.configurations.constants import ITEM_TYPE_TO_PLURAL, DEFAULT_AEA_CONFIG_FILE

from auto_dev.utils import FileType, get_logger, write_to_file, load_autonolas_yaml
from auto_dev.constants import DEFAULT_ENCODING
from auto_dev.exceptions import UserInputError
from auto_dev.cli_executor import CommandExecutor
from auto_dev.services.runner import DevAgentRunner
from auto_dev.services.package_manager.index import PackageManager


@dataclass
class EjectConfig:
    """Configuration for ejection."""

    component_type: str
    public_id: PublicId
    fork_id: PublicId
    base_path: Path = field(default_factory=Path.cwd)
    skip_dependencies: bool = False


class ComponentEjector:
    """Class to handle component ejection."""

    def __init__(self, config: EjectConfig):
        """Initialize the ejector with configuration."""
        self.config = config
        self.executor = CommandExecutor([""])  # Placeholder, will be set per command
        self.logger = get_logger(__name__)
        self.package_manager = PackageManager(verbose=True)

    def eject(self, display=False) -> list[PublicId]:
        """Eject a component and all its dependencies recursively.

        Returns
        -------
            List of ejected component IDs

        Raises
        ------
            ValueError: If component ejection fails
            ConfigUpdateError: If configuration update fails
            OSError: If file operations fail

        """
        agent_runner = DevAgentRunner(
            agent_name=self.config.public_id,
            verbose=True,
            force=False,
            logger=self.logger,
            fetch=False,
        )

        if not agent_runner.is_in_agent_dir():
            self.logger.error("You must run the command from within an agent directory!.")
            msg = "You must run the command from within an agent directory!."
            raise UserInputError(msg)

        self._run_eject_command(self.config.public_id, self.config.component_type)

        ejected_components = self.get_ejected_components()
        self.logger.info(f"Total Ejected components: {len(ejected_components)}")

        self.update_all_references(ejected_components)

        if display:
            self.show_display(ejected_components)
        return ejected_components

    def get_ejected_components(self) -> dict[PackageId, PackageId]:
        """Search for ejected components in the current directory."""
        ejected_components = {}
        for item_type, plural in ITEM_TYPE_TO_PLURAL.items():
            component_pattern = f"{plural}/*"
            for item_dir in Path.cwd().glob(component_pattern):
                if not item_dir.is_dir():
                    continue
                component_config = load_autonolas_yaml(item_type, item_dir)[0]
                public_id = PublicId.from_json(component_config)
                package_id = PackageId(
                    public_id=public_id,
                    package_type=item_type,
                )
                new_package_id = PackageId(
                    public_id=PublicId(
                        name=public_id.name, author=self.config.fork_id.author, version=public_id.version
                    ),
                    package_type=item_type,
                )
                ejected_components[package_id] = new_package_id
        return ejected_components

    def update_all_references(self, ejected_components: dict[PackageId, PackageId]) -> None:
        """We need to update all references in the agent to the new components."""
        # We use a find and replace to update all references in the agent to the new name.
        for package_id, new_package_id in ejected_components.items():
            self.update_python_files(package_id, new_package_id, ejected_components)
            self.update_yaml_files(package_id, new_package_id, ejected_components)

        agent_config, *overides = load_autonolas_yaml(PackageType.AGENT)
        agent_config["author"] = self.config.fork_id.author

        for package_id, new_package_id in ejected_components.items():
            agent_config = self.update_agent_config(agent_config, package_id, new_package_id)

        # We now need to do a
        new_overrides = []
        for overide in overides:
            override_package_id = PackageId(
                public_id=PublicId.from_str(overide.get("public_id")), package_type=PackageType(overide.get("type"))
            )
            for package_id, new_package_id in ejected_components.items():
                if all(
                    [
                        override_package_id.package_type == package_id.package_type,
                        overide.get("public_id").startswith(str(package_id.public_id)),
                    ]
                ):
                    overide["public_id"] = str(new_package_id.public_id)
                    break

            # connection specific logic
            if (
                override_package_id.package_type == PackageType.CONNECTION
                and overide.get("config")
                and overide.get("config").get("target_skill_id")
            ):
                target_skill_id = PublicId.from_str(overide.get("config").get("target_skill_id"))
                filtered_ejected_components = {
                    k.public_id: v for k, v in ejected_components.items() if k.package_type == PackageType.SKILL
                }
                if target_skill_id in filtered_ejected_components:
                    overide["config"]["target_skill_id"] = str(target_skill_id)

            new_overrides.append(overide)

        write_to_file(Path.cwd() / DEFAULT_AEA_CONFIG_FILE, [agent_config, *new_overrides], file_type=FileType.YAML)

    def update_agent_config(self, agent_config: dict, package_id: PackageId, new_package_id: PackageId) -> dict:
        """Update the agent config with the new package id."""
        new_agent_config = deepcopy(agent_config)
        plural_package_type = ITEM_TYPE_TO_PLURAL[package_id.package_type.value]
        current_packages = new_agent_config.get(plural_package_type, [])
        for package in deepcopy(current_packages):
            existing_public_id = PublicId.from_str(package)
            if all(
                [
                    existing_public_id.author == package_id.public_id.author,
                    existing_public_id.name == package_id.public_id.name,
                ]
            ):
                new_public_id = PublicId(
                    author=new_package_id.public_id.author,
                    name=new_package_id.public_id.name,
                    version=existing_public_id.version,
                )
                current_packages.remove(package)
                current_packages.append(str(new_public_id))

        return new_agent_config

    def update_python_files(
        self, package_id: PackageId, new_package_id: PublicId, ejected_components: dict[PackageId, PackageId]
    ) -> None:
        """We search for all python files in the agent and update the references to the new package id."""
        old_dotted_path = (
            f"packages.{package_id.public_id.author}.{package_id.package_type.value}s.{package_id.public_id.name}"
        )
        new_dotted_path = f"packages.{new_package_id.public_id.author}.{new_package_id.package_type.value}s.{new_package_id.public_id.name}"  # noqa: E501

        old_str_public_id = str(package_id.public_id)
        new_str_public_id = str(new_package_id.public_id)

        for dependent_package_id in ejected_components:
            directory = Path.cwd() / ITEM_TYPE_TO_PLURAL[dependent_package_id.package_type.value]
            if not directory.exists():
                continue
            for python_file in directory.rglob("*.py"):
                file_data = python_file.read_text()
                new_file_data = file_data.replace(old_dotted_path, new_dotted_path)
                new_file_data = new_file_data.replace(old_str_public_id, new_str_public_id)
                python_file.write_text(new_file_data, encoding=DEFAULT_ENCODING)

    def update_yaml_files(self, package_id: PackageId, new_package_id: PackageId, ejected_components) -> None:
        """We search for all yaml files in the agent and update the references to the new package id."""
        directory = Path.cwd() / ITEM_TYPE_TO_PLURAL[package_id.package_type.value] / package_id.public_id.name

        old_str_public_id = str(package_id.public_id)
        new_str_public_id = str(new_package_id.public_id)
        plural_package_type = ITEM_TYPE_TO_PLURAL[package_id.package_type.value]

        for yaml_file in directory.glob("*.yaml"):
            component_config = load_autonolas_yaml(package_id.package_type.value, yaml_file.parent)[0]
            component_config["author"] = new_package_id.public_id.author
            component_config["name"] = new_package_id.public_id.name

            if package_id.package_type is PackageType.PROTOCOL:
                component_config["protocol_specification_id"] = new_str_public_id

            write_to_file(yaml_file, component_config, file_type=FileType.YAML)

        for dependent_package_id in ejected_components:
            dependent_package_type_plural = ITEM_TYPE_TO_PLURAL[dependent_package_id.package_type.value]
            dependent_config = load_autonolas_yaml(
                dependent_package_id.package_type.value,
                Path.cwd() / dependent_package_type_plural / dependent_package_id.public_id.name,
            )[0]
            current_packages_of_type = dependent_config.get(plural_package_type, [])
            if not current_packages_of_type:
                continue
            for package in deepcopy(current_packages_of_type):
                if package.startswith(old_str_public_id):
                    current_packages_of_type.remove(package)
                    current_packages_of_type.append(package.replace(old_str_public_id, new_str_public_id))
            dependent_config[plural_package_type] = current_packages_of_type
            write_to_file(
                Path.cwd()
                / dependent_package_type_plural
                / dependent_package_id.public_id.name
                / f"{dependent_package_id.package_type.value}.yaml",
                dependent_config,
                file_type=FileType.YAML,
            )

    def show_display(self, ejected_components: dict[PackageId, PackageId]) -> None:
        """Display the ejected components in a table."""
        table = Table(title="Ejected Components")
        table.add_column("Package ID", style="magenta")
        table.add_column("New Package ID", style="cyan")
        for package, new_package_id in ejected_components.items():
            table.add_row(str(package), str(new_package_id))
        console = Console()
        console.print(table)

    def run_command(self, command: str, shell: bool = False) -> tuple[bool, int]:
        """Run a command using the executor and return success and exit code."""
        self.executor.command = command if shell else command.split()
        success = self.executor.execute(verbose=False, shell=shell)
        return success, self.executor.return_code or 0

    def _run_eject_command(self, component_id: PublicId, component_type: str) -> bool:
        """Run the aea eject command."""
        if component_type == "custom":
            # For customs, just copy from vendor to customs directory
            vendor_path = Path.cwd() / "vendor" / component_id.author / "customs" / component_id.name
            customs_path = Path.cwd() / "customs" / component_id.name
            if vendor_path.exists() and not customs_path.exists():
                customs_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(vendor_path, customs_path)
            return True
        success, _ = self.run_command(
            f"yes | aea -s eject {component_type} {component_id.author}/{component_id.name}", shell=True
        )
        return success
