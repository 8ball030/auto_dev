r"""Commands for FSM (Finite State Machine) operations.

Available Commands:

    from_file: Convert between FSM specification formats

Required Parameters:

    fsm_spec: Path to the FSM specification file

    fsm_name: Name of the FSM to process

Optional Parameters:

    in_type: Input format type (fsm_spec or mermaid). Default: fsm_spec

    output: Output format type (fsm_spec or mermaid). Default: mermaid

    output_path: Path to write the output to. If not provided, prints to stdout.

Usage:
    Convert FSM spec to mermaid and save to file:
        adev fsm from-file fsm_specification.yaml testAbciApp --output-path diagram.mmd

    Convert FSM spec to mermaid and print to stdout:
        adev fsm from-file fsm_specification.yaml testAbciApp

    Convert FSM spec to FSM spec (validation):
        adev fsm from-file fsm_specification.yaml testAbciApp --output fsm_spec

    Convert from mermaid to FSM spec:
        adev fsm from-file diagram.mmd testAbciApp --in-type mermaid --output fsm_spec

    Convert mermaid to mermaid (validation):
        adev fsm from-file diagram.mmd testAbciApp --in-type mermaid
"""

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
    """Type of FSM output."""

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
@click.option(
    "--output-path",
    type=click.Path(dir_okay=False, writable=True),
    help="Path to write the output to. If not provided, prints to stdout.",
    default=None,
)
def from_file(fsm_spec: str, fsm_name: str, in_type: str, output: str, output_path: str | None) -> None:
    r"""Convert between FSM specification formats.

    Required Parameters:

        fsm_spec: Path to the FSM specification file

        fsm_name: Name of the FSM to process

    Optional Parameters:

        in_type: Input format type (fsm_spec or mermaid). (Default: fsm_spec)

        output: Output format type (fsm_spec or mermaid). (Default: mermaid)

        output_path: Path to write the output to. If not provided, prints to stdout.

    Usage:

        Convert FSM spec to mermaid and save to file:
            adev fsm from-file fsm_specification.yaml testAbciApp --output-path diagram.mmd

        Convert FSM spec to mermaid and print to stdout:
            adev fsm from-file fsm_specification.yaml testAbciApp

        Convert FSM spec to FSM spec (validation):
            adev fsm from-file fsm_specification.yaml testAbciApp --output fsm_spec

        Convert from mermaid to FSM spec:
            adev fsm from-file diagram.mmd testAbciApp --in-type mermaid --output fsm_spec

        Convert mermaid to mermaid (validation):
            adev fsm from-file diagram.mmd testAbciApp --in-type mermaid
    """

    fsm = INPUT_TO_FUNC[in_type](fsm_spec, label=fsm_name)
    output_to_func = {FsmType.MERMAID.value: fsm.to_mermaid, FsmType.FSM_SPEC.value: fsm.to_string}
    result = output_to_func[output]()

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(result)
        logger.info(f"Output written to {output_path}")
    else:
        click.echo(result)
