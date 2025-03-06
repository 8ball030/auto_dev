"""Module for testing the project."""

import os
from pathlib import Path
from multiprocessing import cpu_count

import pytest


COVERAGE_COMMAND = f"""coverage report \
                    -m \
                    --omit='{Path('**') / 'tests' / '*.py'!s}' \
                    {Path() / '**' / '*.py'!s} > 'coverage-report.txt'
"""


def test_path(
    path: str,
    verbose: bool = False,
    watch: bool = False,
    multiple: bool = False,
) -> bool:
    """Run tests for a specified path.

    Args:
    ----
        path (str): The path to run tests on
        verbose (bool, optional): Whether to show verbose output. Defaults to False
        watch (bool, optional): Whether to watch for file changes and rerun tests. Defaults to False
        multiple (bool, optional): Whether to run tests in parallel. Defaults to False

    Returns:
    -------
        bool: True if all tests passed, False if any tests failed

    Notes:
    -----
        Features:
            - Supports pytest test discovery
            - File watching for TDD workflow
            - Parallel test execution
            - Verbose output option

        Configuration:
            - Uses pytest as test runner
            - Automatically detects CPU count for parallel runs
            - Supports pytest command line arguments
            - Integrates with coverage reporting

    """
    extra_args = ["--cache-clear"]

    if verbose:
        extra_args.append("-v")

    if watch:
        extra_args.append("-w")

    if multiple:
        extra_args.extend(("-n", str(cpu_count())))

    args = [path, *extra_args]
    os.environ["PYTHONPATH"] = "."
    os.environ["PYTHONWARNINGS"] = "ignore"
    result = pytest.main(args)
    return result == 0
