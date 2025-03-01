"""Command."""

import sys
import shutil
from pathlib import Path
from textwrap import dedent

import yaml
import rich_click as click
from aea.configurations.base import PublicId, PackageId, PackageType
from aea.configurations.constants import PACKAGES, SERVICES, DEFAULT_SERVICE_CONFIG_FILE

from auto_dev.base import build_cli
from auto_dev.utils import get_logger, load_autonolas_yaml
from auto_dev.constants import DEFAULT_ENCODING, DEFAULT_IPFS_HASH
from auto_dev.exceptions import UserInputError
from auto_dev.scaffolder import BasePackageScaffolder
from auto_dev.workflow_manager import Task
from auto_dev.services.runner.runner import DEFAULT_VERSION, DevAgentRunner
from auto_dev.services.package_manager.index import PackageManager


JINJA_SUFFIX = ".jinja"

logger = get_logger()

cli = build_cli(plugins=False)
CONVERSION_COMPLETE_MSG = "Conversion complete. Service is ready! 🚀"


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
    """Config for the agent service convert cli.


    agent_public_id: Public ID of the source agent.
    service_public_id: Public ID for the target service.

    """

    package_type = SERVICES

    def __init__(self, agent_public_id: PublicId, service_public_id: PublicId):
        self.agent_public_id = agent_public_id
        self.service_public_id = service_public_id

        self.agent_runner = DevAgentRunner(self.agent_public_id, verbose=True, force=True, logger=logger)
        self.validate()
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
        if not self.agent_runner.agent_package_path.exists():
            msg = f"Agent directory {self.agent_runner.agent_package_path} does not exist."
            raise UserInputError(msg)

        agent_config, *_ = load_autonolas_yaml(
            package_type=PackageType.AGENT, directory=self.agent_runner.agent_package_path
        )
        if self.agent_public_id.author != agent_config["author"]:
            msg = (
                f"Author {self.agent_public_id.author} does not match the author in the agent: {agent_config['author']}"
            )
            raise UserInputError(msg)

    def generate(self, force: bool = False, number_of_agents: int = 1):
        """Convert from agent to service."""
        self.check_if_service_exists(
            force,
        )
        agent_config, *overrides = load_autonolas_yaml(
            package_type=PackageType.AGENT, directory=self.agent_runner.agent_package_path
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
        test_data = dedent("""
        \"\"\"Tests for the service.\"\"\"

        def test_service():
            \"\"\"Test the service.\"\"\"
            assert True
        """)

        test_path = code_dir / "tests"
        test_path.mkdir(parents=True, exist_ok=True)
        test_init_path = test_path / "__init__.py"
        test_init_path.write_text(
            dedent("""
        \"\"\"Tests for the service.\"\"\"
        """),
            DEFAULT_ENCODING,
        )

        test_path /= "test_service.py"
        test_path.write_text(test_data, DEFAULT_ENCODING)

        init_path = code_dir / "__init__.py"
        init_path.write_text(
            dedent("""
        \"\"\"Service package.\"\"\"
        """),
            DEFAULT_ENCODING,
        )

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
    agent_public_id: PublicId,
    service_public_id: PublicId,
    number_of_agents: int = 1,
    force: bool = False,
) -> None:
    """Convert an autonomous agent into a deployable service.

    Required Parameters:

        agent_public_id: Public ID of the source agent

        service_public_id: Public ID for the target service

    Optional Parameters:

        number_of_agents (-n): Number of agents to include in the service

        force (-f): Force overwrite if service exists

    Notes
    -----
    The agent must exist in the agent registry. The service must not exist unless force=True.

    The function will validate these prerequisites before proceeding.

    Exceptions are handled by the underlying ConvertCliTool class.

    Example usage:

        adev convert agent-to-service author/some_agent author/some_finished_service

    """
    for public_id in [agent_public_id, service_public_id]:
        if Path(public_id.name).exists() and not force:
            logger.error(f"Conversion directory `{public_id.name}` already exists. Please remove it before converting.")
            sys.exit(1)
    service_public_id = PublicId(
        author=service_public_id.author,
        name=service_public_id.name,
        version=DEFAULT_VERSION,
        package_hash=DEFAULT_IPFS_HASH,
    )
    logger.info(f"Converting agent {agent_public_id} to service {service_public_id}.")
    converter = ConvertCliTool(agent_public_id, service_public_id)
    converter.generate(number_of_agents=number_of_agents, force=force)
    logger.info(CONVERSION_COMPLETE_MSG)
    logger.info("Service dependencies locked successfully.")
    package_manager = PackageManager(
        verbose=False,
    )
    package_manager.add_to_packages(
        dev_packages=[
            PackageId(
                package_type=PackageType.SERVICE,
                public_id=PublicId(
                    author=service_public_id.author,
                    name=service_public_id.name,
                    version=DEFAULT_VERSION,
                    package_hash=DEFAULT_IPFS_HASH,
                ),
            )
        ],
        third_party_packages=[],
    )
    logger.info("Service added to package manager.")
    if Task(command="autonomy packages lock").work().is_failed:
        logger.warning("Service dependencies could not be locked. Please check the logs.")

    logger.info("Service is ready! 🚀")
