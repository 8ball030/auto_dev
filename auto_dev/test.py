"""Module for testing the project."""

from pathlib import Path
from multiprocessing import cpu_count

import pytest


COVERAGE_COMMAND = f"""coverage report \
                    -m \
                    --omit='{str(Path('**') / 'tests' / '*.py')}' \
                    {str(Path() / '**' / '*.py')} > 'coverage-report.txt'
"""


def test_path(
    path: str,
    verbose: bool = False,
    watch: bool = False,
    multiple: bool = False,
) -> bool:
    """Check the path for linting errors.
    :param path: The path to check.
    """
    extra_args = []

    if verbose:
        extra_args.append("-v")

    if watch:
        extra_args.append("-w")

    if multiple:
        extra_args.append("-n")
        extra_args.append(str(cpu_count()))

    args = [path] + extra_args
    res = pytest.main(args)
    return bool(res == 0)
