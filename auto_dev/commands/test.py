"""
Test command cli module.
"""
import rich_click as click
from rich.progress import track

from auto_dev.base import build_cli
from auto_dev.test import test_path
from auto_dev.utils import get_packages

cli = build_cli()


@cli.command()
@click.option(
    "-p",
    "--path",
    help="Path to directory to test. If not provided will test all packages.",
    type=click.Path(exists=True, file_okay=False),
    default=None,
)
@click.option(
    "-w",
    "--watch",
    help="Watch the files for changes.",
    is_flag=True,
    default=False,
)
@click.pass_context
def test(ctx, path, watch):
    """
    Runs the test tooling
    """
    verbose = ctx.obj["VERBOSE"]
    logger = ctx.obj["LOGGER"]
    logger.info(f"Testing path: `{path if path else 'All dev packages/packages.json'}` ⌛")
    try:
        packages = get_packages() if not path else [path]
    except Exception as error:
        raise click.ClickException(f"Unable to get packages are you in the right directory? {error}")
    results = {}
    for package in track(range(len(packages)), description="Testing..."):
        result = test_path(str(packages[package]), verbose=verbose, watch=watch)
        results[packages[package]] = result
        logger.info(f"{'👌' if result else '❗'} - {packages[package]}")

    raises = []
    for package, result in results.items():
        if not result:
            raises.append(package)
    if raises:
        for package in raises:
            logger.error(f"❗ - {package}")
        raise click.ClickException("Testing failed! ❌")
    click.echo("Testing completed successfully! ✅")


if __name__ == "__main__":
    cli()  # pylint: disable=no-value-for-parameter
