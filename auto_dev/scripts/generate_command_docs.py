"""Script to generate command documentation."""

from pathlib import Path


COMMANDS = [
    "run",
    "create",
    "lint",
    "publish",
    "test",
    "improve",
    "release",
    "metadata",
    "fmt",
    "scaffold",
    "deps",
    "convert",
    "repo",
    "fsm",
    "augment",
]

TEMPLATE = """# {command_title} Command

::: auto_dev.commands.{command_name}.{command_name}
    options:
      show_root_heading: false
      show_source: false
      show_signature: true
      show_signature_annotations: true
      docstring_style: sphinx
      show_docstring_parameters: true
      show_docstring_returns: false
      show_docstring_raises: false
      show_docstring_examples: true
      docstring_section_style: table
      docstring_options:
        heading_level: 2
        merge_init_into_class: false
        show_docstring_attributes: false
        show_docstring_description: true
        show_docstring_examples: true
        show_docstring_other_parameters: false
        show_docstring_parameters: true
        show_docstring_raises: false
        show_docstring_returns: false
        show_docstring_warns: false
        show_docstring_yields: false
        parameter_headings:
          required: "Required Parameters"
          optional: "Optional Parameters"
"""


def main():
    """Generate documentation for all commands."""
    # Get the package root directory
    package_root = Path(__file__).parent.parent.parent
    docs_dir = package_root / "docs" / "commands"
    docs_dir.mkdir(parents=True, exist_ok=True)

    for command in COMMANDS:
        doc_path = docs_dir / f"{command}.md"
        with open(doc_path, "w", encoding="utf-8") as f:
            f.write(TEMPLATE.format(command_title=command.title(), command_name=command))
