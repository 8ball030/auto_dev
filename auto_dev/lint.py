"""Simple linting tooling for autonomy repos."""

from auto_dev.constants import DEFAULT_RUFF_CONFIG

from .cli_executor import CommandExecutor


def check_path(path: str, verbose: bool = False) -> bool:
    """Check the path for linting errors.
    :param path: The path to check.
    """
    command = CommandExecutor(
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
    # We now
    return command.execute(verbose=verbose)
