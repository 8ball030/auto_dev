# noqa: INP001
"""Test the prometheus skill."""

import json
import logging
from typing import cast
from pathlib import Path
from unittest.mock import patch

import pytest
from aea.test_tools.test_skill import BaseSkillTestCase


ROOT_DIR = Path(__file__).parent.parent.parent.parent.parent.parent


class TestSkillHandler(BaseSkillTestCase):
    """Test HttpHandler of http_echo."""

    path_to_skill = Path(ROOT_DIR, "packages", "eightballer", "skills", "prometheus")

    @pytest.mark.skip("Test not implemented")
    def test_setup(self):
        """Test the setup method of the http_echo handler."""
        self.assert_quantity_in_outbox(0)


def test_import():
    """Test the import of the skill module."""
    from packages.eightballer.skills.prometheus import behaviours  # noqa

    assert behaviours is not None
