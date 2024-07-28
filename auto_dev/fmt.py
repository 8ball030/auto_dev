"""
Module to format the code.
"""

from multiprocessing import Pool

from rich.progress import track

from auto_dev.cli_executor import CommandExecutor
from auto_dev.utils import isolated_filesystem


class Formatter:
    """Formatter class to run the formatter."""

    def __init__(self, verbose):
        self.verbose = verbose

    def format(self, path, fix=True):
        """Format the path."""
        if not fix:
            with isolated_filesystem(True):
                result = self.format_path(path, verbose=self.verbose)
        else:
            result = self.format_path(path, verbose=self.verbose)
        return result

    def format_path(self, path, verbose=False):
        """Format the path."""

        results = all(
            [
                self.run_autoflake8(path, verbose=verbose),
                self.run_isort(path, verbose=verbose),
                self.run_black(path, verbose=verbose),
            ]
        )
        return results

    @staticmethod
    def run_black(path, verbose=False):
        """Run black on the path."""
        command = CommandExecutor(
            [
                "poetry",
                "run",
                "black",
                str(path),
            ]
        )
        result = command.execute(verbose=verbose)
        return result

    @staticmethod
    def run_isort(path, verbose=False):
        """Run isort on the path."""
        command = CommandExecutor(
            [
                "poetry",
                "run",
                "isort",
                str(path),
            ]
        )
        result = command.execute(verbose=verbose)
        return result

    @staticmethod
    def run_autoflake8(path, verbose=False):
        """Run autoflake8 on the path."""
        command = CommandExecutor(
            [
                "poetry",
                "run",
                "autoflake8",
                "--remove-unused-variables",
                "--in-place",
                "--recursive",
                str(path),
            ]
        )
        result = command.execute(verbose=verbose)
        return result


def single_thread_fmt(paths, verbose, logger):
    """Run the formatting in a single thread."""
    results = {}
    formatter = Formatter(verbose)
    for package in track(range(len(paths)), description="Formatting..."):
        path = paths[package]
        if verbose:
            logger.info(f"Formatting: {path}")
        result = formatter.format(path)
        results[package] = result
    return results


def multi_thread_fmt(paths, verbose, num_processes):
    """Run the formatting in multiple threads."""
    formatter = Formatter(verbose)
    with Pool(num_processes) as pool:
        results = pool.map(formatter.format, paths)
    return results
