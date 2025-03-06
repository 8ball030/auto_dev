"""Test documentation generation."""

from pathlib import Path
from importlib import import_module

import click

from auto_dev.utils import read_from_file


def test_check_documentation_and_suggest():
    """Check that all source files and subcommands have documentation and suggest running make docs if not."""
    # Define the source and docs directories
    source_dir = Path("auto_dev/commands")
    docs_dir = Path("docs/commands")

    # Get all Python files in the source directory, excluding __init__ and __pycache__
    source_files = list(source_dir.glob("*.py"))
    source_files = [f for f in source_files if f.stem not in {"__init__", "__pycache__"}]

    # Check that each source file has a corresponding doc file, ex. adev run
    for source_file in source_files:
        doc_file = docs_dir / f"{source_file.stem}.md"
        assert doc_file.exists(), f"Documentation missing for command {source_file.stem}. Consider running 'make docs'."

        # Import the module and check for subcommands
        module_name = f"auto_dev.commands.{source_file.stem}"
        try:
            module = import_module(module_name)
        except ImportError as e:
            msg = f"Could not import module {module_name}: {e}"
            raise AssertionError(msg) from e

        # Get the command group function
        group_func = getattr(module, source_file.stem, None)
        if not group_func or not isinstance(group_func, click.Group):
            continue

        # Read the documentation file content
        doc_content = read_from_file(doc_file)

        # Get commands directly from the Click group
        for cmd_name, cmd in group_func.commands.items():
            if not isinstance(cmd, click.Command) or isinstance(cmd, click.Group):
                continue

            # Check for subcommand documentation within the same file, ex. adev run dev
            assert (
                f"### {cmd_name}" in doc_content
            ), f"Documentation missing for subcommand {cmd_name} in {source_file.stem}. Consider running 'make docs'."
