"""This module contains the logic for the fmt command."""

import rich_click as click

from auto_dev.fmt import multi_thread_fmt, single_thread_fmt
from auto_dev.base import build_cli
from auto_dev.utils import get_paths


cli = build_cli()


@cli.command()
@click.option(
    "-p",
    "--path",
    help="Path to code to format. If not provided will format all packages.",
    type=click.Path(exists=True, file_okay=True, dir_okay=True),
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
def fmt(ctx, path, changed_only) -> None:
    r"""Format code using the configured formatters.

    Optional Parameters:\n
        path (-p): Path to code to format. (Default: None)\n
            - If not provided, formats all packages\n
            - Can be file or directory path\n
            - Must exist in workspace\n
        changed_only (-co): Only format files that have changed. (Default: False)\n
            - Uses git to detect changes\n
            - Only formats files with uncommitted changes\n
            - Ignores untracked files\n

    Usage:
        Format all packages:\n
            adev fmt\n

        Format specific path:\n
            adev fmt -p ./my_package\n

        Format only changed files:\n
            adev fmt --changed-only\n

        Format specific path and only changed files:\n
            adev fmt -p ./my_package --changed-only\n

    Notes
    -----
        - Uses multiple formatters:
            - black: Python code formatting
            - isort: Import sorting
            - docformatter: Docstring formatting
        - Supports parallel processing for faster formatting
        - Shows formatting statistics on completion
        - Exits with error if any formatting fails
        - Can be integrated into pre-commit hooks
        - Respects .gitignore patterns

    """
    verbose = ctx.obj["VERBOSE"]
    num_processes = ctx.obj["NUM_PROCESSES"]
    logger = ctx.obj["LOGGER"]
    remote = ctx.obj["REMOTE"]
    logger.info("Formatting Open Autonomy Packages...")
    logger.info(f"Remote: {remote}")
    paths = get_paths(path, changed_only)
    logger.info(f"Formatting {len(paths)} files...")
    if num_processes > 1:
        results = multi_thread_fmt(paths, verbose, num_processes, remote=remote)
    else:
        results = single_thread_fmt(paths, verbose, logger, remote=remote)
    passed = sum(results.values())
    failed = len(results) - passed
    logger.info(f"Formatting completed with {passed} passed and {failed} failed")
    if failed > 0:
        msg = "Formatting failed!"
        raise click.ClickException(msg)
