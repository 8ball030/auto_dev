"""Service for handling component dependencies."""

from typing import Dict, Set
from pathlib import Path
from auto_dev.utils import load_autonolas_yaml


class DependencyBuilder:
    """Class to handle building dependency trees for components."""

    def __init__(self, component_path: Path | str, component_type: str):
        """Initialize the dependency builder.
        
        Args:
            component_path: Path to the component directory
            component_type: Type of the component (skill, protocol, etc.)
        """
        self.component_path = Path(component_path)
        self.component_type = component_type
        self.dependencies: Dict[str, Set[str]] = {}

    def process_dependencies_field(self, config_deps: dict) -> None:
        """Process the dependencies field of a component config.
        
        Args:
            config_deps: Dependencies configuration from component config
        """
        for dep_type, deps in config_deps.items():
            if dep_type not in self.dependencies:
                self.dependencies[dep_type] = set()
            self.dependencies[dep_type].update(deps)

    def process_component_field(self, field_type: str, field_deps: list) -> None:
        """Process a component field (protocols, contracts, etc) from config.
        
        Args:
            field_type: Type of the component field
            field_deps: List of dependencies for this field
        """
        if field_type not in self.dependencies:
            self.dependencies[field_type] = set()
        self.dependencies[field_type].update(field_deps)

    def build(self) -> Dict[str, Set[str]]:
        """Build dependency tree for the component.

        Returns:
            Dictionary mapping dependency types to sets of dependencies
        """
        try:
            config = load_autonolas_yaml(self.component_type, self.component_path)[0]
            dependency_fields = ["dependencies", "protocols", "contracts", "connections", "skills"]

            for field in dependency_fields:
                if field not in config:
                    continue

                if field == "dependencies":
                    self.process_dependencies_field(config[field])
                else:
                    field_type = field[:-1]  # Remove 's' from end
                    self.process_component_field(field_type, config[field])

            return self.dependencies
        except (FileNotFoundError, ValueError):
            return {}


def build_dependency_tree_for_component(component_path: Path | str, component_type: str) -> Dict[str, Set[str]]:
    """Build dependency tree for a component.

    Args:
        component_path: Path to the component directory
        component_type: Type of the component (skill, protocol, etc.)

    Returns:
        Dictionary mapping dependency types to sets of dependencies
    """
    builder = DependencyBuilder(component_path, component_type)
    return builder.build()