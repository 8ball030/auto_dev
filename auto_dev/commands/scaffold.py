"""Module to allow the scaffolding of contracts.
Contains a BlockExplorer class to allow the user to interact with
the blockchain explorer.

Also contains a Contract, which we will use to allow the user to;
- generate the open-aea contract class.
- generate the open-aea contract tests.

"""

import sys
from pathlib import Path

import yaml
import rich_click as click
from web3 import Web3
from jinja2 import Environment, FileSystemLoader
from aea.configurations.constants import DEFAULT_AEA_CONFIG_FILE, PROTOCOL_LANGUAGE_PYTHON, SUPPORTED_PROTOCOL_LANGUAGES
from aea.configurations.data_types import PublicId

from auto_dev.base import build_cli
from auto_dev.enums import FileType, BehaviourTypes
from auto_dev.utils import load_aea_ctx, remove_suffix, camel_to_snake, read_from_file
from auto_dev.constants import BASE_FSM_SKILLS, DEFAULT_ENCODING, JINJA_TEMPLATE_FOLDER, Network
from auto_dev.cli_executor import CommandExecutor
from auto_dev.handlers.base import HandlerTypes, HandlerScaffolder
from auto_dev.dao.scaffolder import DAOScaffolder
from auto_dev.workflow_manager import Task
from auto_dev.contracts.contract import DEFAULT_NULL_ADDRESS
from auto_dev.handler.scaffolder import HandlerScaffoldBuilder
from auto_dev.dialogues.scaffolder import DialogueTypes, DialogueScaffolder
from auto_dev.protocols.scaffolder import ProtocolScaffolder
from auto_dev.behaviours.scaffolder import BehaviourScaffolder
from auto_dev.connections.scaffolder import ConnectionScaffolder
from auto_dev.contracts.block_explorer import BlockExplorer
from auto_dev.contracts.contract_scafolder import ContractScaffolder


cli = build_cli()


# we have a new command group called scaffold.
@cli.group()
def scaffold() -> None:
    r"""Commands for scaffolding new components.

    Available Commands:

        contract: Scaffold a smart contract component
        fsm: Scaffold a Finite State Machine (FSM)
        protocol: Scaffold a protocol component
        connection: Scaffold a connection component
        handler: Generate an AEA handler from OpenAPI 3 specification
    """


def validate_address(address: str, logger, contract_name: str | None = None) -> str | None:
    """Convert address to checksum format and validate it."""
    if address == DEFAULT_NULL_ADDRESS:
        return address
    try:
        return Web3.to_checksum_address(str(address))
    except ValueError as e:
        name_suffix = f" for {contract_name}" if contract_name else ""
        logger.exception(f"Invalid address format{name_suffix}: {e}")
        return None


def _process_from_block_explorer(validated_address, name, logger, scaffolder):
    """Process contracts from a block explorer."""
    logger.info("Getting ABI from abidata.net")
    new_contract = scaffolder.from_block_explorer(validated_address, name)
    logger.info(f"New contract scaffolded from block explorer at {new_contract.path}")
    return new_contract


def _process_from_abi(from_abi: str, validated_address: str, name: str, logger, scaffolder) -> object | None:
    """Process contract from ABI file."""
    logger.info(f"Using ABI file: {from_abi}")
    try:
        new_contract = scaffolder.from_abi(from_abi, validated_address, name)
        logger.info(f"New contract scaffolded from ABI file at {new_contract.path}")
        return new_contract
    except Exception as e:
        logger.exception(f"Failed to process ABI file: {e!s}")
        msg = f"Error processing ABI file: {e!s}"
        raise ValueError(msg) from e


def _process_from_file(ctx, yaml_dict, network, read_functions, write_functions, logger):
    """Process contracts from a file."""
    for contract_name, contract_address in yaml_dict["contracts"].items():
        validated_address = validate_address(contract_address, logger, contract_name)
        if validated_address is None:
            continue
        ctx.invoke(
            contract,
            address=validated_address,
            name=camel_to_snake(contract_name),
            network=yaml_dict.get("network", network),
            read_functions=read_functions,
            write_functions=write_functions,
        )


@scaffold.command()
@click.argument("public_id", type=PublicId.from_str, default=None, required=False)
@click.option("--address", default=DEFAULT_NULL_ADDRESS, required=False, help="The address of the contract.")
@click.option("--from-file", default=None, help="Ingest a file containing a list of addresses and names.")
@click.option("--from-abi", default=None, help="Ingest an ABI file to scaffold a contract.")
@click.option(
    "--network",
    type=click.Choice([network.value for network in Network], case_sensitive=False),
    default=Network.ETHEREUM.value,
    help="The network to fetch the ABI from (e.g., ethereum, polygon)",
)
@click.option("--read-functions", default=None, help="Comma separated list of read functions to scaffold.")
@click.option("--write-functions", default=None, help="Comma separated list of write functions to scaffold.")
@click.pass_context
def contract(ctx, public_id, address, network, read_functions, write_functions, from_abi, from_file):
    r"""Scaffold a smart contract component.

    Required Parameters:

    one of:

        public_id: The public ID of the contract (author/name format).
        from_file: Path to file containing contract addresses and names.

    Optional Parameters:

        address(--address): Contract address on the blockchain. (Default: null address)

        from_abi(--from-abi): Path to ABI file to use for scaffolding. (Default: None)

        network(--network): Blockchain network to fetch ABI from. (Default: ethereum)

        read_functions(--read-functions): Comma-separated list of read functions to include. (Default: None (all))

        write_functions(--write-functions): Comma-separated list of write functions to include. (Default: None (all))

    Usage:
        Scaffold from address:
            adev scaffold contract author/contract_name --address 0x123...

        Scaffold from ABI file:
            adev scaffold contract author/contract_name --from-abi ./contract.abi

        Scaffold from file with multiple contracts:
            adev scaffold contract --from-file ./contracts.yaml

        Scaffold with specific network:
            adev scaffold contract author/contract_name --address 0x123... --network polygon

        Scaffold with specific functions:
            adev scaffold contract author/contract_name --address 0x123... --read-functions "balanceOf,totalSupply"
    """
    logger = ctx.obj["LOGGER"]

    # Validate inputs
    if address is None and public_id is None and from_file is None:
        msg = "Must provide either an address and public_id or a file containing a list of addresses and names."
        raise ValueError(msg)

    # Process public_id
    if public_id is not None:
        processed_name = public_id.name if public_id else None
        author = public_id.author if public_id else None
    else:
        processed_name = None
        author = None

    # Create the scaffolder before doing any processing
    block_explorer = BlockExplorer("https://abidata.net", network=Network(network))
    scaffolder = ContractScaffolder(block_explorer=block_explorer, author=author)

    # Process from file if specified
    if from_file is not None:
        with open(from_file, encoding=DEFAULT_ENCODING) as file_pointer:
            yaml_dict = yaml.safe_load(file_pointer)
        _process_from_file(ctx, yaml_dict, network, read_functions, write_functions, logger)
        return

    # Validate address
    validated_address = validate_address(address, logger)
    if validated_address is None:
        return

    # Process contract
    new_contract = None
    if from_abi is not None:
        # note, if this fails, an error is raised
        new_contract = _process_from_abi(from_abi, validated_address, processed_name, logger, scaffolder)
        logger.info(f"New contract scaffolded from ABI file at {new_contract.path}")
    else:
        new_contract = _process_from_block_explorer(validated_address, processed_name, logger, scaffolder)
        logger.info(f"New contract scaffolded from block explorer at {new_contract.path}")

    if new_contract is None:
        logger.error("Failed to scaffold contract")
        msg = "Failed to scaffold contract"
        raise ValueError(msg)
    # Generate and process contract
    logger.info("Generating openaea contract with aea scaffolder.")
    contract_path = scaffolder.generate_openaea_contract(new_contract)
    logger.info("Writing abi to file, Updating contract.yaml with build path. Parsing functions.")
    new_contract.process()
    _log_contract_info(new_contract, contract_path, logger)
    task = Task(command="autonomy packages lock")
    task.work()
    if task.is_failed:
        logger.error("Failed to lock packages Please run 'autonomy packages lock' manually.")
        return
    logger.info("Locked packages successfully.")


def _log_contract_info(contract, contract_path, logger):
    """Log contract information."""
    logger.info("Read Functions extracted:")
    for function in contract.read_functions:
        logger.info(f"    {function.name}")
    logger.info("Write Functions extracted:")
    for function in contract.write_functions:
        logger.info(f"    {function.name}")
    logger.info("Events extracted:")
    for event in contract.events:
        logger.info(f"    {event.name}")
    logger.info(f"New contract scaffolded at {contract_path}")


@scaffold.command()
@click.option("--spec", default=None, required=False)
def fsm(spec) -> None:
    """Scaffold a new Finite State Machine (FSM).

    Optional Parameters:

        spec: Path to FSM specification YAML file. Default: None

    Usage:

        Scaffold base FSM:
            adev scaffold fsm

        Scaffold from specification:
            adev scaffold fsm --spec fsm_specification.yaml

    Notes
    -----
        - Requires aea_config.yaml in current directory
        - Automatically adds required base FSM skills:
            - abstract_abci
            - abstract_round_abci
            - registration_abci
            - reset_pause_abci
            - termination_abci
        - When using spec file:
            - Must be valid FSM specification in YAML format
            - FSM label must end with 'App' suffix
            - Creates FSM based on specification structure

    """
    if not Path(DEFAULT_AEA_CONFIG_FILE).exists():
        msg = f"No {DEFAULT_AEA_CONFIG_FILE} found in current directory"
        raise ValueError(msg)

    for skill, ipfs_hash in BASE_FSM_SKILLS.items():
        command = CommandExecutor(["autonomy", "add", "skill", ipfs_hash])
        result = command.execute(verbose=True)
        if not result:
            msg = f"Adding failed for skill: {skill}"
            raise ValueError(msg)

    if not spec:
        return

    path = Path(spec)
    if not path.exists():
        msg = f"Specified spec '{path}' does not exist."
        raise click.ClickException(msg)

    fsm_spec = yaml.safe_load(path.read_text(encoding=DEFAULT_ENCODING))
    name = camel_to_snake(remove_suffix(fsm_spec["label"], "App"))

    command = CommandExecutor(["autonomy", "scaffold", "fsm", name, "--spec", str(spec)])
    result = command.execute(verbose=True)
    if not result:
        msg = f"FSM scaffolding failed for spec: {spec}"
        raise ValueError(msg)


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
    """Scaffold a new protocol component.

    Required Parameters:

        protocol_specification_path: Path to protocol specification file

    Optional Parameters:

        language: Programming language for protocol (default: python)

    Usage:

        Basic protocol scaffolding:
            adev scaffold protocol path/to/spec.yaml

        Specify language:
            adev scaffold protocol path/to/spec.yaml --l python

    Notes
    -----
        - Creates protocol package from specification
        - Supports multiple programming languages
        - Generates message classes and serialization
        - Adds protocol to agent configuration

    """
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
) -> None:
    """Scaffold a new connection component.

    Required Parameters:

        name: Name of the connection to create.

        protocol: Public ID of the protocol to use (author/name format).

    Usage:

        Create connection with protocol:
            adev scaffold connection my_connection --protocol author/protocol_name

        Create connection in specific directory:
            cd my_project
            adev scaffold connection my_connection --protocol author/protocol_name
    """
    logger = ctx.obj["LOGGER"]

    if protocol not in ctx.aea_ctx.agent_config.protocols:
        msg = f"Protocol {protocol} not found in agent configuration."
        raise click.ClickException(msg)

    scaffolder = ConnectionScaffolder(ctx, name, protocol)
    scaffolder.generate()

    connection_path = Path.cwd() / "connections" / name
    logger.info(f"New connection scaffolded at {connection_path}")


@scaffold.command()
@click.argument("spec_file", type=click.Path(exists=True), required=True)
@click.argument("public_id", type=PublicId.from_str, required=True)
@click.option("--new-skill", is_flag=True, default=False, help="Create a new skill")
@click.option("--auto-confirm", is_flag=True, default=False, help="Auto confirm all actions")
@click.pass_context
def handler(ctx, spec_file, public_id, new_skill, auto_confirm) -> int:
    """Generate an AEA handler from an OpenAPI 3 specification.

    Required Parameters:
        spec_file: Path to OpenAPI 3 specification file

        public_id: Public ID for the handler (author/name format)

    Optional Parameters:

        new_skill: Create a new skill for the handler. Default: False

        auto_confirm: Skip confirmation prompts. Default: False

    Usage:

        Basic handler generation:
            adev scaffold handler api_spec.yaml author/handler_name

        Create new skill:
            adev scaffold handler api_spec.yaml author/handler_name --new-skill

        Skip confirmations:
            adev scaffold handler api_spec.yaml author/handler_name --auto-confirm

    Notes
    -----
        - Requires aea_config.yaml in current directory
        - Generates handler code from OpenAPI endpoints
        - Creates necessary message classes
        - Can optionally create a new skill
        - Shows changes and prompts for confirmation

    """
    logger = ctx.obj["LOGGER"]
    verbose = ctx.obj["VERBOSE"]

    if not Path(DEFAULT_AEA_CONFIG_FILE).exists():
        msg = f"No {DEFAULT_AEA_CONFIG_FILE} found in current directory"
        raise ValueError(msg)

    scaffolder = (
        HandlerScaffoldBuilder()
        .create_scaffolder(spec_file, public_id, logger, verbose, new_skill=new_skill, auto_confirm=auto_confirm)
        .build()
    )

    scaffolder.scaffold()

    return 0


@scaffold.command()
@click.argument("spec_file", type=click.Path(exists=True), required=True)
@click.option("-tsa", "--target-speech-acts", default=None, help="Comma separated list of speech acts to scaffold.")
@click.option("--auto-confirm", is_flag=True, default=False, help="Auto confirm all actions")
@click.option(
    "--behaviour-type",
    type=click.Choice([f.value for f in (BehaviourTypes.metrics, BehaviourTypes.simple_fsm)]),
    required=True,
    help="The type of behaviour to generate.",
    default=BehaviourTypes.metrics.value,
)
@click.pass_context
def behaviour(
    ctx: click.Context,
    spec_file: str,
    behaviour_type: str,
    auto_confirm: bool,
    target_speech_acts: str | None,
) -> None:
    """Generate AEA behaviours from an OpenAPI 3 specification.

    Required Parameters:

        spec_file: Path to OpenAPI 3 specification file
            - Must be a valid OpenAPI 3.0+ specification
            - File must exist and be readable

    Optional Parameters:

        target_speech_acts (--target-speech-acts): Comma separated list of speech acts to scaffold. (Default: None)
            - If provided, only generates behaviours for specified speech acts
            - Must match speech acts defined in the spec

        auto_confirm (--auto-confirm): Skip confirmation prompts. (Default: False)
            - Automatically applies all changes without prompting
            - Use with caution in production environments

        behaviour_type (--behaviour-type): Type of behaviour to generate. (Default: metrics)
            - metrics: Generates metrics collection behaviour
            - simple_fsm: Generates simple finite state machine behaviour

    Usage:

        Generate metrics behaviour:
            adev scaffold behaviour openapi.yaml --behaviour-type metrics

        Generate FSM behaviour:
            adev scaffold behaviour openapi.yaml --behaviour-type simple_fsm

        Generate specific speech acts:
            adev scaffold behaviour openapi.yaml --target-speech-acts "request,inform"

        Skip confirmations:
            adev scaffold behaviour openapi.yaml --auto-confirm

    Notes
    -----
        Generation Process:
            - Parses OpenAPI specification
            - Creates behaviour class structure
            - Implements required methods
            - Adds necessary imports

        Features:
            - Multiple behaviour type support
            - Speech act filtering
            - Auto-confirmation option
            - OpenAPI 3.0+ compatibility

        Integration:
            - Works with existing AEA projects
            - Compatible with custom skills
            - Supports behaviour composition
            - Handles complex specifications

        Error Handling:
            - Validates OpenAPI specification
            - Checks speech act existence
            - Reports generation failures
            - Preserves existing code

    Returns
    -------
        None

    """
    logger = ctx.obj["LOGGER"]
    verbose = ctx.obj["VERBOSE"]

    scaffolder = BehaviourScaffolder(
        spec_file,
        behaviour_type=BehaviourTypes[behaviour_type],
        logger=logger,
        verbose=verbose,
        auto_confirm=auto_confirm,
    )
    scaffolder.scaffold(
        target_speech_acts=target_speech_acts,
    )


@scaffold.command()
@click.argument("spec_file", type=click.Path(exists=True), required=True)
@click.option("-tsa", "--target-speech-acts", default=None, help="Comma separated list of speech acts to scaffold.")
@click.option("--auto-confirm", is_flag=True, default=False, help="Auto confirm all actions")
@click.option(
    "--handler_type",
    type=click.Choice([HandlerTypes.simple]),
    required=True,
    help="The type of handler to generate.",
    default=HandlerTypes.simple,
)
@click.pass_context
def handlers(
    ctx: click.Context,
    spec_file: str,
    handler_type: HandlerTypes,
    auto_confirm: bool,
    target_speech_acts: str | None,
) -> None:
    """Generate AEA handlers from an OpenAPI 3 specification.

    Required Parameters:

        spec_file: Path to OpenAPI 3 specification file
            - Must be a valid OpenAPI 3.0+ specification
            - File must exist and be readable

    Optional Parameters:

        target_speech_acts (--target-speech-acts): Comma separated list of speech acts to scaffold. (Default: None)
            - If provided, only generates handlers for specified speech acts
            - Must match speech acts defined in the spec

        auto_confirm (--auto-confirm): Skip confirmation prompts. (Default: False)
            - Automatically applies all changes without prompting
            - Use with caution in production environments

        handler_type (--handler_type): Type of handler to generate. (Default: simple)
            - simple: Generates basic request/response handler

    Usage:

        Generate simple handler:
            adev scaffold handlers openapi.yaml --handler_type simple

        Generate specific speech acts:
            adev scaffold handlers openapi.yaml --target-speech-acts "request,inform"

        Skip confirmations:
            adev scaffold handlers openapi.yaml --auto-confirm

    Notes
    -----
        Generation Process:
            - Parses OpenAPI specification
            - Creates handler class structure
            - Implements handle methods
            - Adds necessary imports

        Features:
            - Multiple handler type support
            - Speech act filtering
            - Auto-confirmation option
            - OpenAPI 3.0+ compatibility

        Integration:
            - Works with existing AEA projects
            - Compatible with custom skills
            - Supports handler composition
            - Handles complex specifications

        Error Handling:
            - Validates OpenAPI specification
            - Checks speech act existence
            - Reports generation failures
            - Preserves existing code

    Returns
    -------
        None

    """
    logger = ctx.obj["LOGGER"]
    verbose = ctx.obj["VERBOSE"]

    scaffolder = HandlerScaffolder(
        spec_file, handler_type=handler_type, logger=logger, verbose=verbose, auto_confirm=auto_confirm
    )
    scaffolder.scaffold(
        target_speech_acts=target_speech_acts,
    )


@scaffold.command()
@click.argument("spec_file", type=click.Path(exists=True), required=True)
@click.option("-tsa", "--target-speech-acts", default=None, help="Comma separated list of speech acts to scaffold.")
@click.option("--auto-confirm", is_flag=True, default=False, help="Auto confirm all actions")
@click.option(
    "--dialogue-type",
    type=click.Choice([DialogueTypes.simple]),
    required=True,
    help="The type of dialogue to generate.",
    default=DialogueTypes.simple,
)
@click.pass_context
def dialogues(
    ctx: click.Context,
    spec_file: str,
    dialogue_type: DialogueTypes,
    auto_confirm: bool,
    target_speech_acts: str | None,
) -> None:
    """Generate AEA dialogues from an OpenAPI 3 specification.

    Required Parameters:

        spec_file: Path to OpenAPI 3 specification file
            - Must be a valid OpenAPI 3.0+ specification
            - File must exist and be readable

    Optional Parameters:

        target_speech_acts (--target-speech-acts): Comma separated list of speech acts to scaffold. (Default: None)
            - If provided, only generates dialogues for specified speech acts
            - Must match speech acts defined in the spec

        auto_confirm (--auto-confirm): Skip confirmation prompts. (Default: False)
            - Automatically applies all changes without prompting
            - Use with caution in production environments

        dialogue_type (--dialogue-type): Type of dialogue to generate. (Default: simple)
            - simple: Generates basic request/response dialogue

    Usage:
        Generate simple dialogue:
            adev scaffold dialogues openapi.yaml --dialogue-type simple

        Generate specific speech acts:
            adev scaffold dialogues openapi.yaml --target-speech-acts "request,inform"

        Skip confirmations:
            adev scaffold dialogues openapi.yaml --auto-confirm

    Notes
    -----
        Generation Process:
            - Parses OpenAPI specification
            - Creates dialogue class structure
            - Implements dialogue rules
            - Adds necessary imports

        Features:
            - Multiple dialogue type support
            - Speech act filtering
            - Auto-confirmation option
            - OpenAPI 3.0+ compatibility

        Integration:
            - Works with existing AEA projects
            - Compatible with custom skills
            - Supports dialogue composition
            - Handles complex specifications

        Error Handling:
            - Validates OpenAPI specification
            - Checks speech act existence
            - Reports generation failures
            - Preserves existing code

    Returns
    -------
        None

    """
    logger = ctx.obj["LOGGER"]
    verbose = ctx.obj["VERBOSE"]

    scaffolder = DialogueScaffolder(
        spec_file, dialogue_type=dialogue_type, logger=logger, verbose=verbose, auto_confirm=auto_confirm
    )
    scaffolder.scaffold(
        target_speech_acts=target_speech_acts,
    )


@scaffold.command()
@click.pass_context
def tests(
    ctx,
) -> None:
    """Generate tests for an aea component in the current directory
    AEA handler from an OpenAPI 3 specification.
    """
    logger = ctx.obj["LOGGER"]
    verbose = ctx.obj["VERBOSE"]
    env = Environment(loader=FileSystemLoader(Path(JINJA_TEMPLATE_FOLDER, "tests", "customs")), autoescape=True)
    template = env.get_template("test_custom.jinja")
    output = template.render(
        name="test",
    )
    if verbose:
        logger.info(f"Generated tests: {output}")


@scaffold.command()
@click.option(
    "--auto-confirm",
    is_flag=True,
    default=False,
    help="Automatically confirm all prompts",
)
@click.pass_context
def dao(ctx, auto_confirm) -> None:
    """Scaffold Data Access Objects (DAOs) and generate test scripts based on an OpenAPI 3 specification.

    This command creates:

    1. Data Access Object classes for each model in the OpenAPI spec
    2. Sample data for testing
    3. Test scripts to validate the Data Access Objects
    """
    logger = ctx.obj["LOGGER"]
    verbose = ctx.obj["VERBOSE"]

    if not Path("component.yaml").exists():
        msg = "component.yaml not found in the current directory."
        raise ValueError(msg)

    customs_config = read_from_file(Path("component.yaml"), FileType.YAML)
    if customs_config is None:
        msg = "Error: customs_config is None. Unable to process."
        raise ValueError(msg)

    api_spec_path = customs_config.get("api_spec")
    if not api_spec_path:
        msg = "Error: api_spec key not found in component.yaml"
        raise ValueError(msg)

    component_author = customs_config.get("author")
    component_name = customs_config.get("name")
    public_id = PublicId(component_author, component_name.split(":")[0])
    dao_dir = Path.cwd() / "daos"
    if (
        dao_dir.exists()
        and not auto_confirm
        and not click.confirm("DAOs directory already exists. Do you want to overwrite it?")
    ):
        logger.info("Aborting DAO scaffolding.")
        sys.exit(1)

    try:
        scaffolder = DAOScaffolder(logger, verbose, auto_confirm, public_id)
        scaffolder.scaffold()
    except Exception as e:
        logger.exception(f"Failed to scaffold DAO: {e!s}")
        msg = "Error during DAO scaffolding and test generation"
        raise ValueError(msg) from e


if __name__ == "__main__":
    cli()  # pylint: disable=no-value-for-parameter
