"""Wf manager commands."""

import rich_click as click

from auto_dev.base import build_cli
from auto_dev.workflow_manager import WorkflowManager


cli = build_cli()


@cli.command()
@click.argument(
    "path",
    type=click.Path(exists=True, file_okay=True),
    default=None,
)
@click.option(
    "--params", type=str, help="Parameters for the workflow in key=value format, separated by commas.", default=""
)
def wf(path, params) -> None:
    """Run Workflow commands.

    Required Parameters:

        path: Path to the workflow file.

    Usage:

        adev wf my_workflow.yaml --params key1=value1,key2=value2

    """

    wf_manager = WorkflowManager.load_custom_workflow(path, params)
    wf_manager.run()
