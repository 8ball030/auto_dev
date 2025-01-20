"""Tests for the eject command."""

import shutil
from pathlib import Path

from auto_dev.utils import change_dir


def test_eject_metrics_skill_workflow(cli_runner):
    """Test the complete workflow of creating an agent and ejecting the metrics skill."""
    # 1. Create agent with eightballer/base template
    agent_name = "test_agent"
    create_cmd = [
        "adev",
        "-v",
        "create",
        f"new_author/{agent_name}",
        "-t",
        "eightballer/base",
        "--no-clean-up",
        "--force",
    ]
    runner = cli_runner(create_cmd)
    result = runner.execute()
    assert runner.return_code == 0

    try:
        # 2. CD into the agent directory
        agent_dir = Path(agent_name)
        assert agent_dir.exists(), f"Agent directory {agent_dir} was not created"
        # cd into the agent directory
        with change_dir(agent_dir):
            # 3. Eject the metrics skill
            eject_cmd = [
                "adev",
                "-v",
                "eject",
                "skill",
                "eightballer/metrics",
                "new_author/better_skill",
            ]
            runner.execute(eject_cmd)
            assert 'Agent "test_agent" successfully saved in packages folder.' in runner.output
            assert "Agent packages/new_author/agents/test_agent created successfully." in runner.output
            assert runner.return_code == 0
    finally:
        # Cleanup: Remove the agent directory and packages directory
        if Path(agent_name).exists():
            shutil.rmtree(agent_name)
        if Path("packages").exists():
            shutil.rmtree("packages")


def test_eject_metrics_skill_skip_deps(cli_runner):
    """Test ejecting the metrics skill with skip-dependencies flag."""
    # 1. Create agent with eightballer/base template
    agent_name = "test_agent"
    create_cmd = [
        "adev",
        "-v",
        "create",
        f"new_author/{agent_name}",
        "-t",
        "eightballer/base",
        "--no-clean-up",
        "--force",
    ]
    runner = cli_runner(create_cmd)
    result = runner.execute()
    assert runner.return_code == 0

    try:
        # 2. CD into the agent directory
        agent_dir = Path(agent_name)
        assert agent_dir.exists(), f"Agent directory {agent_dir} was not created"
        # cd into the agent directory
        with change_dir(agent_dir):
            # 3. Eject the metrics skill with skip-dependencies
            eject_cmd = [
                "adev",
                "-v",
                "eject",
                "skill",
                "eightballer/metrics",
                "new_author/better_skill",
                "--skip-dependencies",
            ]
            runner.execute(eject_cmd)
            assert 'Agent "test_agent" successfully saved in packages folder.' in runner.output
            assert "Agent packages/new_author/agents/test_agent created successfully." in runner.output
            assert runner.return_code == 0
    finally:
        # Cleanup: Remove the agent directory and packages directory
        if Path(agent_name).exists():
            shutil.rmtree(agent_name)
        if Path("packages").exists():
            shutil.rmtree("packages")
