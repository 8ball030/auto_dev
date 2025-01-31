"""Simple linting tooling for autonomy repos."""

from pathlib import Path

from auto_dev.constants import DEFAULT_RUFF_CONFIG

from .cli_executor import CommandExecutor


def check_path(path: str, verbose: bool = False) -> bool:
    """Check the path for linting errors.

    Args:
    ----
        path (str): The path to check for linting errors
        verbose (bool, optional): Whether to show verbose output. Defaults to False.

    Returns:
    -------
        bool: True if linting passed, False if there were errors

    Notes:
    -----
        Runs the following linters:
            - ruff: Fast Python linter with auto-fixes
            - pydoclint: Docstring style checker

        Configuration:
            - Uses default ruff config from constants
            - Enforces sphinx docstring style
            - Checks argument order and types
            - Requires return sections
            - Allows init docstrings
            - Skips raises checking

    """

    path_obj = Path(path)

    # If path doesn't exist, return True (consider it a pass)
    if not path_obj.exists():
        if verbose:
            pass
        return True

    ruff_command = CommandExecutor(
        [
            "poetry",
            "run",
            "ruff",
            "check",
            "--fix",
            "--unsafe-fixes",
            path,
            "--config",
            str(DEFAULT_RUFF_CONFIG),
        ]
    )

    ruff_result = ruff_command.execute(verbose=verbose)
    if not ruff_result:
        return False

    pydoclint_command = CommandExecutor(
        [
            "poetry",
            "run",
            "pydoclint",
            path,
            "--style=sphinx",
            "--check-arg-order=True",
            "--skip-checking-short-docstrings=True",
            "--check-return-types=True",
            "--check-yield-types=True",
            "--arg-type-hints-in-docstring=True",
            "--require-return-section-when-returning-nothing=True",
            "--allow-init-docstring=True",
            "--skip-checking-raises=True",
        ]
    )

    return pydoclint_command.execute(verbose=verbose)
