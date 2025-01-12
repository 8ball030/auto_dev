"""Tests for the scaffold command."""

import sys
import subprocess
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, MagicMock, patch

import yaml
import pytest
from aea.cli import cli as aea_cli
from aea.configurations.base import PublicId

from auto_dev.cli import cli
from auto_dev.utils import get_logger
from auto_dev.constants import DEFAULT_ENCODING
from auto_dev.dao.scaffolder import DAOScaffolder
from auto_dev.handler.scaffolder import HandlerScaffolder, HandlerScaffoldBuilder
from auto_dev.protocols.scaffolder import read_protocol
from auto_dev.handler.openapi_models import (
    Schema,
    OpenAPI,
    PathItem,
    Response,
    MediaType,
    Operation,
    Reference,
    Components,
)


FSM_SPEC = Path("auto_dev/data/fsm/fsm_specification.yaml").absolute()


class Mockers:
    """Class containing mock objects for testing."""

    class MockRunner:
        """Mock runner for testing scaffold commands."""

        def __init__(self):
            self.return_code = 0
            self.output = ""


def get_yaml_files(directory):
    """Get all yaml files in a directory."""
    return [str(f) for f in Path(directory).glob("*.yaml")]


def get_paths_from_yaml(yaml_file):
    """Get all paths from a yaml file."""
    with open(yaml_file, encoding=DEFAULT_ENCODING) as f:
        spec = yaml.safe_load(f)

    paths = []
    for path, methods in spec.get("paths", {}).items():
        for method in methods:
            handler_name = path.replace("{", "").replace("}", "")
            handler_name = f"handle_{method.lower()}_{handler_name.lstrip('/').replace('/', '_')}"
            paths.append(handler_name)
    return paths


@pytest.mark.skip(reason="Needs chain contracts update")
@pytest.mark.parametrize("spec", [None, FSM_SPEC])
def test_scaffold_fsm_with_aea_run(cli_runner, spec, dummy_agent_tim):
    """Test scaffold base FSM upto `aea run`."""

    command = ["adev", "scaffold", "fsm"]
    if spec:
        command.extend(["--spec", str(spec)])

    dummy_agent_tim.exists()
    runner = cli_runner(command)
    result = runner.execute()
    assert runner.exit_code == 0, runner.output

    assert (Path.cwd() / "vendor" / "valory" / "skills" / "abstract_abci").exists()
    assert (Path.cwd() / "vendor" / "valory" / "skills" / "abstract_round_abci").exists()
    assert (Path.cwd() / "vendor" / "valory" / "skills" / "registration_abci").exists()
    assert (Path.cwd() / "vendor" / "valory" / "skills" / "reset_pause_abci").exists()
    assert (Path.cwd() / "vendor" / "valory" / "skills" / "termination_abci").exists()

    cmd = ["aea", "run"]
    runner = cli_runner(cmd)
    result = runner.execute()
    assert runner.exit_code == 1, runner.output
    assert "An error occurred during instantiation of connection valory" in result.output


@pytest.mark.skip(reason="Needs chain contracts update")
def test_scaffold_protocol(cli_runner, dummy_agent_tim, caplog):
    """Test scaffold protocol."""

    path = Path.cwd() / ".." / "tests" / "data" / "dummy_protocol.yaml"
    command = ["scaffold", "protocol", str(path)]
    result = cli_runner.invoke(cli, command)

    assert result.exit_code == 0, result.output
    assert f"New protocol scaffolded at {dummy_agent_tim}" in caplog.text

    protocol = read_protocol(str(path))
    original_content = path.read_text(encoding=DEFAULT_ENCODING)
    readme_path = dummy_agent_tim / "protocols" / protocol.metadata["name"] / "README.md"
    assert original_content in readme_path.read_text(encoding=DEFAULT_ENCODING)


@pytest.mark.skip(reason="Needs changes to scaffolder to handle directory structure")
def test_scaffold_handler(dummy_agent_tim, openapi_test_case):
    """Test scaffold handler."""

    openapi_file, expected_handlers = openapi_test_case
    openapi_spec_path, public_id = prepare_scaffold_inputs(openapi_file, dummy_agent_tim)

    runner = run_scaffold_command(
        openapi_spec_path=openapi_spec_path, public_id=public_id, new_skill=True, auto_confirm=True
    )

    assert runner.return_code == 0, runner.output

    skill_path = Path(dummy_agent_tim) / "skills" / public_id.name
    verify_scaffolded_files(skill_path)
    verify_handlers_content(skill_path, expected_handlers)
    verify_dynamic_handlers(openapi_spec_path, expected_handlers, openapi_file)
    verify_skill_yaml(skill_path)


def prepare_scaffold_inputs(openapi_file, dummy_agent_tim):
    """Prepare inputs for scaffold command."""
    assert Path.cwd() == Path(dummy_agent_tim)
    openapi_spec_path = f"../tests/data/openapi_examples/{openapi_file}"
    skill_name = f"skill_{openapi_file.replace('.yaml', '').replace('.yml', '')}"
    sanitized_skill_name = skill_name.replace("-", "_").replace(" ", "_")
    public_id = PublicId("dummy_author", sanitized_skill_name, "0.1.0")
    return openapi_spec_path, public_id


def run_scaffold_command(openapi_spec_path, public_id, new_skill, auto_confirm):
    """Run scaffold command."""
    logger = get_logger()
    verbose = True

    scaffolder = (
        HandlerScaffoldBuilder()
        .create_scaffolder(
            openapi_spec_path,
            public_id,
            logger,
            verbose,
            new_skill=new_skill,
            auto_confirm=auto_confirm,
        )
        .build()
    )

    scaffolder.scaffold()
    return Mockers.MockRunner()


def verify_scaffolded_files(skill_path):
    """Verify if expected files are created/modified."""
    assert not (skill_path / "behaviours.py").exists()
    assert (skill_path / "strategy.py").exists()
    assert (skill_path / "dialogues.py").exists()
    assert (skill_path / "handlers.py").exists()


def verify_handlers_content(skill_path, expected_handlers):
    """Verify content of handlers.py."""
    handlers_content = (skill_path / "handlers.py").read_text()
    assert "class HttpHandler(Handler):" in handlers_content
    for handler in expected_handlers:
        assert f"def {handler}(" in handlers_content, f"Handler method for '{handler}' not found"


def verify_dynamic_handlers(openapi_spec_path, expected_handlers, openapi_file):
    """Verify dynamically generated handlers."""
    dynamic_handlers = get_paths_from_yaml(openapi_spec_path)
    assert set(expected_handlers) == set(
        dynamic_handlers
    ), f"Mismatch between expected and dynamically generated handlers for {openapi_file}"


def verify_skill_yaml(skill_path):
    """Verify content of skill.yaml."""
    with open(skill_path / "skill.yaml", encoding=DEFAULT_ENCODING) as f:
        skill_yaml = yaml.safe_load(f)
    assert "eightballer/http:0.1.0" in skill_yaml["protocols"][0]
    assert "behaviours" in skill_yaml
    assert not skill_yaml["behaviours"]
    assert "handlers" in skill_yaml
    assert "http_handler" in skill_yaml["handlers"]
    assert "models" in skill_yaml
    assert "strategy" in skill_yaml["models"]
    assert "http_dialogues" in skill_yaml["models"]


@pytest.mark.skip(reason="Needs chain contracts update")
class TestScaffoldConnection:
    """Test scaffold connection."""

    @classmethod
    def setup_class(cls) -> None:
        """Setup class."""

        cls.protocol_id = "zarathustra/sql_crud:0.1.0"
        cls.protocol_path = "../tests/data/crud_protocol.yaml"

    def test_no_name_provided(self, cli_runner, dummy_agent_tim):
        """Test no name provided."""

        assert Path.cwd() == Path(dummy_agent_tim)

        result = cli_runner.invoke(cli, f"scaffold protocol {self.protocol_path}")
        assert result.exit_code == 0, result.output

        result = cli_runner.invoke(cli, ["scaffold", "connection"])
        assert result.exit_code == 2, result.output
        assert "Missing argument 'NAME'" in result.output

    def test_scaffold_with_spec_readme(self, cli_runner, dummy_agent_tim, caplog):
        """Test scaffold protocol specification in README."""

        result = cli_runner.invoke(cli, f"scaffold protocol {self.protocol_path}")
        assert result.exit_code == 0, result.output

        result = cli_runner.invoke(cli, ["scaffold", "connection", "my_connection", "--protocol", self.protocol_id])
        assert result.exit_code == 0, result.output
        assert f"Read protocol specification: {self.protocol_path}" in caplog.text
        assert f"New connection scaffolded at {dummy_agent_tim}" in caplog.text

    def test_scaffold_with_python(self, cli_runner, dummy_agent_tim, caplog):
        """Test scaffold with python run for correct imports."""

        result = cli_runner.invoke(cli, f"scaffold protocol {self.protocol_path}")
        assert result.exit_code == 0, result.output

        result = cli_runner.invoke(cli, ["scaffold", "connection", "my_connection", "--protocol", self.protocol_id])
        assert result.exit_code == 0, result.output
        assert f"New connection scaffolded at {dummy_agent_tim}" in caplog.text

        result = cli_runner.invoke(aea_cli, "remove-key ethereum".split())
        assert result.exit_code == 0, result.output

        result = cli_runner.invoke(aea_cli, "publish --push-missing --local".split())
        assert result.exit_code == 0, result.output

        connection_dir = Path("../packages/zarathustra/connections/my_connection")
        connection_path = connection_dir / "connection.py"
        test_connection_path = connection_dir / "tests" / "test_connection.py"

        for path in (connection_path, test_connection_path):
            result = subprocess.run([sys.executable, path], shell=True, check=True, capture_output=True)
            assert result.returncode == 0, result.stderr


class TestDAOScaffolder:
    """Test suite for DAOScaffolder."""

    @pytest.fixture
    def mock_logger(self):
        """Mock logger."""
        return Mock()

    @pytest.fixture
    def scaffolder(self, mock_logger, tmp_path):
        """Create a scaffolder instance with a temporary working directory."""
        public_id = PublicId("dummy_author", "dummy_name", "0.1.0")
        scaffolder = DAOScaffolder(mock_logger, verbose=True, auto_confirm=True, public_id=public_id)
        scaffolder.component_yaml = tmp_path / "component.yaml"
        return scaffolder

    @pytest.fixture
    def mock_api_spec(self, tmp_path):
        """Create a mock API spec file."""
        api_spec = tmp_path / "test_api.yaml"
        api_spec.write_text("""
            components:
              schemas:
                TestModel:
                  type: object
                  properties:
                    id: {type: integer}
                    name: {type: string}
            paths:
              /test:
                get:
                  responses:
                    '200':
                      content:
                        application/json:
                          schema:
                            $ref: '#/components/schemas/TestModel'
        """)
        return api_spec

    def setup_component_yaml(self, scaffolder, api_spec_path):
        """Set up the component.yaml file."""
        scaffolder.component_yaml.write_text(f"api_spec: {api_spec_path}")

    @patch("auto_dev.dao.scaffolder.validate_openapi_spec", return_value=True)
    @patch("auto_dev.dao.scaffolder.DAOGenerator")
    @patch("builtins.input", return_value="y")
    def test_scaffold(self, mock_input, mock_dao_generator, mock_validate, scaffolder, mock_api_spec):
        """Test the entire scaffolding process."""
        assert mock_input.return_value == "y"
        self.setup_component_yaml(scaffolder, mock_api_spec)

        mock_generator = Mock()
        mock_generator.generate_dao_classes.return_value = {"TestDAO": "class TestDAO:..."}
        mock_dao_generator.return_value = mock_generator

        with patch("auto_dev.dao.scaffolder.Path.mkdir"), patch("auto_dev.dao.scaffolder.write_to_file") as mock_write:
            scaffolder.scaffold()

            scaffolder.logger.info.assert_any_call("Starting DAO scaffolding process")
            mock_validate.assert_called_once()
            mock_generator.generate_dao_classes.assert_called_once()

            assert mock_write.call_count >= 3

            scaffolder.logger.info.assert_any_call("DAO scaffolding and test script generation completed successfully.")

    @patch("auto_dev.dao.scaffolder.validate_openapi_spec", return_value=False)
    def test_scaffold_invalid_api_spec(self, mock_validate, scaffolder, mock_api_spec):
        """Test scaffolding with an invalid API spec."""
        self.setup_component_yaml(scaffolder, mock_api_spec)

        with pytest.raises(SystemExit):
            scaffolder.scaffold()

        assert mock_validate.return_value is False

    def test_scaffold_missing_component_yaml(self, scaffolder):
        """Test scaffolding with a missing component.yaml file."""
        with pytest.raises(FileNotFoundError):
            scaffolder.scaffold()

    @patch("builtins.input", return_value="n")
    @patch("auto_dev.dao.scaffolder.validate_openapi_spec", return_value=True)
    def test_scaffold_user_abort(self, mock_validate, mock_input, scaffolder, tmp_path):
        """Test scaffolding process when user aborts."""

        assert mock_input.return_value == "n"
        assert mock_validate.return_value is True
        dummy_openapi_path = tmp_path / "dummy_openapi.yaml"
        dummy_openapi_path.write_text("""
openapi: 3.0.0
info:
  title: Dummy API
  version: 1.0.0
paths:
  /users:
    get:
      responses:
        '200':
          description: Successful response
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/User'
components:
  schemas:
    User:
      type: object
      properties:
        id:
          type: integer
        name:
          type: string
    """)
        self.setup_component_yaml(scaffolder, dummy_openapi_path)

        scaffolder.scaffold()
        scaffolder.logger.info.assert_any_call("Exiting scaffolding process.")


class TestHandlerScaffolder(TestCase):
    """Test suite for HandlerScaffolder."""

    def setUp(self):  # noqa: N802
        """Set up test case."""
        self.logger = Mock()
        self.scaffolder = HandlerScaffolder(config=None, logger=self.logger)

    def test_extract_schema_with_reference(self):
        """Test schema extraction with reference."""
        operation = Operation(
            responses={
                "200": Response(
                    description="OK",
                    content={
                        "application/json": MediaType(media_type_schema=Reference(ref="#/components/schemas/Item"))
                    },
                )
            }
        )
        schema_name = self.scaffolder.extract_schema(operation)
        assert schema_name == "Item"

    def test_extract_schema_with_inline_schema(self):
        """Test schema extraction with inline schema."""
        operation = Operation(
            responses={
                "200": Response(
                    description="OK",
                    content={"application/json": MediaType(media_type_schema=Schema(type="object", properties={}))},
                )
            }
        )
        schema_name = self.scaffolder.extract_schema(operation)
        assert schema_name is None

    def test_get_persistent_schemas(self):
        """Test getting persistent schemas."""
        self.scaffolder.config = Mock(use_daos=True)
        openapi_spec = OpenAPI(
            openapi="3.0.0",
            info={"title": "Test API", "version": "1.0"},
            paths={},
            components=Components(
                schemas={"Item": Schema(type="object", x_persistent=True), "NonPersistent": Schema(type="object")}
            ),
        )
        schemas = self.scaffolder.get_persistent_schemas(openapi_spec)
        assert schemas == ["Item"]

    def test_identify_persistent_schemas(self):
        """Test identifying persistent schemas."""
        openapi_spec = OpenAPI(
            openapi="3.0.0",
            info={"title": "Test API", "version": "1.0"},
            paths={
                "/items": PathItem(
                    get=Operation(
                        responses={
                            "200": Response(
                                description="OK",
                                content={
                                    "application/json": MediaType(
                                        media_type_schema=Reference(ref="#/components/schemas/Item")
                                    )
                                },
                            )
                        }
                    )
                )
            },
            components=Components(schemas={"Item": Schema(type="object"), "Ignored": Schema(type="object")}),
        )
        schemas = self.scaffolder.identify_persistent_schemas(openapi_spec)
        assert schemas == ["Item"]


class TestHandlerScaffoldBuilder(TestCase):
    """Test suite for HandlerScaffoldBuilder."""

    def test_create_scaffolder(self):
        """Test creating a scaffolder."""
        builder = HandlerScaffoldBuilder()
        public_id = PublicId(author="author", name="skill", version="0.1.0")
        scaffolder = builder.create_scaffolder(
            spec_file_path="path/to/spec.yaml",
            public_id=public_id,
            logger=None,
            verbose=True,
            new_skill=True,
            auto_confirm=False,
            use_daos=False,
        ).build()
        assert isinstance(scaffolder, HandlerScaffolder)


class TestHandlerScaffolderIntegration(TestCase):
    """Test suite for HandlerScaffolderIntegration."""

    @patch("auto_dev.handler.scaffolder.CommandExecutor")
    @patch("auto_dev.handler.scaffolder.load_openapi_spec")
    @patch("auto_dev.handler.scaffolder.HandlerScaffolder.save_handler")
    @patch("auto_dev.handler.scaffolder.HandlerScaffolder._change_dir")
    def test_scaffold_process(self, mock_change_dir, mock_save_handler, mock_load_spec, mock_cmd_executor):
        """Test scaffold process."""
        mock_cmd_executor.return_value.execute.return_value = True
        mock_load_spec.return_value = MagicMock()
        self.scaffolder = HandlerScaffolder(config=None, logger=Mock())
        self.scaffolder.config = MagicMock(new_skill=True, output="output_skill", auto_confirm=True)
        self.scaffolder.present_actions = MagicMock(return_value=True)
        self.scaffolder.create_new_skill = MagicMock()
        self.scaffolder.update_skill_yaml = MagicMock()
        self.scaffolder.move_and_update_my_model = MagicMock()
        self.scaffolder.remove_behaviours = MagicMock()
        self.scaffolder.create_dialogues = MagicMock()
        self.scaffolder.create_exceptions = MagicMock()
        self.scaffolder.fingerprint = MagicMock()
        self.scaffolder.aea_install = MagicMock()
        self.scaffolder.generate_handler = MagicMock()
        mock_change_dir.return_value = MagicMock()
        self.scaffolder.scaffold()
        self.scaffolder.present_actions.assert_called_once()
        self.scaffolder.create_new_skill.assert_called_once()
        self.scaffolder.generate_handler.assert_called_once()
        mock_save_handler.assert_called_once()
        self.scaffolder.update_skill_yaml.assert_called_once()
        self.scaffolder.move_and_update_my_model.assert_called_once()
        self.scaffolder.remove_behaviours.assert_called_once()
        self.scaffolder.create_dialogues.assert_called_once()
        self.scaffolder.create_exceptions.assert_called_once()
        self.scaffolder.fingerprint.assert_called_once()
        self.scaffolder.aea_install.assert_called_once()
