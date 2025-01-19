"""Test command cli module."""

from pathlib import Path

import rich_click as click
from rich.progress import track

from auto_dev.base import build_cli
from auto_dev.test import COVERAGE_COMMAND, test_path
from auto_dev.utils import get_packages
from auto_dev.exceptions import OperationError
from auto_dev.cli_executor import CommandExecutor


cli = build_cli()


@cli.command()
@click.option(
    "-p",
    "--path",
    help="Path to directory to test. If not provided will test all packages.",
    type=click.Path(exists=True, file_okay=True),
    default=None,
)
@click.option(
    "-w",
    "--watch",
    help="Watch the files for changes.",
    is_flag=True,
    default=False,
)
@click.option("-c", "--coverage-report", help="Run the coverage report", is_flag=True, default=True)
@click.pass_context
def test(ctx, path, watch, coverage_report) -> None:
    """Runs the test tooling."""
    verbose = ctx.obj["VERBOSE"]
    click.echo(
        f"Testing path: `{path or 'All dev packages/packages.json'}` ⌛",
    )

    if coverage_report:
        cli_runner = CommandExecutor(COVERAGE_COMMAND)
        if not cli_runner.execute(stream=True, shell=True):
            msg = f"Unable to successfully execute coverage report"
            raise OperationError(msg)

    try:
        packages = get_packages() if not path else [path]
    except FileNotFoundError as error:
        msg = f"Unable to get packages are you in the right directory? {error}"
        raise click.ClickException(msg) from error
    results = {}
    for package in track(range(len(packages)), description="Testing..."):
        result = test_path(str(packages[package]), verbose=verbose, watch=watch)
        results[packages[package]] = result
        click.echo(f"{'👌' if result else '❗'} - {packages[package]}")

    raises = []
    for package, result in results.items():
        if not result:
            raises.append(package)
    if raises:
        for package in raises:
            click.echo(f"❗ - {package}")
        msg = "Testing failed! ❌"
        raise click.ClickException(msg)
    click.echo("Testing completed successfully! ✅")


if __name__ == "__main__":
    cli()  # pylint: disable=no-value-for-parameter
