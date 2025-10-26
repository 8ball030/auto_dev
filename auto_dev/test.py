"""Module for testing the project."""

import sys
import os
from pathlib import Path
from multiprocessing import cpu_count
from importlib import invalidate_caches


import pytest


COVERAGE_COMMAND = f"""coverage report \
                    -m \
                    --omit='{Path('**') / 'tests' / '*.py'!s}' \
                    {Path() / '**' / '*.py'!s} > 'coverage-report.txt'
"""


def get_test_cpu_count() -> str:
    """Determine how many CPUs to use for pytest-xdist."""
    return str(cpu_count()) if os.getenv("CI") else "auto"


def test_path(
    path: str | list[str],
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
    extra_args = ["--cache-clear", 
                  "--disable-warnings", 
                  "--import-mode=importlib"
                  ]

    if verbose:
        extra_args.append("-v")

    if watch:
        extra_args.append("-w")

    if multiple:
        extra_args.extend(("-n", get_test_cpu_count()))

    args = [path, *extra_args]
    os.environ["PYTHONWARNINGS"] = "ignore"
    sys.path.insert(0, os.getcwd())
    print(f"Running tests with pytest args: {args}")
    result = pytest.main(args)
    return result == 0
