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
def wf(path) -> None:
    """Run Workflow commands.

    Required Parameters:

        path: Path to the workflow file.

    Usage:

        adev wf my_workflow.yaml
    """

    wf_manager = WorkflowManager.from_yaml(path)
    wf_manager.run()
