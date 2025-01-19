"""Tests for the documentation."""

import os
from logging import getLogger
from pathlib import Path

import pytest

from auto_dev.utils import restore_directory
from auto_dev.constants import DEFAULT_ENCODING
from auto_dev.cli_executor import CommandExecutor


def extract_code_blocks(doc):
    """Extract the code blocks from the documentation."""
    with open(doc, encoding=DEFAULT_ENCODING) as file_path:
        lines = file_path.readlines()
    code_blocks = []
    code_block = []
    in_code_block = False
    for line in lines:
        if in_code_block:
            if line.startswith("```"):
                in_code_block = False
                code_blocks.append("".join(code_block))
                code_block = []
            else:
                cleaned_line = line.strip()
                code_block.append(cleaned_line)
        elif line.startswith("```bash"):
            in_code_block = True
    return code_blocks


# we test the documents works.

documentation = ["docs/fsm.md"]
logger = getLogger()


@pytest.mark.parametrize("doc", documentation)
def test_documentation(doc):
    """Test the documentation."""
    assert Path(doc).exists()


@pytest.mark.parametrize("doc", documentation)
def test_doc_code_execution(doc, test_filesystem):
    """Test the documentation."""

    assert test_filesystem

    commands = extract_code_blocks(doc)

    with restore_directory():
        for command in commands:
            logger.info(f'Executing command:\n""\n{command}\n""')
            if command.startswith("cd "):
                os.chdir(command.split(" ")[1])
            else:
                executor = CommandExecutor(command)
                assert executor.execute(
                    stream=True, shell=True, verbose=False
                ), f"Command failed: {command}: {executor.output}"
