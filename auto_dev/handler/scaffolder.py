"""Handler scaffolder."""

import os

import yaml

from auto_dev.cli_executor import CommandExecutor
from auto_dev.commands.metadata import read_yaml_file
from auto_dev.constants import DEFAULT_ENCODING
from auto_dev.utils import get_logger

HTTP_PROTOCOL = "eightballer/http:0.1.0:bafybeia2yjjpa57ihbfru54lvq3rru5vtaomyor3fn4zz4ziiaum5yywje"

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

from packages.{author}.protocols.http.message import HttpMessage
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

HANDLER_METHOD_TEMPLATE = """
    def handle(self, message):
        "main handler method"
        url = message.url
        parts = url.split('/')
        if len(parts) == 3:
            route = parts[-2]
            id = parts[-1]
            body = json.loads(message.body.decode("utf-8"))
            return self.handle_post(route, id, body)
        elif len(parts) == 2:
            route = parts[1]
            return self.handle_get(route)
        return self.handle_unexpected_message(message)
        {unexpected_message_handler}
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


class HandlerScaffolder:
    """
    Handler Scaffolder
    """

    def __init__(self, spec_file_path: str, author: str, output: str, logger, verbose: bool = True):
        """Initialize HandlerScaffolder."""

        self.logger = logger or get_logger()
        self.verbose = verbose
        self.author = author
        self.output = output
        self.spec_file_path = spec_file_path
        self.logger.info(f"Read OpenAPI specification: {spec_file_path}")

    def generate(self) -> None:
        """Generate handler."""

        skill_cmd = f"aea scaffold skill {self.output}".split(" ")
        if not CommandExecutor(skill_cmd).execute(verbose=self.verbose):
            raise ValueError("Failed to scaffold skill.")

        openapi_spec = read_yaml_file(self.spec_file_path)
        handler_methods = []

        for path, path_spec in openapi_spec.get('paths', {}).items():
            for method, operation in path_spec.items():  # noqa
                method_name: str = f"handle_{method.lower()}_{path.lstrip('/').replace('/', '_').replace('{', '').replace('}', '')}"  # noqa
                params = []
                if "{" in path:
                    params.append("id")
                if method.lower() in ["post", "put", "patch"]:
                    params.append("body")

                param_str: str = ", ".join(["self"] + params)

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

        handler_code: str = HANDLER_HEADER_TEMPLATE.format(
            author=self.author, skill_name=openapi_spec["info"]["title"].replace(" ", "_")
        )

        main_handler: str = f"""
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

            handler_method = getattr(self, f"handle_{{method.lower()}}_{{path.lstrip('/').replace('/', '_').replace('{', '').replace('}', '')}}", None)

            if handler_method:
                kwargs = {{'body': body}} if method.lower() in ['post', 'put', 'patch'] else {{}}
                if '{{' in path:
                    kwargs['id'] = id
                return handler_method(**kwargs)

            return self.handle_unexpected_message(message)

    {all_methods}

    {UNEXPECTED_MESSAGE_HANDLER_TEMPLATE}
    """

        handler_code += main_handler
        return handler_code

    def save_handler(self, path, content):
        """Save handler to file."""
        with open(path, "w", encoding=DEFAULT_ENCODING) as f:
            try:
                f.write(content)
            except Exception as e:
                raise ValueError(f"Error writing to file: {e}") from e

    def update_skill_yaml(self, file):
        """
        Update the skill.yaml file
        """
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

    def move_and_update_my_model(self):
        """
        Reads in the my_model.py file and updates it.
        We replace the name MyModel with the name Strategy.
        """
        with open("my_model.py", "r", encoding=DEFAULT_ENCODING) as f:
            strategy_code: str = f.read()
        strategy_code = strategy_code.replace("MyModel", "Strategy")

        os.remove("my_model.py")

        strategy_file = "strategy.py"
        with open(strategy_file, "w", encoding=DEFAULT_ENCODING) as f:
            f.write(strategy_code)

    def remove_behaviours(self):
        """
        Remove the behaviours
        """
        os.remove("behaviours.py")

    def create_dialogues(self):
        """
        Create the dialogues
        """
        dialogues_file = "dialogues.py"
        with open(dialogues_file, "w", encoding=DEFAULT_ENCODING) as f:
            f.write(DIALOGUES_CODE)
