"""
Command
"""
from contextlib import chdir
from pathlib import Path
import rich_click as click

from auto_dev.base import build_cli
from auto_dev.utils import get_logger, load_aea_config
from aea.configurations.base import PublicId

logger = get_logger()

cli = build_cli(plugins=False)


@cli.group()
def convert() -> None:
    """
    Commands to convert between an agent and a service or vice versa.

    """


class ConvertCliConfig:
    """Config for the convert cli."""

    def __init__(self, agent_public_id: PublicId, service_public_id: PublicId):
        """Init the config."""
        self.agent_public_id = agent_public_id
        self.service_public_id = service_public_id

    def from_agent_to_service(self):
        """Convert from agent to service."""
        agent_path = self._check_agent_exists()
        agent_config, *overrides = load_aea_config(agent_path)
        self._create_service(agent_config, overrides)

    def _check_agent_exists(self):
        agent_path = Path("packages") / self.agent_public_id.author / "agents" / self.agent_public_id.name
        if not agent_path.exists():
            raise FileNotFoundError(f"Agent {self.agent_public_id} not found.")
        if not (agent_path / "aea-config.yaml").exists():
            raise FileNotFoundError(f"Agent {self.agent_public_id} not found.")
        return agent_path
    
    def _create_service(self, agent_config, overrides):
        """
        Create the service from a jinja template.
        """
        


@convert.command()
@click.argument("agent_public_id", type=PublicId.from_str)
@click.argument("service_public_id", type=PublicId.from_str)
@click.option("--number_of_agents", type=int, default=1, required=False, 
                help="Number of agents to be included in the service.")
def agent_to_service(
    agent_public_id: PublicId, service_public_id: PublicId, number_of_agents: int = 1
) -> None:
    """
    Convert an agent to a service.

    args:
        AGENT_PUBLIC_ID: The public id of the agent.
        SERVICE_PUBLIC_ID: The public id of the service to be converted to.

    Example:
        adev convert AGENT_PUBLIC_ID SERVICE_PUBLIC_ID
    """
    logger.info(f"Converting agent {agent_public_id} to service {service_public_id}.")

    converter = ConvertCliConfig(agent_public_id, service_public_id)
    converter.from_agent_to_service()

    logger.info("Conversion complete. Service is ready! 🚀")
    

