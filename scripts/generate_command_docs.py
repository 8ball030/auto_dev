"""Script to generate command documentation.

This module handles the automatic generation of documentation for all CLI commands
in the auto_dev project. It uses introspection to discover commands and their
subcommands, then generates markdown documentation with proper formatting.
"""

import logging
from pathlib import Path
from importlib import import_module
from dataclasses import dataclass

import yaml
import click

from auto_dev.utils import FileType, write_to_file
from auto_dev.constants import DEFAULT_ENCODING


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def discover_commands() -> list[str]:
    """Discover all available commands by scanning the commands directory.

    Returns
    -------
        List of command names (without .py extension)

    """
    commands_dir = Path(__file__).parent.parent / "auto_dev" / "commands"
    commands = []

    for file_path in commands_dir.glob("*.py"):
        # Skip __init__.py and any other special files
        if file_path.stem.startswith("_"):
            continue
        logger.info(f"Discovered command: {file_path.stem}")
        commands.append(file_path.stem)

    return sorted(commands)


@dataclass
class DocTemplates:
    """Templates for documentation generation."""

    COMMAND = """# {command_name}

## Description
::: auto_dev.commands.{command_name}.{command_name}
    options:
      show_root_heading: false
      show_root_toc_entry: false
      members_order: source
      show_source: false
      show_signature: false
      show_signature_annotations: false
      show_object_full_path: false
      docstring_style: sphinx
      show_docstring_parameters: true
      show_docstring_returns: false
      show_docstring_raises: false
      show_docstring_examples: true
      docstring_section_style: list
      heading_level: 2
      heading_text: Description{subcommands_section}"""

    SUBCOMMAND = """

### {cmd_name}
::: auto_dev.commands.{command_name}.{subcommand_func}
    options:
      show_root_heading: false
      show_root_toc_entry: false
      members_order: source
      show_source: false
      show_signature: false
      show_signature_annotations: false
      show_object_full_path: false
      docstring_style: sphinx
      show_docstring_parameters: true
      show_docstring_returns: false
      show_docstring_raises: false
      show_docstring_examples: true
      docstring_section_style: list
      heading_level: 3
      heading_text: Description"""


class CommandDocGenerator:
    """Handles the generation of command documentation."""

    def __init__(self, docs_dir: Path):
        """Initialize the generator with output directory."""
        self.docs_dir = docs_dir
        self.templates = DocTemplates()

    def find_function_name(self, module, cmd_name: str) -> str | None:
        """Find the actual function name in the module for a given command name.

        Args:
        ----
            module: The imported module to search
            cmd_name: The command name to find

        Returns:
        -------
            The function name if found, None otherwise

        """
        for attr_name, attr_value in module.__dict__.items():
            if isinstance(attr_value, click.Command) and attr_value.name == cmd_name:
                return attr_name
        return None

    def get_subcommands(self, command_name: str) -> list[tuple[str, str]]:
        """Discover subcommands for a given command by inspecting its module.

        Args:
        ----
            command_name: Name of the command to inspect

        Returns:
        -------
            List of tuples containing (command_name, function_name)

        """
        try:
            module = import_module(f"auto_dev.commands.{command_name}")
        except ImportError as e:
            logger.warning(f"Could not import command module {command_name}: {e}")
            return []

        # Get the command group function
        group_func = getattr(module, command_name, None)
        if not group_func or not isinstance(group_func, click.Group):
            return []

        # Get commands directly from the Click group
        subcommands = []
        for cmd_name, cmd in group_func.commands.items():
            if not isinstance(cmd, click.Command) or isinstance(cmd, click.Group):
                continue

            func_name = self.find_function_name(module, cmd_name)
            if func_name:
                subcommands.append((cmd_name, func_name))

        return sorted(subcommands)

    def generate_command_doc(self, command: str) -> None:
        """Generate documentation for a single command.

        Args:
        ----
            command: Name of the command to document

        """
        doc_path = self.docs_dir / f"{command}.md"
        subcommands = self.get_subcommands(command)

        # Generate table of contents for subcommands
        toc_subcommands = ""
        subcommands_section = ""

        if subcommands:
            toc_subcommands = "- [Subcommands](#subcommands)\n"
            for cmd_name, _ in subcommands:
                toc_subcommands += f"  - [{cmd_name}](#{cmd_name.lower()})\n"

            # Generate subcommand documentation
            subcommands_text = ""
            for cmd_name, func_name in subcommands:
                subcommands_text += self.templates.SUBCOMMAND.format(
                    command_name=command, cmd_name=cmd_name, subcommand_func=func_name
                )
            subcommands_section = f"\n\n## Subcommands{subcommands_text}"

        try:
            doc_path.write_text(
                self.templates.COMMAND.format(
                    command_name=command, toc_subcommands=toc_subcommands, subcommands_section=subcommands_section
                ),
                encoding="utf-8",
            )
        except OSError as e:
            logger.exception(f"Failed to write documentation for {command}: {e}")


def update_mkdocs_nav(commands: list[str]) -> None:
    """Update the mkdocs.yml navigation to include all commands."""
    mkdocs_path = Path("mkdocs.yml")
    try:
        config = yaml.safe_load(mkdocs_path.read_text(encoding=DEFAULT_ENCODING))
    except OSError as e:
        logger.exception(f"Failed to read mkdocs.yml: {e}")
        return

    # Ensure config is a dictionary
    if config is None:
        config = {}

    # Ensure nav exists
    if "nav" not in config:
        config["nav"] = []

    # Find the Commands section in nav
    for item in config["nav"]:
        if isinstance(item, dict) and "Commands" in item:
            # Create new commands structure
            commands_nav = {"Commands": [{cmd: f"commands/{cmd}.md"} for cmd in sorted(commands)]}
            config["nav"][config["nav"].index(item)] = commands_nav
            break
    else:
        # If Commands section doesn't exist, add it
        commands_nav = {"Commands": [{cmd: f"commands/{cmd}.md"} for cmd in sorted(commands)]}
        config["nav"].append(commands_nav)

    try:
        write_to_file(mkdocs_path, config, FileType.YAML)
        logger.info("Updated mkdocs.yml navigation")
    except OSError as e:
        logger.exception(f"Failed to write mkdocs.yml: {e}")


def generate_docs() -> None:
    """Generate documentation for all commands."""
    # Setup directory paths
    docs_dir = Path("docs")
    commands_dir = docs_dir / "commands"

    # Create commands directory if it doesn't exist
    try:
        commands_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Ensured commands directory exists: {commands_dir}")
    except OSError as e:
        logger.exception(f"Failed to create directory {commands_dir}: {e}")
        return

    # Generate documentation
    generator = CommandDocGenerator(commands_dir)
    commands = discover_commands()
    logger.info(f"Discovered {len(commands)} commands: {', '.join(commands)}")

    for command in commands:
        try:
            generator.generate_command_doc(command)
            logger.info(f"Generated documentation for {command}")
        except Exception as e:
            logger.exception(f"Failed to generate documentation for {command}: {e}")

    # Update mkdocs.yml with discovered commands
    update_mkdocs_nav(commands)

    logger.info("Documentation generation complete!")


def on_config(config):
    """MkDocs hook to generate command documentation when building docs."""
    generate_docs()
    return config


if __name__ == "__main__":
    generate_docs()
