"""This module contains the logic for the fmt command."""

from pathlib import Path

import rich_click as click
from aea.configurations.base import PublicId

from auto_dev.base import build_cli
from auto_dev.utils import camel_to_snake
from auto_dev.fsm.fsm import FsmSpec
from auto_dev.constants import WORKFLOWS_FOLDER
from auto_dev.workflow_manager import Workflow, WorkflowManager


cli = build_cli()


@cli.command()
@click.argument(
    "public_id",
    type=PublicId.from_str,
)
@click.argument(
    "fsm_spec_file_path",
    type=click.Path(exists=True),
)
def create_from_fsm(public_id: PublicId, fsm_spec_file_path: str) -> None:
    r"""Create an agent from a finite state machine specification.

    Required Parameters:

        public_id: The public id of the agent to be created.

        fsm_spec_file_path: The path to the FSM specification file.

    Usage:
        Create a new agent from a finite state machine specification.
            adev create_from_fsm eightballer/agent_2 auto_dev/data/fsm/samples/fsm_specification.yaml

    """
    click.echo(f"Creating agent {public_id} from FSM specification {fsm_spec_file_path}")

    fsm = FsmSpec.from_path(
        fsm_spec_file_path,
    )

    wf = Workflow.from_file(Path(WORKFLOWS_FOLDER) / "create_new_agent_from_fsm.yaml")
    kwargs = {
        "new_author": public_id.author,
        "new_agent": public_id.name,
        "new_skill": camel_to_snake(fsm.label),
        "fsm_spec_path": fsm_spec_file_path,
    }
    wf.kwargs = kwargs
    wf_manager = WorkflowManager()
    wf_manager.add_workflow(wf)
    wf_manager.run_workflow(wf.id)
