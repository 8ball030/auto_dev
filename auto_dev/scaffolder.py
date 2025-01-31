"""Module for the base class for the scaffolder."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from auto_dev.constants import JINJA_TEMPLATE_FOLDER


class BasePackageScaffolder:
    """Base class for the scaffolder."""

    def _post_init(self):
        """Post init function."""
        self.template_dir = Path(JINJA_TEMPLATE_FOLDER) / self.package_type
        self.env = Environment(
            loader=FileSystemLoader(self.template_dir), autoescape=select_autoescape(["html", "xml"])
        )

    def generate(self) -> None:
        """Scaffold the package.

        This is an abstract method that must be implemented by subclasses to generate
        their specific package structure and files.

        Returns
        -------
            None: This method doesn't return anything

        Raises
        ------
            NotImplementedError: This is an abstract method that must be implemented by subclasses

        """
        raise NotImplementedError

    def validate(self):
        """Validate the package."""
        raise NotImplementedError

    @property
    def package_type(self):
        """Get the package type."""
        raise NotImplementedError

    @property
    def template_name(self):
        """Get the template name."""
        raise NotImplementedError

    def get_template(self, template_name: str):
        """Get the template."""
        return self.env.get_template(str(template_name))
