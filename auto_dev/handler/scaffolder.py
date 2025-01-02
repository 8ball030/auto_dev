"""Handler scaffolder."""
# ruff: noqa: E501

import re
from typing import Any
from pathlib import Path
from collections import defaultdict

import yaml
from jinja2 import Environment, FileSystemLoader
from aea.configurations.base import PublicId

from auto_dev.enums import FileType
from auto_dev.utils import change_dir, get_logger, write_to_file, camel_to_snake, validate_openapi_spec
from auto_dev.constants import DEFAULT_ENCODING, JINJA_TEMPLATE_FOLDER
from auto_dev.cli_executor import CommandExecutor
from auto_dev.commands.metadata import read_yaml_file


class ScaffolderConfig:
    """Handler Scaffolder."""

    def __init__(
        self,
        spec_file_path: str,
        public_id,
        verbose: bool = True,
        new_skill: bool = False,
        auto_confirm: bool = False,
    ):
        """Initialize HandlerScaffolder."""
        self.verbose = verbose
        self.spec_file_path = spec_file_path
        self.author = public_id.author
        self.output = public_id.name
        self.verbose = verbose
        self.new_skill = new_skill
        self.auto_confirm = auto_confirm


class HandlerScaffolder:
    """Handler Scaffolder."""

    def __init__(
        self,
        config: ScaffolderConfig,
        logger,
    ):
        """Initialize HandlerScaffolder."""

        self.config = config
        self.logger = logger or get_logger()
        self.handler_code = ""
        self.jinja_env = Environment(
            loader=FileSystemLoader(Path(JINJA_TEMPLATE_FOLDER) / "customs"),
            autoescape=False,  # noqa: S701
        )
        self.jinja_env.globals["zip"] = zip

    def scaffold(self):
        """Scaffold the handler."""

        if not self.present_actions():
            return

        if self.config.new_skill:
            self.create_new_skill()

        self.generate_handler()

        with self._change_dir():
            self.save_handler()
            self.update_skill_yaml(Path("skill.yaml"))
            self.move_and_update_my_model()
            self.remove_behaviours()
            self.create_dialogues()
            self.create_exceptions()
        self.fingerprint()
        self.aea_install()

    def _change_dir(self):
        return change_dir(Path("skills") / self.config.output)

    def create_new_skill(self) -> None:
        """Create a new skill."""
        skill_cmd = f"aea scaffold skill {self.config.output}".split(" ")
        if not CommandExecutor(skill_cmd).execute(verbose=self.config.verbose):
            msg = "Failed to scaffold skill."
            raise ValueError(msg)

    def extract_schema(self, operation, persistent_schemas):
        """Extract the schema from the operation."""
        if "responses" not in operation:
            return None

        success_response = next(
            (operation["responses"].get(code, {}) for code in ["201", "200"] if code in operation["responses"]),
            {},
        )
        content = success_response.get("content", {}).get("application/json", {})
        schema_def = content.get("schema", {})

        schema_ref = None
        if schema_def.get("type") == "array":
            schema_ref = schema_def.get("items", {}).get("$ref")
        else:
            schema_ref = schema_def.get("$ref")

        schema_name = schema_ref.split("/")[-1] if schema_ref else None
        return schema_name if schema_name in persistent_schemas else None

    def classify_post_operation(self, path, operation):
        """Classify the post operation."""
        keywords = (
            operation.get("operationId", "")
            + " "
            + operation.get("summary", "")
            + " "
            + operation.get("description", "")
        ).lower()

        if "{" in path:
            return "update"
        if any(word in keywords for word in ["create", "new"]):
            return "insert"
        if any(word in keywords for word in ["update", "modify"]):
            return "update"
        return "other"

    def generate_handler(self) -> None:
        """Generate handler."""
        openapi_spec = read_yaml_file(self.config.spec_file_path)
        if not validate_openapi_spec(openapi_spec, self.logger):
            raise SystemExit(1)

        if not all(path.startswith("/api") for path in openapi_spec.get("paths", {})):
            self.logger.error("All paths in the OpenAPI spec must start with '/api'")
            raise SystemExit(1)

        persistent_schemas = self._get_persistent_schemas(openapi_spec)
        if not self._confirm_schemas(persistent_schemas):
            raise SystemExit(1)

        handler_methods = self._generate_handler_methods(openapi_spec, persistent_schemas)
        if not handler_methods:
            self.logger.error("Error: handler_methods is None. Unable to process.")
            raise SystemExit(1)

        self.handler_code = self._generate_handler_code(
            persistent_schemas, "\n\n".join(handler_methods), self._get_path_params(openapi_spec)
        )

        if not self.handler_code:
            self.logger.error("Error: handler_code is None. Unable to process.")
            raise SystemExit(1)

        return self.handler_code

    def _get_persistent_schemas(self, openapi_spec):
        schemas = openapi_spec.get("components", {}).get("schemas", {})
        persistent_schemas = [schema for schema, details in schemas.items() if details.get("x-persistent")]
        return persistent_schemas or self.identify_persistent_schemas(openapi_spec)

    def _confirm_schemas(self, persistent_schemas):
        self.logger.info("Persistent schemas:")
        for schema in persistent_schemas:
            self.logger.info(f"  - {schema}")
        return input("Use these schemas for augmenting? (y/n): ").lower().strip() == "y"

    def _generate_handler_methods(self, openapi_spec, persistent_schemas):
        handler_methods = []
        for path, path_item in openapi_spec["paths"].items():
            for method, operation in path_item.items():
                method_name = self.generate_method_name(method, path)
                path_params = [
                    param.strip("{}") for param in path.split("/") if param.startswith("{") and param.endswith("}")
                ]
                path_params_snake_case = [camel_to_snake(param) for param in path_params]
                schema = self.extract_schema(operation, persistent_schemas)
                operation_type = "other" if method.lower() != "post" else self.classify_post_operation(path, operation)

                # Extract response information
                response_info = self._extract_response_info(operation)

                # Extract error responses
                error_responses = self._extract_error_responses(operation)

                method_code = self.jinja_env.get_template("method_template.jinja").render(
                    method_name=method_name,
                    method=method,
                    path=path,
                    path_params=path_params,
                    path_params_snake_case=path_params_snake_case,
                    schema=schema,
                    operation_type=operation_type,
                    status_code=response_info["status_code"],
                    status_text=response_info["status_text"],
                    headers=response_info["headers"],
                    error_responses=error_responses,
                )
                handler_methods.append(method_code)
        return handler_methods

    def _generate_handler_code(self, persistent_schemas, all_methods, path_params):
        schema_filenames = [camel_to_snake(schema) + "_dao" for schema in persistent_schemas]

        header = self.jinja_env.get_template("handler_header.jinja").render(
            author=self.config.author,
            skill_name=self.config.output,
            schemas=persistent_schemas,
            schema_filenames=schema_filenames,
        )
        main_handler = self.jinja_env.get_template("main_handler.jinja").render(
            all_methods=all_methods,
            unexpected_message_handler=self.jinja_env.get_template("unexpected_message_handler.jinja").render(),
            path_params=path_params[0],
            path_params_mapping=path_params[1],
        )
        return header + main_handler

    def _get_path_params(self, openapi_spec):
        path_params = set()
        path_params_mapping = {}
        for path in openapi_spec.get("paths", {}):
            for param in re.findall(r"\{(\w+)\}", path):
                snake_case_param = camel_to_snake(param)
                path_params.add(snake_case_param)
                path_params_mapping[param] = snake_case_param
        return path_params, path_params_mapping

    def generate_method_name(self, http_method, path):
        """Generate method name."""
        method_name = "handle_" + http_method.lower()
        parts = [part for part in path.strip("/").split("/") if part]
        name_parts = []
        for part in parts:
            if part.startswith("{") and part.endswith("}"):
                param_name = part.strip("{}")
                param_name = self.sanitize_identifier(param_name)
                name_parts.append("by_" + param_name)
            else:
                part_name = self.sanitize_identifier(part)
                name_parts.append(part_name)
        method_name += "_" + "_".join(name_parts)
        return method_name

    def save_handler(self) -> None:
        """Save handler to file."""
        write_to_file(Path("handlers.py"), self.handler_code, file_type=FileType.PYTHON)

    def update_skill_yaml(self, file) -> None:
        """Update the skill.yaml file."""
        skill_yaml = read_yaml_file(file)

        skill_yaml["behaviours"] = {}
        del skill_yaml["handlers"]
        skill_yaml["handlers"] = {
            "http_handler": {
                "args": {},
                "class_name": "HttpHandler",
            }
        }
        skill_yaml["models"] = {
            "strategy": {
                "args": {},
                "class_name": "Strategy",
            },
            "http_dialogues": {
                "args": {},
                "class_name": "HttpDialogues",
            },
        }

        with open(file, "w", encoding=DEFAULT_ENCODING) as f:
            yaml.safe_dump(skill_yaml, f, sort_keys=False)

    def move_and_update_my_model(self) -> None:
        """Reads in the my_model.py file and updates it.
        We replace the name MyModel with the name Strategy.
        """
        my_model_file = Path("my_model.py")
        strategy_file = Path("strategy.py")

        if my_model_file.exists():
            strategy_code = my_model_file.read_text(encoding=DEFAULT_ENCODING)
            strategy_code = strategy_code.replace("MyModel", "Strategy")

            if self.confirm_action(
                f"Are you sure you want to remove the file '{my_model_file}' and create '{strategy_file}'?"
            ):
                my_model_file.unlink()
                strategy_file.write_text(strategy_code, encoding=DEFAULT_ENCODING)
            else:
                pass

    def remove_behaviours(self) -> None:
        """Remove the behaviours.py file."""
        behaviours_file = Path("behaviours.py")
        if behaviours_file.exists():
            if self.confirm_action(f"Are you sure you want to remove the file '{behaviours_file}'?"):
                behaviours_file.unlink()
            else:
                pass
        else:
            pass

    def create_dialogues(self) -> None:
        """Create the dialogues."""
        dialogues_file = "dialogues.py"
        dialogues_template = self.jinja_env.get_template("dialogues.jinja")
        with open(dialogues_file, "w", encoding=DEFAULT_ENCODING) as f:
            f.write(dialogues_template.render())

    def fingerprint(self):
        """Fingerprint the skill."""
        skill_id = PublicId(self.config.author, self.config.output, "0.1.0")
        cli_executor = CommandExecutor(f"aea fingerprint skill {skill_id}".split())
        result = cli_executor.execute(verbose=True)
        if not result:
            msg = f"Fingerprinting failed: {skill_id}"
            raise ValueError(msg)

    def aea_install(self) -> None:
        """Install the aea."""
        install_cmd = ["aea", "install"]
        if not CommandExecutor(install_cmd).execute(verbose=self.config.verbose):
            msg = f"Failed to execute {install_cmd}."
            raise ValueError(msg)

    def confirm_action(self, message):
        """Prompt the user for confirmation before performing an action."""
        if self.config.auto_confirm:
            self.logger.info(f"Auto confirming: {message}")
            return True
        response = input(f"{message} (y/n): ").lower().strip()
        return response in {"y", "yes"}

    def create_exceptions(self) -> None:
        """Create the exceptions file."""
        exceptions_template = self.jinja_env.get_template("exceptions.jinja").render()
        write_to_file(Path("exceptions.py"), exceptions_template, file_type=FileType.PYTHON)

    def present_actions(self):
        """Present the scaffold summary."""
        actions = [
            f"Generating handler based on OpenAPI spec: {self.config.spec_file_path}",
            f"Saving handler to: skills/{self.config.output}/handlers.py",
            f"Updating skill.yaml in skills/{self.config.output}/",
            f"Moving and updating my_model.py to strategy.py in: skills/{self.config.output}/",
            f"Removing behaviours.py in: skills/{self.config.output}/",
            f"Creating dialogues.py in: skills/{self.config.output}/",
            f"Creating exceptions.py in: skills/{self.config.output}/",
            "Fingerprinting the skill",
            "Running 'aea install'",
        ]

        if self.config.new_skill:
            actions.insert(0, f"Creating new skill: {self.config.output}")

        self.logger.info("The following actions will be performed:")
        for i, action in enumerate(actions, 1):
            self.logger.info(f"{i}. {action}")

        if not self.config.auto_confirm:
            confirm = input("Do you want to proceed? (y/n): ").lower().strip()
            if confirm not in {"y", "yes"}:
                self.logger.info("Scaffolding cancelled.")
                return False

        return True

    def sanitize_identifier(self, name: str) -> str:
        """Sanitize the identifier."""
        name = camel_to_snake(name)
        name = re.sub(r"[^0-9a-zA-Z_]", "_", name)
        if name and name[0].isdigit():
            name = "_" + name
        return name.lower()

    def identify_persistent_schemas(self, api_spec: dict[str, Any]) -> list[str]:
        """Identify the persistent schemas."""
        schemas = api_spec.get("components", {}).get("schemas", {})
        schema_usage = defaultdict(set)

        def process_schema(schema: dict[str, Any], usage_type: str) -> None:
            if "$ref" in schema:
                schema_name = schema["$ref"].split("/")[-1]
                schema_usage[schema_name].add(usage_type)
                for prop in schemas.get(schema_name, {}).get("properties", {}).values():
                    process_schema(prop, f"nested_{usage_type}")
            elif schema.get("type") == "array" and "items" in schema:
                process_schema(schema["items"], usage_type)

        for path in api_spec.get("paths", {}).values():
            for method in path.values():
                if "requestBody" in method:
                    for content in method["requestBody"].get("content", {}).values():
                        process_schema(content.get("schema", {}), "request")
                for response in method.get("responses", {}).values():
                    for content in response.get("content", {}).values():
                        process_schema(content.get("schema", {}), "response")

        return [schema for schema, usage in schema_usage.items() if "response" in usage or "nested_request" in usage]

    def _extract_response_info(self, operation):
        responses = operation.get("responses", {})

        status_code = 200
        status_text = "OK"
        headers = {}

        for code, response in responses.items():
            if 200 <= int(code) < 300:
                status_code = int(code)
                status_text = response.get("description", "OK")
                headers = response.get("headers", {})
                break

        return {
            "status_code": status_code,
            "status_text": status_text,
            "headers": headers,
        }

    def _extract_error_responses(self, operation):
        responses = operation.get("responses", {})
        error_responses = {}

        error_mapping = {
            "400": ("BadRequestError", "Bad Request"),
            "401": ("UnauthorizedError", "Unauthorized"),
            "403": ("ForbiddenError", "Forbidden"),
            "404": ("NotFoundError", "Not Found"),
            "422": ("ValidationError", "Unprocessable Entity"),
        }

        for code, response in responses.items():
            if 400 <= int(code) < 600:
                error_info = error_mapping.get(code, ("Exception", response.get("description", "Error")))
                error_responses[code] = {
                    "exception": error_info[0],
                    "message": response.get("description", error_info[1]),
                    "status_text": error_info[1],
                }

        return error_responses


class HandlerScaffoldBuilder:
    """Builder for HandlerScaffolder."""

    def __init__(self):
        """Initialize HandlerScaffoldBuilder."""
        self.config = None
        self.logger = None

    def create_scaffolder(
        self,
        spec_file_path: str,
        public_id,
        logger,
        verbose: bool = True,
        new_skill: bool = False,
        auto_confirm: bool = False,
    ):
        """Initialize HandlerScaffoldBuilder."""
        self.config = ScaffolderConfig(spec_file_path, public_id, verbose, new_skill, auto_confirm)
        self.logger = logger
        return self

    def build(self) -> HandlerScaffolder:
        """Build the scaffolder."""
        if not self.config:
            msg = "Scaffolder not initialized. Call create_scaffolder first."
            raise ValueError(msg)
        return HandlerScaffolder(self.config, self.logger)
