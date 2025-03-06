"""Module to format the code."""

from pathlib import Path
from multiprocessing import Pool

import requests
from rich.progress import track

from auto_dev.constants import DEFAULT_ENCODING, DEFAULT_RUFF_CONFIG
from auto_dev.cli_executor import CommandExecutor


class Formatter:
    """Formatter class to run the formatter."""

    def __init__(self, verbose, remote):
        self.verbose = verbose
        self.remote = remote

    def format(self, path):
        """Format the path."""
        if not Path(path).exists():
            return True
        func = self._format_path if not self.remote else self._remote_format_path
        return func(path, verbose=self.verbose)

    def _remote_format_path(self, path, verbose=False):
        """Format the path."""
        # pylint: disable=R1732
        with requests.Session() as session, open(path, encoding=DEFAULT_ENCODING) as file:
            data = file.read()
            result = session.post(
                "http://localhost:26659/format",
                data=data.encode(DEFAULT_ENCODING),
                timeout=150,
            )
        if verbose:
            pass

        if result.json():
            if "new_data" in result.json():
                with open(path, "w", encoding=DEFAULT_ENCODING) as file:
                    file.write(result.json()["new_data"])
                return True
            if "result" in result.json():
                return result.json()["result"]

        return False

    def _format_path(self, path, verbose=False):
        """Format the path."""

        return all(
            [
                self.run_sort(path, verbose=verbose),
                self.run_format(path, verbose=verbose),
            ]
        )

    @staticmethod
    def run_format(path, verbose=False):
        """Run black on the path."""
        command = CommandExecutor(["poetry", "run", "ruff", "format", str(path), "--config", str(DEFAULT_RUFF_CONFIG)])
        return command.execute(verbose=verbose)

    @staticmethod
    def run_sort(path, verbose=False):
        """Run sort on the path."""
        command = CommandExecutor(
            [
                "poetry",
                "run",
                "ruff",
                "check",
                "--select",
                "I",
                "--fix",
                str(path),
                "--config",
                str(DEFAULT_RUFF_CONFIG),
            ]
        )
        return command.execute(verbose=verbose)


def single_thread_fmt(paths: list[str], verbose, logger, remote=False):
    """Run the formatting in a single thread."""
    if isinstance(paths, str):
        msg = "Paths must be a list of strings."
        raise TypeError(msg)
    results = {}
    formatter = Formatter(verbose, remote=remote)
    local_formatter = Formatter(verbose, remote=False)
    for package in track(range(len(paths)), description="Formatting..."):
        path = paths[package]
        if verbose:
            logger.info(f"Formatting: {path}")
        result = formatter.format(path)
        if not result and remote:
            logger.error(f"Failed to format {path} remotely, trying locally")
            result = local_formatter.format(path)
        results[package] = result
    return results


def multi_thread_fmt(paths, verbose, num_processes, remote=False):
    """Run the formatting in multiple threads."""
    formatter = Formatter(verbose, remote=remote)
    with Pool(num_processes) as pool:
        results = pool.map(formatter.format, paths)

    # We chekc with the local formatter if the remote formatter fails
    local_formatter = Formatter(verbose, remote=False)
    for i, result in enumerate(results):
        if not result:
            results[i] = local_formatter.format(paths[i])

    return dict(zip(paths, results, strict=False))
