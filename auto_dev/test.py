"""
Module for testing the project.
"""
from auto_dev.cli_executor import CommandExecutor
from multiprocessing import cpu_count
from auto_dev.utils import isolated_filesystem


def test_path(
    path: str,
    verbose: bool = False,
    watch: bool = False,
) -> bool:
    """
    Check the path for linting errors.
    :param path: The path to check
    """
    available_cores = cpu_count()
    with isolated_filesystem(True):
        command = CommandExecutor(
            [
                "poetry",
                "run",
                "pytest",
                str(path),
                "-vv",
                "-n",
                str(available_cores),
            ]
            + (["-ff"] if watch else [])
        )
        result = command.execute(verbose=verbose, stream=True)
    return result
