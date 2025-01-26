"""Command."""

import shutil
from pathlib import Path

import yaml
import rich_click as click
from aea.configurations.base import PublicId, PackageType
from aea.configurations.constants import PACKAGES, SERVICES, DEFAULT_SERVICE_CONFIG_FILE

from auto_dev.base import build_cli
from auto_dev.utils import get_logger, load_autonolas_yaml
from auto_dev.constants import DEFAULT_ENCODING
from auto_dev.exceptions import UserInputError
from auto_dev.scaffolder import BasePackageScaffolder
from auto_dev.commands.run import AgentRunner


JINJA_SUFFIX = ".jinja"

logger = get_logger()

cli = build_cli(plugins=False)


@cli.group()
def convert() -> None:
    """Commands for converting between component types.

    Available Commands:
        agent_to_service: Convert an autonomous agent into a deployable service

    Notes
    -----
        - Handles package type conversion while preserving functionality
        - Manages dependencies and package structure automatically
        - Validates components before conversion
        - Supports Open Autonomy service standards

    """


class ConvertCliTool(BasePackageScaffolder):
    """Config for the agent servce convert cli."""

    package_type = SERVICES

    def __init__(self, agent_public_id: PublicId, service_public_id: PublicId):
        """Init the config."""
        self.agent_public_id = (
            PublicId.from_str(agent_public_id) if isinstance(agent_public_id, str) else agent_public_id
        )
        self.service_public_id = (
            PublicId.from_str(service_public_id) if isinstance(service_public_id, str) else service_public_id
        )
        self.agent_runner = AgentRunner(self.agent_public_id, verbose=True, force=True, logger=logger)
        self._post_init()

    @property
    def template_name(self):
        """Get the template name."""
        return DEFAULT_SERVICE_CONFIG_FILE + JINJA_SUFFIX

    def validate(self):
        """Validate function be called before the conversion."""
        if not self.agent_public_id:
            msg = "Agent public id is required."
            raise UserInputError(msg)
        if not self.service_public_id:
            msg = "Service public id is required."
            raise UserInputError(msg)
        if not self.agent_runner.agent_dir.exists():
            return UserInputError(f"Agent directory {self.agent_runner.agent_dir} does not exist.")
        return None

    def generate(self, force: bool = False, number_of_agents: int = 1):
        """Convert from agent to service."""
        self.check_if_service_exists(
            force,
        )
        self.validate()
        agent_config, *overrides = load_autonolas_yaml(
            package_type=PackageType.AGENT, directory=self.agent_runner.agent_dir
        )
        self.create_service(agent_config, overrides, number_of_agents)
        return True

    def create_service(self, agent_config, overrides, number_of_agents):
        """Create the service from a jinja template."""
        template = self.get_template(self.template_name)
        override_strings = yaml.safe_dump_all(overrides, default_flow_style=False, sort_keys=False)
        agent_public_id = f"{self.agent_public_id.author}/{self.agent_public_id.name}:{self.agent_runner.get_version()}"
        rendered = template.render(
            agent_public_id=agent_public_id,
            service_public_id=self.service_public_id,
            agent_config=agent_config,
            overrides=override_strings,
            number_of_agents=number_of_agents,
            autoescape=False,
        )
        code_dir = Path(PACKAGES) / self.service_public_id.author / SERVICES / self.service_public_id.name
        code_dir.mkdir(parents=True, exist_ok=True)
        code_path = code_dir / self.template_name.split(JINJA_SUFFIX)[0]
        code_path.write_text(rendered, DEFAULT_ENCODING)

    def check_if_service_exists(
        self,
        force: bool = False,
    ):
        """Check if the service exists."""
        code_path = Path(PACKAGES) / self.service_public_id.author / SERVICES / self.service_public_id.name
        if code_path.exists():
            if not force:
                msg = f"Service {self.service_public_id} already exists. Use --force to overwrite."
                raise FileExistsError(msg)
            logger.warning(f"Service {self.service_public_id} already exists. Overwriting ...")
            shutil.rmtree(code_path)
        return True


@convert.command()
@click.argument("agent_public_id", type=PublicId.from_str)
@click.argument("service_public_id", type=PublicId.from_str)
@click.option(
    "--number_of_agents", type=int, default=1, required=False, help="Number of agents to be included in the service."
)
@click.option("--force", is_flag=True, help="Force the operation.", default=False)
def agent_to_service(
    agent_public_id: PublicId, service_public_id: PublicId, number_of_agents: int = 1, force: bool = False
) -> None:
    r"""Convert an autonomous agent into a deployable service.

    Required Parameters:\n
        agent_public_id: Public ID of the source agent (author/name format)\n
        service_public_id: Public ID for the target service (author/name format)\n

    Optional Parameters:\n
        number_of_agents (-n): Number of agent instances in the service. (Default: 1)\n
        force (-f): Overwrite existing service if it exists. (Default: False)\n

    Usage:\n
        Basic conversion:\n
            adev convert agent-to-service author/my_agent author/my_service\n

        With multiple agent instances:
            adev convert agent-to-service author/my_agent author/my_service --number_of_agents 3

        Force overwrite existing:
            adev convert agent-to-service author/my_agent author/my_service --force

    Notes
    -----
        - Prerequisites:
            - Agent must exist in packages directory
            - Agent and service public IDs must be valid
        - Package Structure:
            - Creates service in packages/<author>/services/<name>
            - Follows Open Autonomy service structure
        - Configuration:
            - Copies agent configuration and dependencies
            - Sets up service-specific overrides
            - Configures number of agent instances
            - Includes network and deployment settings
        - Validation:
            - Checks agent existence and structure
            - Validates service creation path
            - Verifies configuration compatibility
        - Use --force to overwrite an existing service

    """
    logger.info(f"Converting agent {agent_public_id} to service {service_public_id}.")
    converter = ConvertCliTool(agent_public_id, service_public_id)
    converter.generate(number_of_agents=number_of_agents, force=force)
    logger.info("Conversion complete. Service is ready! 🚀")
