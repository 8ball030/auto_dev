"""MkDocs hooks for documentation generation."""

import re
import shutil
from typing import Any
from pathlib import Path

from mkdocs.config import Config
from mkdocs.structure.files import Files


def _clean_temp_files() -> None:
    """Clean temporary files."""
    temp_files = [
        "docs/api/auto_dev.md",
        "docs/api/fsm.md",
        "docs/api/handler.md",
        "docs/api/protocols.md",
        "docs/api/dao.md",
    ]
    for file in temp_files:
        path = Path(file)
        if path.exists():
            path.unlink()


def _copy_readme() -> None:
    """Copy README.md to docs/index.md."""
    readme_path = Path("README.md")
    if not readme_path.exists():
        return
    shutil.copy("README.md", "docs/index.md")


def _process_api_docs() -> None:
    """Process API documentation files."""
    api_files = {
        "docs/api/auto_dev.md": (
            "# Auto Dev API\n\n::: auto_dev.commands.create\n::: auto_dev.commands.deps\n"
            "::: auto_dev.commands.fmt\n::: auto_dev.commands.improve\n::: auto_dev.commands.lint\n"
            "::: auto_dev.commands.metadata\n::: auto_dev.commands.publish\n::: auto_dev.commands.release\n"
            "::: auto_dev.commands.repo\n::: auto_dev.commands.run\n::: auto_dev.commands.scaffold\n"
            "::: auto_dev.commands.test\n"
        ),
        "docs/api/fsm.md": "# FSM API\n\n::: auto_dev.fsm.fsm\n",
        "docs/api/handler.md": "# Handler API\n\n::: auto_dev.handler.scaffolder\n",
        "docs/api/protocols.md": "# Protocols API\n\n::: auto_dev.protocols.scaffolder\n",
        "docs/api/dao.md": "# DAO API\n\n::: auto_dev.dao.scaffolder\n",
    }

    for file_path, content in api_files.items():
        Path(file_path).write_text(content, encoding="utf-8")


def _process_command_docs() -> None:
    """Process command documentation files."""
    command_files = Path("docs/commands").glob("*.md")
    for file in command_files:
        content = file.read_text()
        processed_content = re.sub(r"```\n\n```", "```", content)
        file.write_text(processed_content)


def on_config(config: Config, **_: Any) -> Config:
    """Process configuration before running builds."""
    _clean_temp_files()
    _copy_readme()
    _process_api_docs()
    _process_command_docs()
    return config


def on_files(files: Files, **_: Any) -> Files:
    """Process files before running builds."""
    return files
