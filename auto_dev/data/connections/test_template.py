"""Template for the tests for the connection scaffolder."""
# ruff: noqa: E501

from collections import namedtuple


HEADER = """
# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright {year} {author}
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
"""

DOCSTRING = """
\"\"\"This module contains the tests of the {proper_name} connection module.\"\"\"
# pylint: skip-file
"""

IMPORTS = """
import asyncio
import logging
import pytest
from unittest.mock import MagicMock, Mock, patch

from aea.common import Address
from aea.configurations.base import ConnectionConfig
from aea.identity.base import Identity
from aea.mail.base import Envelope, Message
from aea.protocols.dialogue.base import Dialogue as BaseDialogue

from packages.{protocol_author}.protocols.{protocol_name}.dialogues import {protocol_name_camelcase}Dialogues as Base{protocol_name_camelcase}Dialogues
from packages.{protocol_author}.protocols.{protocol_name}.dialogues import {protocol_name_camelcase}Dialogue

from packages.{author}.connections.{name}.connection import (
    {name_camelcase}Connection,
)
from packages.{protocol_author}.protocols.{protocol_name}.message import {protocol_name_camelcase}Message

from packages.{author}.connections.{name}.connection import CONNECTION_ID as CONNECTION_PUBLIC_ID
"""

HELPERS = """
def envelope_it(message: {protocol_name_camelcase}Message):
    \"\"\"Envelope the message\"\"\"

    return Envelope(
        to=message.to,
        sender=message.sender,
        message=message,
    )
"""

DIALOGUES = """
class {protocol_name_camelcase}Dialogues(Base{protocol_name_camelcase}Dialogues):
    \"\"\"The dialogues class keeps track of all {name} dialogues.\"\"\"

    def __init__(self, self_address: Address, **kwargs) -> None:
        \"\"\"
        Initialize dialogues.

        :param self_address: self address
        :param kwargs: keyword arguments
        \"\"\"

        def role_from_first_message(  # pylint: disable=unused-argument
            message: Message, receiver_address: Address
        ) -> BaseDialogue.Role:
            \"\"\"Infer the role of the agent from an incoming/outgoing first message

            :param message: an incoming/outgoing first message
            :param receiver_address: the address of the receiving agent
            :return: The role of the agent
            \"\"\"
            return {protocol_name_camelcase}Dialogue.Role.{OTHER_ROLE}  # TODO: check

        Base{protocol_name_camelcase}Dialogues.__init__(
            self,
            self_address=self_address,
            role_from_first_message=role_from_first_message,
        )
"""

CONNECTION = """
class Test{name_camelcase}Connection():

    def setup(self):
        \"\"\"Initialise the test case.\"\"\"

        self.identity = Identity("dummy_name", address="dummy_address", public_key="dummy_public_key")
        self.agent_address = self.identity.address

        self.connection_id = {name_camelcase}Connection.connection_id
        self.protocol_id = {protocol_name_camelcase}Message.protocol_id
        self.target_skill_id = "dummy_author/dummy_skill:0.1.0"

        # TODO: define custom kwargs for connection
        kwargs = {{}}

        self.configuration = ConnectionConfig(
            target_skill_id=self.target_skill_id,
            connection_id={name_camelcase}Connection.connection_id,
            restricted_to_protocols={{{protocol_name_camelcase}Message.protocol_id}},
            **kwargs,
        )

        self.{name}_connection = {name_camelcase}Connection(
            configuration=self.configuration,
            data_dir=MagicMock(),
            identity=self.identity,
        )

        self.loop = asyncio.get_event_loop()
        self.loop.run_until_complete(self.{name}_connection.connect())
        self.connection_address = str({name_camelcase}Connection.connection_id)
        self._dialogues = {protocol_name_camelcase}Dialogues(self.target_skill_id)

    @pytest.mark.asyncio
    async def test_{name}_connection_connect(self):
        \"\"\"Test the connect.\"\"\"
        await self.{name}_connection.connect()
        assert not self.{name}_connection.channel.is_stopped

    @pytest.mark.asyncio
    async def test_{name}_connection_disconnect(self):
        \"\"\"Test the disconnect.\"\"\"
        await self.{name}_connection.disconnect()
        assert self.{name}_connection.channel.is_stopped

    @pytest.mark.asyncio
    async def test_handles_inbound_query(self):
        \"\"\"Test the connect.\"\"\"
        await self.{name}_connection.connect()

        msg, dialogue = self._dialogues.create(
            counterparty=str(CONNECTION_PUBLIC_ID),
            # TODO: set correct performative and message fields
            performative={protocol_name_camelcase}Message.Performative.{PERFORMATIVE},
            # ...
        )

        await self.{name}_connection.send(envelope_it(msg))
"""

TestConnectionTemplate = namedtuple(
    "TestConnectionTemplate", ["HEADER", "DOCSTRING", "IMPORTS", "HELPERS", "DIALOGUES", "CONNECTION"]
)
TEST_CONNECTION_TEMPLATE = TestConnectionTemplate(HEADER, DOCSTRING, IMPORTS, HELPERS, DIALOGUES, CONNECTION)
