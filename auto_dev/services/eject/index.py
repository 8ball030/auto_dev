# ruff: noqa: PLR1702
"""Service functions for the eject command."""

import shutil
from copy import deepcopy
from typing import cast
from pathlib import Path
from dataclasses import field, dataclass

from rich.table import Table
from rich.console import Console
from aea.cli.eject import (
    IPFSHashOnly,
    ItemRemoveHelper,
    is_item_present,
    reachable_nodes,
    fingerprint_item,
    get_package_path,
    update_references,
    update_item_config,
    copy_package_directory,
    find_topological_order,
    replace_all_import_statements,
    update_item_public_id_in_init,
    get_latest_component_id_from_prefix,
)
from aea.cli.utils.context import Context
from aea.configurations.base import (
    PublicId,
    PackageId,
    ComponentId,
    PackageType,
    ComponentType,
)
from aea.configurations.constants import DEFAULT_VERSION, ITEM_TYPE_TO_PLURAL, DEFAULT_AEA_CONFIG_FILE

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
        self._ejected_components: dict[PackageId, PackageId] = {}

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
        self.agent_runner = DevAgentRunner(
            agent_name=self.config.public_id,
            verbose=True,
            force=False,
            logger=self.logger,
            fetch=False,
        )

        if not self.agent_runner.is_in_agent_dir():
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
        return self._ejected_components

    def update_all_references(self, ejected_components: dict[PackageId, PackageId]) -> None:
        """We need to update all references in the agent to the new components."""
        # We use a find and replace to update all references in the agent to the new name.
        for package_id, new_package_id in ejected_components.items():
            self.update_python_files(package_id, new_package_id, ejected_components)

            self.update_yaml_files(package_id, new_package_id, ejected_components)

        agent_config, *overrides = load_autonolas_yaml(PackageType.AGENT)
        agent_config["author"] = self.config.fork_id.author

        for package_id, new_package_id in ejected_components.items():
            agent_config = self.update_agent_config(agent_config, package_id, new_package_id)

        new_overrides = []
        for override in overrides:
            override_package_id = PackageId(
                public_id=PublicId.from_str(override.get("public_id")), package_type=PackageType(override.get("type"))
            )
            for package_id, new_package_id in ejected_components.items():
                if all(
                    [
                        override_package_id.package_type == package_id.package_type,
                        override.get("public_id").startswith(str(package_id.public_id)),
                    ]
                ):
                    override["public_id"] = str(new_package_id.public_id)
                    break

            # connection specific logic
            if (
                override_package_id.package_type == PackageType.CONNECTION
                and override.get("config")
                and override.get("config").get("target_skill_id")
            ):
                target_skill_id = PublicId.from_str(
                    override.get("config").get("target_skill_id"),
                )
                target_skill_id = PublicId(
                    author=target_skill_id.author,
                    name=target_skill_id.name,
                    version="latest",
                )
                filtered_ejected_components = {
                    k.public_id: v for k, v in ejected_components.items() if k.package_type == PackageType.SKILL
                }

                if target_skill_id in filtered_ejected_components:
                    package_id = filtered_ejected_components[target_skill_id]
                    override["config"]["target_skill_id"] = str(package_id.public_id)

            new_overrides.append(override)

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
        replacements = []
        old_dotted_path = (
            f"packages.{package_id.public_id.author}.{package_id.package_type.value}s.{package_id.public_id.name}"
        )
        new_dotted_path = f"packages.{new_package_id.public_id.author}.{new_package_id.package_type.value}s.{new_package_id.public_id.name}"  # noqa: E501
        replacements.append((old_dotted_path, new_dotted_path))

        old_str_public_id = str(package_id.public_id).replace("latest", DEFAULT_VERSION)
        new_str_public_id = str(new_package_id.public_id).replace("latest", DEFAULT_VERSION)
        replacements.append((old_str_public_id, new_str_public_id))

        if package_id.package_type is PackageType.PROTOCOL:
            # mecessary due to the way the protocol is imported in the generated code
            old_name_camel = "".join(word.capitalize() for word in package_id.public_id.name.split("_")) + "Message"
            new_name_camel = "".join(word.capitalize() for word in new_package_id.public_id.name.split("_")) + "Message"
            replacements.append((old_name_camel, new_name_camel))

        for dependent_package_id in ejected_components.values():
            directory = Path.cwd() / ITEM_TYPE_TO_PLURAL[dependent_package_id.package_type.value]
            for python_file in directory.rglob("*.py"):
                file_data = python_file.read_text()
                for old, new in replacements:
                    file_data = file_data.replace(old, new)
                python_file.write_text(file_data, encoding=DEFAULT_ENCODING)

    def update_yaml_files(self, package_id: PackageId, new_package_id: PackageId, ejected_components) -> None:
        """We search for all yaml files in the agent and update the references to the new package id."""

        old_str_public_id = str(package_id.public_id)
        new_str_public_id = str(new_package_id.public_id)
        plural_package_type = ITEM_TYPE_TO_PLURAL[package_id.package_type.value]

        directory = Path.cwd() / ITEM_TYPE_TO_PLURAL[package_id.package_type.value] / new_package_id.public_id.name
        for yaml_file in directory.glob("*.yaml"):
            component_config = load_autonolas_yaml(package_id.package_type.value, yaml_file.parent)[0]
            component_config["author"] = new_package_id.public_id.author
            component_config["name"] = new_package_id.public_id.name

            if package_id.package_type is PackageType.PROTOCOL:
                component_config["protocol_specification_id"] = new_str_public_id

            write_to_file(yaml_file, component_config, file_type=FileType.YAML)

        for dependent_package_id in ejected_components.values():
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

    def _run_eject_command(self, component_id: PublicId, component_type: str) -> bool:  # noqa: PLR0914
        """Run the aea eject command."""
        ctx = Context(
            cwd=Path.cwd(),
            verbosity="info",
            registry_path=Path.cwd() / "vendor",
        )
        agent_loader = ctx.agent_loader
        with open(DEFAULT_AEA_CONFIG_FILE, encoding="utf-8") as f:
            config = agent_loader.load(f)
        ctx.agent_config = config

        item_type = component_type
        public_id = component_id
        item_type_plural = item_type + "s"

        cwd = Path.cwd()
        if not is_item_present(
            cwd,
            config,
            item_type,
            public_id,
            is_vendor=True,
            with_version=True,
        ):  # pragma: no cover
            msg = f"{item_type.title()} {public_id} not found in agent's vendor items."
            raise UserInputError(msg)

        is_target = all(
            [
                public_id.author == self.config.public_id.author,
                public_id.name == self.config.public_id.name,
            ]
        )
        new_public_id = PublicId(
            self.config.fork_id.author, self.config.fork_id.name if is_target else public_id.name, DEFAULT_VERSION
        )

        self._ejected_components[PackageId(PackageType(item_type), public_id)] = PackageId(
            PackageType(item_type), new_public_id
        )

        src = get_package_path(cwd, item_type, public_id)
        dst = get_package_path(cwd, item_type, new_public_id, is_vendor=False)

        if is_item_present(cwd, config, item_type, public_id, is_vendor=False):  # pragma: no cover
            msg = f"{item_type.title()} {public_id} is already a non-vendor package."
            raise UserInputError(msg)

        component_prefix = ComponentType(item_type), public_id.author, public_id.name
        component_id = get_latest_component_id_from_prefix(config, component_prefix)
        public_id = cast(ComponentId, component_id).public_id

        package_id = PackageId(PackageType(item_type), public_id)

        self.logger.info(f"Ejecting item {package_id.package_type.value} {package_id.public_id!s}")
        self.logger.info(f"Destination: {dst}")
        self.logger.info(f"New public id: {new_public_id}")

        # first, eject all the vendor packages that depend on this
        item_remover = ItemRemoveHelper(ctx, ignore_non_vendor=True)
        reverse_dependencies = item_remover.get_agent_dependencies_with_reverse_dependencies()
        reverse_reachable_dependencies = reachable_nodes(reverse_dependencies, {package_id.without_hash()})
        eject_order = list(reversed(find_topological_order(reverse_reachable_dependencies)))
        eject_order.remove(package_id)
        if len(eject_order) > 0:
            self.logger.info(f"The following vendor packages will be ejected: {eject_order}")

        for dependency_package_id in eject_order:
            self._run_eject_command(
                dependency_package_id.public_id,
                dependency_package_id.package_type.value,
            )

        ctx.clean_paths.append(dst)
        copy_package_directory(Path(src), dst)

        item_config_update = {
            "author": new_public_id.author,
            "version": new_public_id.version,
        }

        update_item_config(item_type, Path(dst), None, **item_config_update)
        update_item_public_id_in_init(item_type, Path(dst), new_public_id)
        shutil.rmtree(src)

        replace_all_import_statements(Path(ctx.cwd), ComponentType(item_type), public_id, new_public_id)
        fingerprint_item(ctx, item_type, new_public_id)
        package_hash = IPFSHashOnly.hash_directory(dst)
        public_id_with_hash = PublicId(new_public_id.author, new_public_id.name, new_public_id.version, package_hash)

        # update references in all the other packages
        component_type = ComponentType(item_type_plural[:-1])
        old_component_id = ComponentId(component_type, public_id)
        new_component_id = ComponentId(component_type, public_id_with_hash)
        update_references(ctx, {old_component_id: new_component_id})
