# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2023 eightballer
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

"""Test dialogues module for prometheus protocol."""

# pylint: disable=too-many-statements,too-many-locals,no-member,too-few-public-methods,redefined-builtin
from aea.test_tools.test_protocol import BaseProtocolDialoguesTestCase

from packages.eightballer.protocols.prometheus.message import PrometheusMessage
from packages.eightballer.protocols.prometheus.dialogues import (
    PrometheusDialogue,
    PrometheusDialogues,
)


class TestDialoguesPrometheus(BaseProtocolDialoguesTestCase):
    """Test for the 'prometheus' protocol dialogues."""

    MESSAGE_CLASS = PrometheusMessage

    DIALOGUE_CLASS = PrometheusDialogue

    DIALOGUES_CLASS = PrometheusDialogues

    ROLE_FOR_THE_FIRST_MESSAGE = PrometheusDialogue.Role.AGENT  # CHECK

    def make_message_content(self) -> dict:
        """Make a dict with message contruction content for dialogues.create."""
        return dict(
            performative=PrometheusMessage.Performative.ADD_METRIC,
            type="some str",
            title="some str",
            description="some str",
            labels={"some str": "some str"},
        )
