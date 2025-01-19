"""DAOScaffolder class is responsible for scaffolding DAO classes and test scripts."""

import json
from typing import Any, Optional
from pathlib import Path
from collections import defaultdict

import yaml
from jinja2 import Environment, FileSystemLoader
from aea.configurations.base import PublicId

from auto_dev.enums import FileType
from auto_dev.utils import write_to_file, camel_to_snake, read_from_file, validate_openapi_spec
from auto_dev.constants import JINJA_TEMPLATE_FOLDER
from auto_dev.dao.generator import DAOGenerator
from auto_dev.dao.dummy_data import generate_dummy_data, generate_single_dummy_data, generate_aggregated_dummy_data


class DAOScaffolder:
    """DAOScaffolder class is responsible for scaffolding DAO classes and test scripts."""

    def __init__(self, logger: Any, verbose: bool, auto_confirm: bool, public_id: PublicId):
        self.logger = logger
        self.verbose = verbose
        self.auto_confirm = auto_confirm
        self.public_id = public_id
        self.env = Environment(
            loader=FileSystemLoader(Path(JINJA_TEMPLATE_FOLDER, "dao")),
            autoescape=True,
            lstrip_blocks=True,
            trim_blocks=True,
        )
        self.component_yaml = Path.cwd() / "component.yaml"
        self.component_data = None
        self.public_id = None

    def scaffold(self) -> None:
        """Scaffold DAO classes and test scripts."""
        try:
            self.logger.info("Starting DAO scaffolding process")
            self.component_data = self._load_component_yaml()
            if not self.component_data:
                msg = "Failed to load component data"
                raise ValueError(msg)

            api_spec_path = self._get_api_spec_path(self.component_data)
            api_spec = self._load_and_validate_api_spec(api_spec_path)

            schemas = api_spec.get("components", {}).get("schemas", {})
            persistent_schemas = [schema for schema, details in schemas.items() if details.get("x-persistent")]

            if persistent_schemas:
                self.logger.info("Found schemas with x-persistent tag:")
                for schema in persistent_schemas:
                    self.logger.info(f"  - {schema}")
                user_input = input("Use these x-persistent schemas for scaffolding? (y/n): ").lower().strip()
            else:
                persistent_schemas = self.identify_persistent_schemas(api_spec)
                self.logger.info("Identified persistent schemas:")
                for schema in persistent_schemas:
                    self.logger.info(f"  - {schema}")
                user_input = input("Use these identified persistent schemas for scaffolding? (y/n): ").lower().strip()

            if user_input != "y":
                self.logger.info("Exiting scaffolding process.")
                return

            # Filter models to only include persistent schemas
            models = {k: v for k, v in schemas.items() if k in persistent_schemas}
            paths = api_spec.get("paths", {})

            aggregated_dummy_data = self._generate_aggregated_dummy_data(models)
            test_dummy_data = self._generate_single_dummy_data(models)

            dao_classes = self._generate_dao_classes(models, paths)
            self._generate_and_save_test_script(dao_classes, test_dummy_data)

            self._save_aggregated_dummy_data(aggregated_dummy_data)
            self._save_dao_classes(dao_classes)

            self._generate_and_save_init_file(dao_classes)

            base_dao_template = self.env.get_template("base_dao.jinja")
            base_dao_content = base_dao_template.render()
            self._save_base_dao(base_dao_content)

            self.logger.info("DAO scaffolding and test script generation completed successfully.")
        except Exception as e:
            self.logger.exception(f"DAO scaffolding failed: {e!s}")
            raise

    def _load_component_yaml(self) -> dict[str, Any]:
        try:
            if not self.component_yaml.exists():
                msg = f"component.yaml not found in the current directory: {self.component_yaml}"
                raise FileNotFoundError(msg)
            return read_from_file(self.component_yaml, FileType.YAML)
        except yaml.YAMLError as e:
            self.logger.exception(f"Error parsing component YAML: {e!s}")
            raise
        except OSError as e:
            self.logger.exception(f"Error reading component YAML file: {e!s}")
            raise

    def _get_api_spec_path(self, component_data: dict[str, Any]) -> str:
        api_spec_path = component_data.get("api_spec")
        if not api_spec_path:
            msg = "No 'api_spec' key found in the component.yaml file."
            raise ValueError(msg)
        return api_spec_path

    def _load_and_validate_api_spec(self, api_spec_path: str) -> dict[str, Any]:
        try:
            api_spec_path = Path(api_spec_path)
            self.logger.info(f"Attempting to load API spec from: {api_spec_path}")

            if not api_spec_path.exists():
                msg = f"API spec file not found: {api_spec_path}"
                raise FileNotFoundError(msg)

            with api_spec_path.open("r") as f:
                if api_spec_path.suffix.lower() in {".yaml", ".yml"}:
                    self.logger.info("Detected YAML file, parsing as YAML")
                    api_spec = yaml.safe_load(f)
                else:
                    self.logger.info("Attempting to parse as JSON")
                    api_spec = json.load(f)

            self.logger.info("Successfully loaded API spec, validating...")

            if "components" not in api_spec or "schemas" not in api_spec["components"]:
                msg = "OpenAPI spec does not contain explicit models in 'components/schemas'."
                self.logger.error(msg)
                raise ValueError(msg)

            if not validate_openapi_spec(api_spec, self.logger):
                raise SystemExit(1)

            return api_spec

        except yaml.YAMLError as e:
            self.logger.exception(f"Error parsing API spec YAML: {e!s}")
            raise
        except json.JSONDecodeError as e:
            self.logger.exception(f"Error parsing API spec JSON: {e!s}")
            raise
        except FileNotFoundError as e:
            self.logger.exception(str(e))
            raise
        except Exception as e:
            self.logger.exception(f"Unexpected error loading or validating API spec: {e!s}")
            raise

    def _generate_dao_classes(self, models: dict[str, Any], paths: dict[str, Any]) -> dict[str, str]:
        try:
            dao_generator = DAOGenerator(
                models,
                paths,
                self.component_data,
                author_name=self.component_data.get("author"),
                package_name=self.component_data.get("name"),
            )
            return dao_generator.generate_dao_classes()
        except Exception as e:
            self.logger.exception(f"Error generating DAO classes: {e!s}")
            raise

    def _generate_aggregated_dummy_data(self, models: dict[str, Any]) -> dict[str, Any]:
        try:
            return generate_aggregated_dummy_data(models)
        except Exception as e:
            self.logger.exception(f"Error generating aggregated dummy data: {e!s}")
            raise

    def _generate_dummy_data(self, models: dict[str, Any]) -> dict[str, Any]:
        try:
            return generate_dummy_data(models)
        except Exception as e:
            self.logger.exception(f"Error generating dummy data: {e!s}")
            raise

    def _generate_single_dummy_data(self, models: dict[str, Any]) -> dict[str, Any]:
        try:
            return {model_name: generate_single_dummy_data(model_schema) for model_name, model_schema in models.items()}
        except Exception as e:
            self.logger.exception(f"Error generating single dummy data: {e!s}")
            raise

    def _output_results(self, dao_classes: dict[str, str], dummy_data: dict[str, Any]) -> None:
        if self.verbose:
            self.logger.info("Generated DAO classes:")
            for class_name, class_code in dao_classes.items():
                self.logger.info(f"\n{class_name}:\n{class_code}")

            self.logger.info("\nGenerated dummy data for tests:")
            self.logger.info(json.dumps(dummy_data, indent=2))

    def _save_aggregated_dummy_data(self, aggregated_dummy_data: dict[str, Any]) -> None:
        try:
            dao_dir = Path("daos")
            dao_dir.mkdir(parents=True, exist_ok=True)
            json_file_path = dao_dir / "aggregated_data.json"
            write_to_file(json_file_path, aggregated_dummy_data, FileType.JSON, indent=2)
            self.logger.info(f"Saved aggregated dummy data JSON: {json_file_path}")
        except OSError as e:
            self.logger.exception(f"Error saving aggregated dummy data: {e!s}")
            raise

    def _save_dao_classes(self, dao_classes: dict[str, str]) -> None:
        try:
            dao_dir = Path("daos")
            dao_dir.mkdir(parents=True, exist_ok=True)
            for class_name, class_code in dao_classes.items():
                snake_case_name = camel_to_snake(class_name[:-3]) + "_dao"
                file_path = dao_dir / f"{snake_case_name}.py"
                write_to_file(file_path, class_code, FileType.PYTHON)
                self.logger.info(f"Saved DAO class: {file_path}")
        except OSError as e:
            self.logger.exception(f"Error saving generated files: {e!s}")
            raise

    def _save_base_dao(self, content: str) -> None:
        try:
            dao_dir = Path("daos")
            dao_dir.mkdir(parents=True, exist_ok=True)
            file_path = dao_dir / "base_dao.py"
            write_to_file(file_path, content, FileType.PYTHON)
            self.logger.info(f"Saved BaseDAO class: {file_path}")
        except OSError as e:
            self.logger.exception(f"Error saving BaseDAO class: {e!s}")
            raise

    def _generate_and_save_test_script(self, dao_classes: dict[str, str], test_dummy_data: dict[str, Any]) -> None:
        model_names = [class_name[:-3] for class_name in dao_classes.keys()]
        dao_file_names = [camel_to_snake(model_name) + "_dao" for model_name in model_names]
        test_script = self._generate_test_script(model_names, dao_file_names, test_dummy_data)
        self._save_test_script(test_script)

    def _generate_test_script(
        self, model_names: list[str], dao_file_names: list[str], test_dummy_data: dict[str, Any]
    ) -> str:
        template = self.env.get_template("test_dao.jinja")
        return template.render(
            model_names=model_names,
            dao_file_names=dao_file_names,
            dummy_data=test_dummy_data,
            author_name=self.component_data.get("author"),
            package_name=self.component_data.get("name"),
        )

    def _save_test_script(self, test_script: str) -> None:
        test_script_path = Path("tests/test_dao.py")
        test_script_path.parent.mkdir(parents=True, exist_ok=True)
        write_to_file(test_script_path, test_script, FileType.PYTHON)
        self.logger.info(f"Test script saved to: {test_script_path}")

    def _generate_and_save_init_file(self, dao_classes: dict[str, str]) -> None:
        try:
            model_names = [class_name[:-3] for class_name in dao_classes.keys()]
            file_names = [camel_to_snake(model) for model in model_names]
            model_file_pairs = list(zip(model_names, file_names, strict=False))
            init_template = self.env.get_template("__init__.jinja")
            init_content = init_template.render(model_file_pairs=model_file_pairs)
            dao_dir = Path("daos")
            init_file_path = dao_dir / "__init__.py"
            write_to_file(init_file_path, init_content, FileType.PYTHON)
            self.logger.info(f"Generated and saved __init__.py: {init_file_path}")
        except Exception as e:
            self.logger.exception(f"Error generating and saving __init__.py: {e!s}")
            raise

    def identify_persistent_schemas(self, api_spec: dict[str, Any]) -> list[str]:
        """Identify persistent schemas in the API spec."""
        schemas = api_spec.get("components", {}).get("schemas", {})
        schema_usage = defaultdict(set)

        self._analyze_paths(api_spec, schema_usage, schemas)

        return [schema for schema, usage in schema_usage.items() if "response" in usage or "nested_request" in usage]

    def _analyze_paths(self, api_spec: dict[str, Any], schema_usage: dict[str, set], schemas: dict[str, Any]) -> None:
        for path_details in api_spec.get("paths", {}).values():
            for method_details in path_details.values():
                self._analyze_method(method_details, schema_usage, schemas)

    def _analyze_method(
        self, method_details: dict[str, Any], schema_usage: dict[str, set], schemas: dict[str, Any]
    ) -> None:
        if "requestBody" in method_details:
            self._analyze_content(method_details["requestBody"].get("content", {}), "request", schema_usage, schemas)

        for response_details in method_details.get("responses", {}).values():
            self._analyze_content(response_details.get("content", {}), "response", schema_usage, schemas)

    def _analyze_content(
        self, content: dict[str, Any], usage_type: str, schema_usage: dict[str, set], schemas: dict[str, Any]
    ) -> None:
        for media_details in content.values():
            schema = media_details.get("schema", {})
            if schema.get("type") == "array":
                self._analyze_schema(schema.get("items", {}), usage_type, schema_usage, schemas)
            else:
                self._analyze_schema(schema, usage_type, schema_usage, schemas)

    def _analyze_schema(
        self, schema: dict[str, Any], usage_type: str, schema_usage: dict[str, set], schemas: dict[str, Any]
    ) -> None:
        schema_name = self._process_schema(schema)
        if schema_name:
            schema_usage[schema_name].add(usage_type)
            self._analyze_nested_properties(schema_name, usage_type, schema_usage, schemas)

    def _analyze_nested_properties(
        self, schema_name: str, usage_type: str, schema_usage: dict[str, set], schemas: dict[str, Any]
    ) -> None:
        if "properties" in schemas.get(schema_name, {}):
            for prop in schemas[schema_name].get("properties", {}).values():
                nested_schema_name = self._process_schema(prop)
                if nested_schema_name:
                    schema_usage[nested_schema_name].add(f"nested_{usage_type}")

    def _process_schema(self, schema: dict[str, Any]) -> Optional[str]:
        if "$ref" in schema:
            return schema["$ref"].split("/")[-1]
        return None
