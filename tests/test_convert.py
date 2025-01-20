"""
Tests for the convert command.
"""

import pytest

from auto_dev.constants import DEFAULT_AUTHOR, DEFAULT_AGENT_NAME
from auto_dev.commands.convert import ConvertCliTool


@pytest.mark.parametrize(
    "agent_public_id, service_public_id",
    [
        (f"{DEFAULT_AUTHOR}/{DEFAULT_AGENT_NAME}", "author/service:0.1.0"),
    ],
)
def test_convert_agent_to_service(dummy_agent_tim, agent_public_id, service_public_id):
    """Test the convert agent to service command."""
    assert dummy_agent_tim, "Dummy agent not created."
    convert = ConvertCliTool(agent_public_id, service_public_id)
    result = convert.from_agent_to_service()
    assert result
