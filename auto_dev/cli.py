"""
Simple cli to allow users to perform the following actions against an autonomy repo;

- lint
- test
- build
"""

import rich_click as click
from rich.progress import track

from auto_dev.test import test_path

from .lint import check_path
from .utils import get_logger, get_packages

click.rich_click.USE_RICH_MARKUP = True
# so we can pretty print the output

logger = get_logger()


@click.group()
# set debug to true to enable debug logging
@click.option("--debug/--no-debug", default=False)
def cli(debug=False):
    """Main auto dev command group."""
    if debug:
        logger.setLevel("DEBUG")
    else:
        logger.setLevel("INFO")


@cli.command()
@click.option("-v", "--verbose", is_flag=True, default=False)
@click.option(
    "-p",
    "--path",
    help="Path to code to lint. If not provided will lint all packages.",
    type=click.Path(exists=True, file_okay=False),
    default=None,
)
def lint(verbose, path):
    """
    Runs the linting tooling
    """
    logger.info("Linting Open Autonomy Packages")
    try:
        packages = get_packages() if not path else [path]
    except Exception as error:
        raise click.ClickException(f"Unable to get packages are you in the right directory? {error}")

    results = {}
    for package in track(range(len(packages)), description="Linting..."):
        logger.debug("Processing package: './%s'", packages[package])
        result = check_path(str(packages[package]), verbose=verbose)
        results[packages[package]] = result

    for package, result in results.items():
        if not result:
            logger.error("Package '%s' failed linting", package)

    if False in results.values():
        raise click.ClickException("Linting failed!")

    logger.info("Linting completed successfully!")


@cli.command()
@click.option("-v", "--verbose", is_flag=True, default=False)
@click.option(
    "-p",
    "--path",
    help="Path to directory to test. If not provided will test all packages.",
    type=click.Path(exists=True, file_okay=False),
    default=None,
)
def test(verbose, path):
    """
    Runs the test tooling
    """
    click.echo("Testing Open Autonomy Packages")
    try:
        packages = get_packages() if not path else [path]
    except Exception as error:
        raise click.ClickException(f"Unable to get packages are you in the right directory? {error}")
    results = {}
    for package in track(range(len(packages)), description="Testing..."):
        logger.debug("Processing package: './%s'", packages[package])
        result = test_path(str(packages[package]), verbose=verbose)
        results[packages[package]] = result

    for package in results.items():
        if not package:
            logger.error("Package '%s' failed testing", package)
    # if any of the results are false, we need to raise an exception
    if False in results.values():
        raise click.ClickException("Testing failed!")

    click.echo("Testing completed successfully!")


@cli.command()
def build():
    """
    Runs the build tooling
    """
    click.echo("Building...")
    click.echo("Building complete!")

@cli.group()
def contract():
    """
    Contract management
    """

@contract.command()
def generate_tests():
    """
    Generates tests for contracts
    """
    click.echo("Generating tests...")
    click.echo("Generating tests complete!")

if __name__ == "__main__":
    cli()
