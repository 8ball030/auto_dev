"""
Module for the base class for the scaffolder.
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from auto_dev.constants import JINJA_TEMPLATE_FOLDER


class BasePackageScaffolder:
    """Base class for the scaffolder."""

    def _post_init(self):
        """Post init function."""
        self.env = Environment(
            loader=FileSystemLoader(Path(JINJA_TEMPLATE_FOLDER) / self.package_type), autoescape=True
        )

    def generate(self) -> None:
        """
        Scaffold the package.

        :return: None
        """
        raise NotImplementedError

    @property
    def package_type(self):
        """Get the package type."""
        raise NotImplementedError

    @property
    def template_name(self):
        """Get the template name."""
        raise NotImplementedError

    @property
    def template(self):
        """Get the template."""
        return self.env.get_template(str(Path(self.package_type) / self.template_name))
