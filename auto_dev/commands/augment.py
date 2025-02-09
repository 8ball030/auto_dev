"""Implement scaffolding tooling."""

import sys
import difflib
from copy import deepcopy
from pathlib import Path

import yaml
import rich_click as click
from aea.configurations.base import SKILLS, PublicId, PackageType
from aea.configurations.constants import DEFAULT_SKILL_CONFIG_FILE

from auto_dev.base import build_cli
from auto_dev.enums import FileType, BehaviourTypes
from auto_dev.utils import get_logger, write_to_file, read_from_file, snake_to_camel, load_autonolas_yaml
from auto_dev.constants import DEFAULT_ENCODING, FSM_END_CLASS_NAME
from auto_dev.exceptions import OperationError
from auto_dev.workflow_manager import Task
from auto_dev.handler.scaffolder import HandlerScaffoldBuilder
from auto_dev.behaviours.scaffolder import BehaviourScaffolder


logger = get_logger()

cli = build_cli(plugins=False)

# we have a scaffold command group

BASE_LOGGING_CONFIG = yaml.safe_load(
    """
logging_config:
    disable_existing_loggers: true
    version: 1
    formatters:
        standard:
            format: '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    handlers:
        {handlers_config}
    loggers:
        aea:
            handlers: {handlers_list}
            level: INFO
            propagate: false
"""
)

LEDGER_CONNECTION_CONFIG = yaml.safe_load(
    """
public_id: valory/ledger:0.19.0
type: connection
config:
  ledger_apis:
    ethereum:
      address: ${str}
      chain_id: ${int}
      poa_chain: ${bool:false}
      default_gas_price_strategy: ${str:eip1559}
"""
)

IPFS_CONNECTION_CONFIG = yaml.safe_load(
    """
public_id: valory/ipfs:0.1.0
type: connection
config:
  ipfs_domain: /dns/registry.autonolas.tech/tcp/443/https
"""
)

ABCI_CONNECTION_CONFIG = yaml.safe_load(
    """
public_id: valory/abci:0.1.0
type: connection
config:
  host: ${str:localhost}
  port: ${int:26658}
  use_tendermint: ${bool:false}
  target_skill_id: ${str}
"""
)

PROMETHEUS_CONNECTION_CONFIG = yaml.safe_load(
    """
public_id: fetchai/prometheus:0.8.0
type: connection
config:
  port: 8888
  host: 0.0.0.0
"""
)

WEBSOCKET_SERVER_CONNECTION_CONFIG = yaml.safe_load(
    """
public_id: eightballer/websocket_server:0.1.0
type: connection
config:
  target_skill_id: ${str}
  port: 8080
  host: 0.0.0.0
"""
)

HTTP_SERVER_CONNECTION_CONFIG = yaml.safe_load(
    """
public_id: eightballer/http_server:0.1.0
type: connection
config:
  target_skill_id: ${str}
  port: 26658
  host: 0.0.0.0
"""
)

CONSOLE_HANDLER = yaml.safe_load(
    """
class: rich.logging.RichHandler
level: INFO
"""
)

HTTP_HANDLER = yaml.safe_load(
    """
class: logging.handlers.HTTPHandler
formatter: standard
level: INFO
host: ${LOG_SERVER:str:localhost:8000}
url: /log/
method: POST
"""
)

LOGFILE_HANDLER = yaml.safe_load(
    """
class: logging.FileHandler
formatter: standard
filename: ${LOG_FILE:str:log.txt}
level: INFO
"""
)

HANDLERS = {
    "console": CONSOLE_HANDLER,
    "http": HTTP_HANDLER,
    "logfile": LOGFILE_HANDLER,
}

CONNECTIONS = {
    "ledger": (
        "valory/ledger:0.19.0:bafybeicgfupeudtmvehbwziqfxiz6ztsxr5rxzvalzvsdsspzz73o5fzfi",
        LEDGER_CONNECTION_CONFIG,
    ),
    "abci": ("valory/abci:0.1.0:bafybeigtjiag4a2h6msnlojahtc5pae7jrphjegjb3mlk2l54igc4jwnxe", ABCI_CONNECTION_CONFIG),
    "ipfs": ("valory/ipfs:0.1.0:bafybeieymwm2o7qp3aybimpsw75qwrqsdqeq764sqlhggookgitncituwa", IPFS_CONNECTION_CONFIG),
    "p2p_libp2p_client": (
        "valory/p2p_libp2p_client:0.1.0:bafybeidfm65eece533hfvg2xyn4icpmvz4lmvbemstrlo3iuffb7e72ycq",
        {},
    ),
    "http_client": ("valory/http_client:0.23.0:bafybeidykl4elwbcjkqn32wt5h4h7tlpeqovrcq3c5bcplt6nhpznhgczi", {}),
    "http_server": (
        "eightballer/http_server:0.1.0:bafybeic5m2px4wanaqjc6jc3ileqmc76k2loitjrsmlffqvafx7bznwrba",
        HTTP_SERVER_CONNECTION_CONFIG,
    ),
    "websocket_server": (
        "eightballer/websocket_server:0.1.0:bafybeifop5szl2ikmesdax7mhjsbtzklfqlkxacm3jvk4hxnl32fhxedwy",
        WEBSOCKET_SERVER_CONNECTION_CONFIG,
    ),
    "prometheus": (
        "fetchai/prometheus:0.8.0:bafybeid3gtvpl2rjo2bccjg27mye3ckyimbn42xtbjqnajjmfkmajnfjeu",
        PROMETHEUS_CONNECTION_CONFIG,
    ),
}

AEA_CONFIG = "aea-config.yaml"


class BaseScaffolder:
    """Base class for scaffolding functionality.

    Initializes a scaffolder with logging and loads the AEA configuration.
    """

    def load(self) -> None:
        """Load."""
        if not Path(AEA_CONFIG).exists():
            msg = f"File {AEA_CONFIG} not found"
            raise FileNotFoundError(msg)
        content = Path(AEA_CONFIG).read_text(encoding=DEFAULT_ENCODING)
        self.aea_config = list(yaml.safe_load_all(content))

    def __init__(self) -> None:
        self.logger = get_logger()
        self.load()


class LoggingScaffolder(BaseScaffolder):
    """Logging scaffolder."""

    def generate(self, handlers: list):
        """Scaffold logging."""
        self.logger.info(f"Generating logging config with handlers: {handlers}")
        if not handlers:
            msg = "No handlers provided"
            raise ValueError(msg)
        if handlers == ["all"]:
            handlers = HANDLERS
        for handler in handlers:
            if handler not in HANDLERS:
                msg = f"Handler '{handler}' not found"
                raise ValueError(msg)
            handlers = {handler: HANDLERS[handler] for handler in handlers}
        logging_config = deepcopy(BASE_LOGGING_CONFIG)
        logging_config["logging_config"]["handlers"] = handlers
        logging_config["logging_config"]["loggers"]["aea"]["handlers"] = list(handlers.keys())
        return logging_config

    def scaffold(self, handlers: list):
        """Scaffold logging."""
        path = "aea-config.yaml"
        if not Path(path).exists():
            msg = f"File {path} not found"
            raise FileNotFoundError(msg)

        config = yaml.safe_load_all(Path(path).read_text(encoding=DEFAULT_ENCODING))
        if isinstance(config, dict):
            pass
        else:
            config = next(iter(config))
        logging_config = self.generate(handlers)
        self.aea_config[0].update(logging_config)
        write_to_file(AEA_CONFIG, self.aea_config, FileType.YAML)
        self.load()
        return logging_config


@cli.group()
def augment() -> None:
    r"""Commands for augmenting project components.

    Available Commands:

        logging: Add logging handlers to AEA configuration
        customs: Augment customs components with OpenAPI3 handlers
    """


@augment.command()
@click.argument("handlers", nargs=-1, type=click.Choice(HANDLERS.keys()), required=True)
def logging(handlers) -> None:
    r"""Augment AEA logging configuration with additional handlers.

    Required Parameters:

        handlers: One or more handlers to add (console, http, logfile)

    Usage:

        Add console handler:

        adev augment logging console


        Add multiple handlers:

        adev augment logging console http logfile


    Notes
    -----
        - Modifies aea-config.yaml logging configuration
        - Available handlers:
            - console: Rich console output
            - http: HTTP POST logging to server
            - logfile: File-based logging
        - Each handler can be configured via environment variables

    """
    logger.info(f"Augmenting logging with handlers: {handlers}")
    logging_scaffolder = LoggingScaffolder()
    logging_scaffolder.scaffold(handlers)
    logger.info("Logging scaffolded.")


class ConnectionScaffolder(BaseScaffolder):
    """ConnectionScaffolder."""

    def generate(self, connections: list) -> list[tuple[str, str]]:
        """Generate connections."""
        self.logger.info(f"Generating connection config for: {connections}")
        if not connections:
            msg = "No connections provided"
            raise ValueError(msg)
        if connections == ["all"]:
            connections = CONNECTIONS
        for connection in connections:
            if connection not in CONNECTIONS:
                msg = f"Connection '{connection}' not found"
                raise ValueError(msg)
        return [CONNECTIONS[c] for c in connections]

    def scaffold(self, connections: list) -> None:
        """Scaffold connection."""
        connections = self.generate(connections)
        for connection, config in connections:
            self.aea_config[0]["connections"].append(connection)
            if config:
                self.aea_config.append(config)

        write_to_file(AEA_CONFIG, self.aea_config, FileType.YAML)
        self.load()


@augment.command()
@click.argument("connections", nargs=-1, type=click.Choice(CONNECTIONS), required=True)
def connection(connections) -> None:
    """Augment an AEA configuration with connections."""
    logger.info(f"Augmenting agent connections: {connections}")
    connection_scaffolder = ConnectionScaffolder()
    connection_scaffolder.scaffold(connections)
    logger.info("Connections scaffolded.")


@augment.command()
@click.argument("component_type", type=click.Choice(["openapi3"]))
@click.option("--auto-confirm", is_flag=True, default=False, help="Auto confirm the augmentation")
@click.option(
    "--use-daos",
    is_flag=True,
    default=False,
    help="Augment OpenAPI3 handlers with Data Access Objects (DAOs)",
)
@click.pass_context
def customs(ctx, component_type, auto_confirm, use_daos):
    """Augment a customs component with generated code.

    Usage:
    ```
    adev augment customs openapi3
    ```

    With Data Access Object integration:
    ```
    adev augment customs openapi3 --use-daos
    ```

    Features:

    - Generates handlers for each OpenAPI operation
    - Creates dialogue classes for request/response handling
    - Optionally adds Data Access Object integration
    - Includes error handling and logging

    """
    logger = ctx.obj["LOGGER"]
    logger.info(f"Augmenting {component_type} component")
    verbose = ctx.obj["VERBOSE"]

    if not Path("component.yaml").exists():
        logger.error("component.yaml not found in the current directory.")
        return

    customs_config = read_from_file(Path("component.yaml"), FileType.YAML)
    if customs_config is None:
        logger.error("Error: customs_config is None. Unable to process.")
        return

    api_spec_path = customs_config.get("api_spec")
    if not api_spec_path:
        logger.error("api_spec key not found in component.yaml")
        return

    component_author = customs_config.get("author")
    component_name = customs_config.get("name")
    public_id = PublicId(component_author, component_name.split(":")[0])

    scaffolder = (
        HandlerScaffoldBuilder()
        .create_scaffolder(
            api_spec_path, public_id, logger, verbose, new_skill=False, auto_confirm=auto_confirm, use_daos=use_daos
        )
        .build()
    )

    handler_code = scaffolder.generate_handler()

    handler_path = Path("handlers.py")
    if handler_path.exists():
        existing_handler_code = read_from_file(handler_path, FileType.PYTHON)

        if existing_handler_code != handler_code:
            diff = difflib.unified_diff(
                existing_handler_code.splitlines(keepends=True),
                handler_code.splitlines(keepends=True),
                fromfile="existing",
                tofile="new",
            )
            logger.info("Differences in handlers.py:")
            logger.info("".join(diff))

            if not auto_confirm:
                confirm = click.confirm("Do you want to update handlers.py with these changes?")
                if not confirm:
                    logger.info("Exiting.")
                    return

    write_to_file(handler_path, handler_code, FileType.PYTHON)
    logger.info(f"Handler code written to {handler_path}")

    scaffolder.create_dialogues()
    if use_daos:
        scaffolder.create_exceptions()
    logger.info("OpenAPI3 scaffolding completed successfully.")


@augment.command()
@click.argument("spec_file", type=click.Path(exists=True))
@click.argument("skill_public_id", type=PublicId.from_str, required=True)
@click.option("--auto-confirm", is_flag=True, default=False, help="Auto confirm the augmentation")
@click.option("--verbose", is_flag=True, default=False, help="Verbose output")
@click.option("--force", is_flag=True, default=False, help="Force the augmentation")
@click.option("--publish/--no-publish", is_flag=True, default=False, help="Publish the skill to the registry")
def skill_from_fsm(
    spec_file: str, skill_public_id: PublicId, auto_confirm: bool, verbose: bool, force: bool, publish: bool
):
    """Augment a skill with a new handler.

    Required Parameters:

        spec_file: Path to the FSM specification file

        skill_public_id: Public ID of the skill to augment

    Optional Parameters:

        auto_confirm (--auto-confirm): Auto confirm the augmentation

        verbose (--verbose): Verbose output
        force (--force): Force the augmentation
    Usage:

        adev augment skill_from_fsm fsm_spec.yaml author/skill_name:0.1.0

    """

    if not Path(AEA_CONFIG).exists():
        msg = f"File {AEA_CONFIG} not found. Please run this command from an agent."
        logger.error(msg)
        sys.exit(1)

    skill_dir = Path(f"{SKILLS}/{skill_public_id.name}")
    behaviour_path = skill_dir / "behaviours.py"
    config, *_overrides = load_autonolas_yaml(PackageType.SKILL, skill_dir)

    if config.get("author") != skill_public_id.author or config.get("name") != skill_public_id.name:
        msg = f"Skill {skill_public_id} not found in the current project."
        logger.error(msg)
        raise OperationError(msg)

    if behaviour_path.exists():
        logger.error(f"Behaviours file already exists for skill {skill_public_id}.")
        if not force:
            logger.error("Use --force to overwrite.")
            sys.exit(1)
        behaviour_path.unlink()

    logger.info("Augmenting skill with a new handler.")
    scaffolder = BehaviourScaffolder(
        spec_file,
        behaviour_type=BehaviourTypes.simple_fsm,
        logger=logger,
        verbose=verbose,
        auto_confirm=auto_confirm,
    )

    output = scaffolder.scaffold()
    write_to_file(behaviour_path, output, FileType.PYTHON)
    class_name = f"{snake_to_camel(scaffolder.fsm_spec.label).capitalize()}{FSM_END_CLASS_NAME}"
    skill_yaml = read_from_file(skill_dir / DEFAULT_SKILL_CONFIG_FILE, FileType.YAML)
    if "behaviours" not in skill_yaml:
        skill_yaml["behaviours"] = {}
    skill_yaml["behaviours"]["main"] = {
        "args": {},
        "class_name": class_name,
    }
    write_to_file(skill_dir / DEFAULT_SKILL_CONFIG_FILE, skill_yaml, FileType.YAML)
    logger.info(f"Skill.yaml updated: {skill_dir / DEFAULT_SKILL_CONFIG_FILE}")
    logger.info(f"Skill successfully augmented: {skill_dir / DEFAULT_SKILL_CONFIG_FILE}")

    if publish:
        logger.info("Publishing agent and skill to the registry.")
        config, *_overrides = load_autonolas_yaml(PackageType.AGENT, Path())
        agent_public_id = PublicId.from_str(f"{config['author']}/{config['agent_name']}:{config['version']}")
        task = Task(command=f"adev publish {agent_public_id}").work()

        if task.is_failed:
            logger.error(f"Error publishing skill: {task.output}")
            sys.exit(1)
        logger.info(f"Skill published successfully! : {skill_public_id}")
        logger.info(f"Agent published successfully! : {agent_public_id}")


if __name__ == "__main__":
    cli()  # pylint: disable=no-value-for-parameter
