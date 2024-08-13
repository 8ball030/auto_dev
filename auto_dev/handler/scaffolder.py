"""Handler scaffolder."""
# ruff: noqa: E501

from pathlib import Path
import sys

import yaml
from aea.configurations.base import PublicId

from auto_dev.utils import change_dir, get_logger
from auto_dev.constants import DEFAULT_ENCODING
from auto_dev.cli_executor import CommandExecutor
from auto_dev.commands.metadata import read_yaml_file


HTTP_PROTOCOL = "eightballer/http:0.1.0:bafybeihmhy6ax5uyjt7yxppn4viqswibcs5lsjhl3kvrsesorqe2u44jcm"
HANDLER_HEADER_TEMPLATE = """
# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2024 {author}
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# ------------------------------------------------------------------------------

"This package contains a scaffold of a handler."

from typing import Optional, cast

from aea.protocols.base import Message
from aea.skills.base import Handler

from packages.eightballer.protocols.http.message import HttpMessage
from packages.{author}.skills.{skill_name}.dialogues import HttpDialogue
from packages.{author}.skills.{skill_name}.strategy import Strategy

class HttpHandler(Handler):
    \"\"\"Implements the HTTP handler.\"\"\"

    SUPPORTED_PROTOCOL = HttpMessage.protocol_id  # type: Optional[str]

    def setup(self) -> None:
        \"\"\"Set up the handler.\"\"\"
        self.strategy = cast(Strategy, self.context.strategy)

    def handle_get(self, route, id=None):
        \"\"\"handle get protocol\"\"\"
        raise NotImplementedError

    def handle_post(self, route, id, body):
        \"\"\"handle post protocol\"\"\"
        raise NotImplementedError

    def teardown(self) -> None:
        \"\"\"Tear down the handler.\"\"\"
        pass

"""


PATH_FILTER_TEMPLATE = """
        if filter == "{path}":
            return self.{method_filters}{route}(message)
"""

UNEXPECTED_MESSAGE_HANDLER_TEMPLATE = """
    def handle_unexpected_message(self, message):
        \"\"\"handler for unexpected messages\"\"\"
        self.context.logger.info("received unexpected message: {}".format(message))
        raise NotImplementedError
"""

DIALOGUES_CODE = """
# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2022 Valory AG
#   Copyright 2018-2021 Fetch.AI Limited
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# ------------------------------------------------------------------------------

# we do a backslash here like so:
\"\"\"
This module contains the classes required for dialogue management.

- DefaultDialogue: The dialogue class maintains state of a dialogue of type default and manages it.
- DefaultDialogues: The dialogues class keeps track of all dialogues of type default.
- HttpDialogue: The dialogue class maintains state of a dialogue of type http and manages it.
- HttpDialogues: The dialogues class keeps track of all dialogues of type http.


\"\"\"

from typing import Any

from aea.protocols.base import Address, Message
from aea.protocols.dialogue.base import Dialogue as BaseDialogue
from aea.skills.base import Model

from packages.eightballer.protocols.http.dialogues import (
    HttpDialogue as BaseHttpDialogue,
)
from packages.eightballer.protocols.http.dialogues import (
    HttpDialogues as BaseHttpDialogues,
)

HttpDialogue = BaseHttpDialogue


class HttpDialogues(Model, BaseHttpDialogues):
    \"\"\"The dialogues class keeps track of all dialogues.\"\"\"

    def __init__(self, **kwargs: Any) -> None:
        \"\"\"Initialize the Dialogues class.\"\"\"
        Model.__init__(self, **kwargs)

        def role_from_first_message(  # pylint: disable=unused-argument
            message: Message, receiver_address: Address
        ) -> BaseDialogue.Role:
            \"\"\"
            Infer the role of the agent from an incoming/outgoing first message.

            :param message: an incoming/outgoing first message
            :param receiver_address: the address of the receiving agent
            :return: The role of the agent
            \"\"\"
            del message, receiver_address
            return BaseHttpDialogue.Role.SERVER

        BaseHttpDialogues.__init__(
            self,
            self_address=str(self.skill_id),
            role_from_first_message=role_from_first_message,
        )

"""

MAIN_HANDLER_TEMPLATE = """
    def handle(self, message: HttpMessage) -> None:
        \"\"\"Handle incoming HTTP messages\"\"\"
        method = message.method
        url = message.url
        body = message.body

        path_parts = url.split('/')
        path = '/' + '/'.join(path_parts[1:])

        if '{{' in path:
            id_index = path_parts.index([part for part in path_parts if '{{' in part][0])
            id = path_parts[id_index]
            path = '/' + '/'.join(path_parts[1:id_index] + ['{{'+ path_parts[id_index][1:-1] + '}}'] + path_parts[id_index+1:])

        handler_method = getattr(self, f"handle_{{method.lower()}}_{{path.lstrip('/').replace('/', '_').replace('{{', '').replace('}}', '')}}", None)

        if handler_method:
            kwargs = {{'body': body}} if method.lower() in ['post', 'put', 'patch', 'delete'] else {{}}
            if '{{' in path:
                kwargs['id'] = id
            return handler_method(**kwargs)

        return self.handle_unexpected_message(message)

{all_methods}

{unexpected_message_handler}
"""


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
    """
    Handler Scaffolder
    """

    def __init__(
        self,
        config: ScaffolderConfig,
        logger,
    ):
        """Initialize HandlerScaffolder."""

        self.config = config
        self.logger = logger or get_logger()
        self.handler_code = ""

    def scaffold(self):
        """Scaffold the handler."""

        if not self.present_actions():
            return

        if self.config.new_skill:
            self.create_new_skill()

        self.generate_handler()

        skill_route = Path('vendor') / self.config.author / self.public_id.name / 'skill.yaml' if not self.config.new_skill else Path('skills') / self.config.output / 'skill.yaml'
        if not skill_route.exists():
            self.logger.error(f"Skill not found at: {skill_route}. Exiting.")
            sys.exit(1)
        with self._change_dir():
            self.save_handler(Path(self.config.output) / "handlers.py")
            self.update_skill_yaml(Path(self.config.output) / "skill.yaml")
            self.move_and_update_my_model()
            self.remove_behaviours()
            self.create_dialogues()

        self.fingerprint()
        self.aea_install()
        self.add_protocol()

    def _change_dir(self):
        return change_dir(Path("skills") / self.config.output)

    def create_new_skill(self) -> None:
        """Create a new skill."""
        skill_cmd = f"aea scaffold skill {self.config.output}".split(" ")
        if not CommandExecutor(skill_cmd).execute(verbose=self.config.verbose):
            msg = "Failed to scaffold skill."
            raise ValueError(msg)

    def generate_handler(self) -> None:
        """Generate handler."""

        if not self.config.new_skill:
            skill_path = Path("skills") / self.config.output
            if not skill_path.exists():
                self.logger.warning(f"Skill '{self.config.output}' not found in the 'skills' directory. Exiting.")

        openapi_spec = read_yaml_file(self.config.spec_file_path)
        handler_methods = []

        for path, path_spec in openapi_spec.get("paths", {}).items():
            for method, operation in path_spec.items():  # noqa
                method_name: str = (
                    f"handle_{method.lower()}_{path.lstrip('/').replace('/', '_').replace('{', '').replace('}', '')}"
                )
                params = []
                if "{" in path:
                    params.append("id")
                if method.lower() in {"post", "put", "patch", "delete"}:
                    params.append("body")

                param_str: str = ", ".join(["self", *params])

                method_code: str = f"""
    def {method_name}({param_str}):
        \"\"\"
        Handle {method.upper()} request for {path}
        \"\"\"
        # TODO: Implement {method.upper()} logic for {path}
        raise NotImplementedError
    """
                handler_methods.append(method_code)

        all_methods: str = "\n".join(handler_methods)

        self.handler_code: str = HANDLER_HEADER_TEMPLATE.format(
            author=self.config.author, skill_name=self.config.output
        )
        main_handler: str = MAIN_HANDLER_TEMPLATE.format(
            all_methods=all_methods, unexpected_message_handler=UNEXPECTED_MESSAGE_HANDLER_TEMPLATE
        )
        self.handler_code += main_handler

    def save_handler(self, path) -> None:
        """Save handler to file."""
        path = Path("handlers.py")
        with open(path, "w", encoding=DEFAULT_ENCODING) as f:
            try:
                f.write(self.handler_code)
            except Exception as e:
                msg = f"Error writing to file: {e}"
                raise ValueError(msg) from e

    def update_skill_yaml(self, file) -> None:
        """Update the skill.yaml file."""
        skill_yaml = read_yaml_file(file)

        skill_yaml["protocols"] = [HTTP_PROTOCOL]
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
        with open(dialogues_file, "w", encoding=DEFAULT_ENCODING) as f:
            f.write(DIALOGUES_CODE)

    def fingerprint(self):
        """
        Fingerprint the skill
        """
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
            raise ValueError(f"Failed to execute {install_cmd}.")

    def add_protocol(self):
        """
        Add the protocol
        """
        protocol_cmd = f"aea add protocol {HTTP_PROTOCOL}".split(" ")
        if not CommandExecutor(protocol_cmd).execute(verbose=self.config.verbose):
            raise ValueError(f"Failed to add {HTTP_PROTOCOL}.")

    def confirm_action(self, message):
        """Prompt the user for confirmation before performing an action."""
        if self.config.auto_confirm:
            self.logger.info(f"Auto confirming: {message}")
            return True
        response = input(f"{message} (y/n): ").lower().strip()
        return response in ("y", "yes")

    def present_actions(self):
        """Present the scaffold summary"""
        actions = [
            f"Generating handler based on OpenAPI spec: {self.config.spec_file_path}",
            f"Saving handler to: skills/{self.config.output}/handlers.py",
            f"Updating skill.yaml in skills/{self.config.output}/",
            f"Moving and updating my_model.py to strategy.py in: skills/{self.config.output}/",
            f"Removing behaviours.py in: skills/{self.config.output}/",
            f"Creating dialogues.py in: skills/{self.config.output}/",
            "Fingerprinting the skill",
            "Running 'aea install'",
            f"Adding HTTP protocol: {HTTP_PROTOCOL}",
        ]

        if self.config.new_skill:
            actions.insert(0, f"Creating new skill: {self.config.output}")

        self.logger.info("The following actions will be performed:")
        for i, action in enumerate(actions, 1):
            self.logger.info(f"{i}. {action}")

        if not self.config.auto_confirm:
            confirm = input("Do you want to proceed? (y/n): ").lower().strip()
            if confirm not in ("y", "yes"):
                self.logger.info("Scaffolding cancelled.")
                return False

        return True


class HandlerScaffoldBuilder:
    """Builder for HandlerScaffolder"""

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
            raise ValueError("Scaffolder not initialized. Call create_scaffolder first.")
        return HandlerScaffolder(self.config, self.logger)
