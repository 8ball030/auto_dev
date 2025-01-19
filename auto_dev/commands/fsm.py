"""Implement fsm tooling."""

from enum import Enum

import rich_click as click

from auto_dev.base import build_cli
from auto_dev.utils import get_logger
from auto_dev.fsm.fsm import FsmSpec


logger = get_logger()

cli = build_cli(plugins=False)


# we have a fsm command group
@cli.group()
def fsm() -> None:
    """Implement fsm tooling."""


class FsmType(Enum):
    """Type of FSM output"""

    MERMAID = "mermaid"
    FSM_SPEC = "fsm_spec"


INPUT_TO_FUNC = {FsmType.MERMAID.value: FsmSpec.from_mermaid_path, FsmType.FSM_SPEC.value: FsmSpec.from_path}


@fsm.command()
@click.argument(
    "fsm_spec",
    type=click.Path(
        "r",
    ),
)
@click.argument("fsm_name", type=str)
@click.option(
    "--in-type", type=click.Choice([f.value for f in FsmType], case_sensitive=False), default=FsmType.FSM_SPEC.value
)
@click.option(
    "--output", type=click.Choice([f.value for f in FsmType], case_sensitive=False), default=FsmType.MERMAID.value
)
def from_file(fsm_spec: str, fsm_name: str, in_type: str, output: str) -> None:
    """
    We parse an fsm file, in order to covnert between mermaid and fsm_spec.

    Example Usage:
    `adev fsm from-file auto_dev/data/fsm/fsm_specification.yaml testAbciApp`
    `adev fsm from-file auto_dev/data/fsm/fsm_specification.yaml testAbciApp --output fsm_spec`
    """

    fsm = INPUT_TO_FUNC[in_type](fsm_spec, label=fsm_name)
    output_to_func = {FsmType.MERMAID.value: fsm.to_mermaid, FsmType.FSM_SPEC.value: fsm.to_string}
    output = output_to_func[output]()
    click.echo(output)
