"""
Module to allow the scaffolding of contracts.
Contains a BlockExplorer class to allow the user to interact with
the blockchain explorer.

Also contains a Contract, which we will use to allow the user to;
- generate the open-aea contract class.
- generate the open-aea contract tests.

"""

from pathlib import Path

import rich_click as click
import yaml
from aea.configurations.constants import DEFAULT_AEA_CONFIG_FILE, PROTOCOL_LANGUAGE_PYTHON, SUPPORTED_PROTOCOL_LANGUAGES
from aea.configurations.data_types import PublicId

from auto_dev.base import build_cli
from auto_dev.cli_executor import CommandExecutor
from auto_dev.connections.scaffolder import ConnectionScaffolder
from auto_dev.constants import BASE_FSM_SKILLS, DEFAULT_ENCODING
from auto_dev.contracts.block_explorer import BlockExplorer
from auto_dev.contracts.contract_scafolder import ContractScaffolder
from auto_dev.handler.scaffolder import HandlerScaffolder
from auto_dev.protocols.scaffolder import ProtocolScaffolder
from auto_dev.utils import camel_to_snake, change_dir, load_aea_ctx, remove_suffix

cli = build_cli()


# we have a new command group called scaffold.
@cli.group()
def scaffold():
    """
    Scaffold a (set of) components.
    """


@scaffold.command()
@click.argument("address", default=None, required=False)
@click.argument("name", default=None, required=False)
@click.option("--from-file", default=None, help="Ingest a file containing a list of addresses and names.")
@click.option("--block-explorer-url", default="https://api.etherscan.io/api")
@click.option("--block-explorer-api-key", required=True)
@click.option("--read-functions", default=None, help="Comma separated list of read functions to scaffold.")
@click.option("--write-functions", default=None, help="Comma separated list of write functions to scaffold.")
@click.pass_context
def contract(  # pylint: disable=R0914
    ctx, address, name, block_explorer_url, block_explorer_api_key, read_functions, write_functions, from_file
):
    """
    Scaffold a contract.
    """
    logger = ctx.obj["LOGGER"]
    if address is None and name is None and from_file is None:
        logger.error("Must provide either an address and name or a file containing a list of addresses and names.")
        return
    if from_file is not None:
        with open(from_file, "r", encoding=DEFAULT_ENCODING) as file_pointer:
            yaml_dict = yaml.safe_load(file_pointer)
        for contract_name, contract_address in yaml_dict["contracts"].items():
            ctx.invoke(
                contract,
                address=str(contract_address),
                name=camel_to_snake(contract_name),
                block_explorer_url=yaml_dict["block_explorer_url"],
                block_explorer_api_key=block_explorer_api_key,
                read_functions=read_functions,
                write_functions=write_functions,
            )

        return
    logger.info(f"Using block explorer url: {block_explorer_url}")
    logger.info(f"Scaffolding contract at address: {address} with name: {name}")

    block_explorer = BlockExplorer(block_explorer_url, block_explorer_api_key)
    scaffolder = ContractScaffolder(block_explorer=block_explorer)
    logger.info("Getting abi from block explorer.")
    new_contract = scaffolder.from_block_explorer(address, name)
    logger.info("Generating openaea contract with aea scaffolder.")
    contract_path = scaffolder.generate_openaea_contract(new_contract)
    logger.info("Writing abi to file, Updating contract.yaml with build path. Parsing functions.")
    new_contract.process()
    logger.info("Read Functions:")
    for function in new_contract.read_functions:
        logger.info(f"    {function.name}")
    logger.info("Write Functions:")
    for function in new_contract.write_functions:
        logger.info(f"    {function.name}")

    logger.info(f"New contract scaffolded at {contract_path}")


@scaffold.command()
@click.option("--spec", default=None, required=False)
def fsm(spec):
    """
    Scaffold a FSM.

    usage: `adev scaffold fsm [--spec fsm_specification.yaml]`
    """

    if not Path(DEFAULT_AEA_CONFIG_FILE).exists():
        raise ValueError(f"No {DEFAULT_AEA_CONFIG_FILE} found in current directory")

    for skill, ipfs_hash in BASE_FSM_SKILLS.items():
        command = CommandExecutor(["autonomy", "add", "skill", ipfs_hash])
        result = command.execute(verbose=True)
        if not result:
            raise ValueError(f"Adding failed for skill: {skill}")

    if not spec:
        return

    path = Path(spec)
    if not path.exists():
        raise click.ClickException(f"Specified spec '{path}' does not exist.")

    fsm_spec = yaml.safe_load(path.read_text(encoding=DEFAULT_ENCODING))
    name = camel_to_snake(remove_suffix(fsm_spec["label"], "App"))

    command = CommandExecutor(["autonomy", "scaffold", "fsm", name, "--spec", str(spec)])
    result = command.execute(verbose=True)
    if not result:
        raise ValueError(f"FSM scaffolding failed for spec: {spec}")


@scaffold.command()
@click.argument("protocol_specification_path", type=str, required=True)
@click.option(
    "--l",
    "language",
    type=click.Choice(SUPPORTED_PROTOCOL_LANGUAGES),
    required=False,
    default=PROTOCOL_LANGUAGE_PYTHON,
    help="Specify the language in which to generate the protocol package.",
)
@click.pass_context
def protocol(ctx, protocol_specification_path: str, language: str) -> None:
    """Scaffold a protocol"""

    logger = ctx.obj["LOGGER"]
    verbose = ctx.obj["VERBOSE"]
    scaffolder = ProtocolScaffolder(protocol_specification_path, language, logger=logger, verbose=verbose)
    scaffolder.generate()


@scaffold.command()
@click.argument("name", default=None, required=True)
@click.option("--protocol", type=PublicId.from_str, required=True, help="the PublicId of a protocol.")
@click.pass_context
@load_aea_ctx
def connection(  # pylint: disable=R0914
    ctx,
    name,
    protocol: PublicId,
):
    """
    Scaffold a connection.
    """

    logger = ctx.obj["LOGGER"]

    if protocol not in ctx.aea_ctx.agent_config.protocols:
        raise click.ClickException(f"Protocol {protocol} not found in agent configuration.")

    scaffolder = ConnectionScaffolder(ctx, name, protocol)
    scaffolder.generate()

    connection_path = Path.cwd() / "connections" / name
    logger.info(f"New connection scaffolded at {connection_path}")


@scaffold.command()
@click.argument("spec_file", type=click.Path(exists=True))
@click.option("--author", default="eightballer", help="Author of the skill")
@click.option("--output", default="my_api_skill", help="Name of API skill")
@click.pass_context
def handler(ctx, spec_file, author, output):
    """Generate an AEA handler from an OpenAPI 3 specification."""

    logger = ctx.obj["LOGGER"]
    verbose = ctx.obj["VERBOSE"]

    scaffolder = HandlerScaffolder(spec_file, author, output, logger=logger, verbose=verbose)
    handler_code = scaffolder.generate()

    with change_dir(f"skills/{output}"):
        output_path = Path('handlers.py')
        scaffolder.save_handler(output_path, handler_code)
        skill_yaml_file = "skill.yaml"

        scaffolder.update_skill_yaml(skill_yaml_file)
        scaffolder.move_and_update_my_model()
        scaffolder.remove_behaviours()
        scaffolder.create_dialogues()

    return 0


if __name__ == "__main__":
    cli()  # pylint: disable=no-value-for-parameter
