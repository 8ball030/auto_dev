"""Simple cli to allow users to perform the following actions against an autonomy repo.

- lint
- test
- build
"""

from functools import partial
from multiprocessing import Pool

import rich_click as click
from rich.progress import track

from auto_dev.base import build_cli
from auto_dev.lint import check_path
from auto_dev.utils import get_paths


cli = build_cli()


@cli.command()
@click.option(
    "-p",
    "--path",
    help="Path to code to lint. If not provided will lint all packages.",
    type=click.Path(exists=True, file_okay=True),
    default=None,
)
@click.option(
    "-co",
    "--changed-only",
    help="Only lint the files that have changed.",
    is_flag=True,
    default=False,
)
@click.pass_context
def lint(ctx, path, changed_only) -> None:
    """Run linting checks on code.

    Required Parameters:

        None

    Optional Parameters:

        path (-p): Path to code to lint. (Default: None)
            - If not provided, lints all packages
            - Can be file or directory path
            - Must exist in workspace

        changed_only (-co): Only lint files that have changed. (Default: False)
            - Uses git to detect changes
            - Only lints files with uncommitted changes
            - Ignores untracked files

    Usage:

        Lint all packages:
            adev lint

        Lint specific path:
            adev lint -p ./my_package

        Lint only changed files:
            adev lint --changed-only

        Lint specific path and only changed files:
            adev lint -p ./my_package --changed-only

        Lint with verbose output:
            adev lint -v

    Notes
    -----
        Linting Tools:
            - ruff: Fast Python linter
            - pylint: Comprehensive code analysis
            - mypy: Static type checking
            - bandit: Security checks

        Features:
            - Parallel linting for performance
            - Configurable via pyproject.toml
            - Auto-fixes for common issues
            - Detailed error reporting
            - Custom rule configuration

        Integration:
            - Works with pre-commit hooks
            - CI/CD pipeline support
            - Editor/IDE integration
            - Custom plugin support

        Configuration:
            - Severity levels customization
            - Rule enabling/disabling
            - File/directory exclusions
            - Line length settings

    """
    logger = ctx.obj["LOGGER"]
    verbose = ctx.obj["VERBOSE"]
    num_processes = ctx.obj["NUM_PROCESSES"]
    logger.info("Linting Open Autonomy Packages")
    if changed_only:
        logger.info("Checking for changed files...")
    paths = get_paths(path=path, changed_only=changed_only)

    logger.info(f"Linting {len(paths)} files...")
    if num_processes > 1:
        results = multi_thread_lint(paths, verbose, num_processes)
    else:
        results = single_thread_lint(paths, verbose, logger)
    passed = sum(results.values())
    failed = len(results) - passed
    logger.info(f"Linting completed with {passed} passed and {failed} failed")
    if failed > 0:
        for file_path, result in results.items():
            if not result:
                logger.error(f"Linting failed for {file_path}")
    if failed > 0:
        msg = "Linting failed!"
        raise click.ClickException(msg)


def single_thread_lint(paths: list[str], verbose, logger):
    """Run the linting in a single thread."""
    if not isinstance(paths, list):
        msg = "Paths must be a list of strings."
        raise TypeError(msg)
    results = {}
    for package in track(range(len(paths)), description="Linting..."):
        path = paths[package]
        if verbose:
            logger.info(f"Linting: {path}")
        result = check_path(path, verbose=verbose)
        results[path] = result
    return results


def multi_thread_lint(paths, verbose, num_processes):
    """Run the linting in parallel."""
    with Pool(num_processes) as pool:
        results = pool.map(partial(check_path, verbose=verbose), paths)
    return dict(zip(paths, results, strict=False))


if __name__ == "__main__":
    cli()  # pylint: disable=no-value-for-parameter
