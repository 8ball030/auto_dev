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

"""Test messages module for prometheus protocol."""

# pylint: disable=too-many-statements,too-many-locals,no-member,too-few-public-methods,redefined-builtin
from typing import List

from aea.test_tools.test_protocol import BaseProtocolMessagesTestCase

from packages.eightballer.protocols.prometheus.message import PrometheusMessage


class TestMessagePrometheus(BaseProtocolMessagesTestCase):
    """Test for the 'prometheus' protocol message."""

    MESSAGE_CLASS = PrometheusMessage

    def build_messages(self) -> List[PrometheusMessage]:  # type: ignore[override]
        """Build the messages to be used for testing."""
        return [
            PrometheusMessage(
                performative=PrometheusMessage.Performative.ADD_METRIC,
                type="some str",
                title="some str",
                description="some str",
                labels={"some str": "some str"},
            ),
            PrometheusMessage(
                performative=PrometheusMessage.Performative.UPDATE_METRIC,
                title="some str",
                callable="some str",
                value=1.0,
                labels={"some str": "some str"},
            ),
            PrometheusMessage(
                performative=PrometheusMessage.Performative.RESPONSE,
                code=12,
                message="some str",
            ),
        ]

    def build_inconsistent(self) -> List[PrometheusMessage]:  # type: ignore[override]
        """Build inconsistent messages to be used for testing."""
        return [
            PrometheusMessage(
                performative=PrometheusMessage.Performative.ADD_METRIC,
                # skip content: type
                title="some str",
                description="some str",
                labels={"some str": "some str"},
            ),
            PrometheusMessage(
                performative=PrometheusMessage.Performative.UPDATE_METRIC,
                # skip content: title
                callable="some str",
                value=1.0,
                labels={"some str": "some str"},
            ),
            PrometheusMessage(
                performative=PrometheusMessage.Performative.RESPONSE,
                # skip content: code
                message="some str",
            ),
        ]
