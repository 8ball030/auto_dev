"""Abstract base class for agent runners."""

from abc import ABC, abstractmethod


class AgentRunner(ABC):
    """Class to manage running an agent."""

    @abstractmethod
    def run(self) -> None:
        """Run the agent."""
        raise NotImplementedError

    @abstractmethod
    def check_exists(self) -> bool:
        """Check if the agent exists."""
        raise NotImplementedError

    @abstractmethod
    def setup(self) -> None:
        """Setup the agent."""
        raise NotImplementedError
