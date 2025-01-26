"""DAO generator class."""

from typing import Any, Optional

from jinja2 import Environment, FileSystemLoader

from auto_dev.utils import Path
from auto_dev.constants import JINJA_TEMPLATE_FOLDER


class DAOGenerator:
    """Generator class for DAO files."""

    def __init__(
        self,
        models: dict[str, Any],
        paths: dict[str, Any],
        component_data: dict[str, Any],
        author_name: Optional[str] = None,
        package_name: Optional[str] = None,
    ):
        self.models = models
        self.paths = paths
        self.component_data = component_data
        self.author_name = author_name
        self.package_name = package_name
        self.env = Environment(
            loader=FileSystemLoader(Path(JINJA_TEMPLATE_FOLDER, "dao")),
            autoescape=True,
            lstrip_blocks=True,
            trim_blocks=True,
        )

    def generate_dao_classes(self) -> dict[str, str]:
        """Generate DAO classes."""
        dao_classes = {}
        for model_name, model_schema in self.models.items():
            dao_classes[f"{model_name}DAO"] = self._generate_dao_class(model_name, model_schema)
        return dao_classes

    def _generate_dao_class(self, model_name: str, model_schema: dict[str, Any]) -> str:
        other_model_names = [name for name in self.models if name != model_name]
        properties = model_schema.get("properties", {})
        return self.env.get_template("dao_template.jinja").render(
            model_name=model_name,
            model_schema=model_schema,
            other_model_names=other_model_names,
            properties=properties,
            base_dao_import="from base_dao import BaseDAO",
            author=self.author_name,
            package_name=self.package_name,
        )
