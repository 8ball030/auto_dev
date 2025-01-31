"""Test documentation generation."""

from pathlib import Path


def test_check_documentation_and_suggest():
    """Check that all source files have documentation and suggest running make docs-generate if not."""
    # Get all Python files in the source directory
    source_dir = Path("auto_dev/commands")
    docs_dir = Path("docs")

    source_files = list(source_dir.glob("*.py"))

    source_files = [f for f in source_files if f.stem not in {"__init__", "__pycache__"}]

    # replace auto_dev/commands/* with docs/commands/*.md
    docs_files = [docs_dir / "commands" / f"{f.stem}.md" for f in source_files]
    # Check that each source file has a corresponding doc file
    for doc_file in docs_files:
        assert (
            doc_file.exists()
        ), f"Documentation missing for command {doc_file.stem}. Consider running 'make docs-generate'."
