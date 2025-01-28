"""Test documentation generation."""

from pathlib import Path


def check_documentation_exists(source_files: list[Path], docs_dir: Path, file_type: str):
    """Check that documentation exists and is valid for given source files."""
    for source_file in source_files:
        doc_file = docs_dir / f"{source_file.stem}.md"
        assert doc_file.exists(), f"Documentation missing for {file_type} {source_file.stem}"

        # Check that the documentation file is not empty
        assert doc_file.stat().st_size > 0, f"Documentation is empty for {file_type} {source_file.stem}"

        # Read the doc file and check for basic content
        content = doc_file.read_text()
        assert "# " in content, f"Documentation lacks title for {file_type} {source_file.stem}"
        assert "## " in content, f"Documentation lacks sections for {file_type} {source_file.stem}"


def test_all_endpoints_documented(generated_docs):
    """Test that all command and API endpoints are documented."""
    # Get all Python files in the commands directory
    commands_dir = Path("auto_dev/commands")
    command_files = list(commands_dir.glob("*.py"))
    command_files = [f for f in command_files if f.stem not in {"__init__", "__pycache__"}]

    # Get all Python files in the API directory
    api_dir = Path("auto_dev/api")
    api_files = list(api_dir.glob("*.py"))
    api_files = [f for f in api_files if f.stem not in {"__init__", "__pycache__"}]

    # Check command documentation
    check_documentation_exists(command_files, generated_docs, "command")

    # Check API documentation
    check_documentation_exists(api_files, Path("docs/api"), "API endpoint")
