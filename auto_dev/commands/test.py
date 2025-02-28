"""Command to run tests for packages."""

import rich_click as click

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
@click.option(
    "-c", "--coverage-report/--no-coverage-report", help="Run the coverage report", is_flag=True, default=False
)
@click.pass_context
def test(ctx, path, watch, coverage_report) -> None:
    """Run tests for packages.

    Required Parameters:
        None

    Optional Parameters:

        path (-p): Path to directory to test. (Default: None)
            - If not provided, tests all packages
            - Must be a valid directory containing tests
            - Can be package root or specific test directory

        watch (-w): Watch files for changes and re-run tests. (Default: False)
            - Monitors file changes in real-time
            - Re-runs tests when files are modified
            - Useful for test-driven development

        coverage_report (-c): Generate test coverage report. (Default: True)
            - Creates detailed coverage analysis
            - Shows line-by-line coverage stats
            - Generates HTML report for visualization

    Usage:
        Test all packages:
            adev test

        Test specific directory:
            adev test -p ./my_package

        Test with file watching:
            adev test -w

        Test without coverage report:
            adev test --no-coverage-report

        Test specific directory with watching:
            adev test -p ./my_package -w

    Notes
    -----
        Test Framework:
            - Uses pytest as test runner
            - Supports fixtures and markers
            - Handles async tests
            - Configurable via pytest.ini

        Coverage:
            - Tracks line and branch coverage
            - Excludes test files from coverage
            - Sets minimum coverage thresholds
            - Generates HTML reports

        Features:
            - Parallel test execution
            - JUnit XML reports
            - Integration with CI/CD
            - Detailed failure reporting
            - Test categorization with markers

        Error Handling:
            - Reports test failures
            - Shows detailed error traces
            - Exits with error on failure
            - Preserves test state on error

    """
    verbose = ctx.obj["VERBOSE"]
    click.echo(
        f"Testing path: `{path or 'All dev packages/packages.json'}` ⌛",
    )

    if coverage_report:
        cli_runner = CommandExecutor(COVERAGE_COMMAND)
        if not cli_runner.execute(stream=True, shell=True):
            msg = "Unable to successfully execute coverage report"
            raise OperationError(msg)

    try:
        packages = get_packages() if not path else [path]
    except FileNotFoundError as error:
        msg = f"Unable to get packages are you in the right directory? {error}"
        raise click.ClickException(msg) from error
    results = {}
    for package in range(len(packages)):
        click.echo(f"Testing {packages[package]} {package + 1}/{len(packages)}")
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
