"""Tests for the eject command."""

from pathlib import Path

from auto_dev.utils import change_dir
from auto_dev.constants import DEFAULT_AUTHOR, DEFAULT_AGENT_NAME


def test_eject_metrics_skill_workflow(cli_runner, test_filesystem):
    """Test the complete workflow of creating an agent and ejecting the metrics skill."""
    assert str(Path.cwd()) == test_filesystem
    # 1. Create agent with eightballer/base template
    create_cmd = [
        "adev",
        "-v",
        "create",
        f"{DEFAULT_AUTHOR}/{DEFAULT_AGENT_NAME}",
        "-t",
        "eightballer/base",
        "--no-clean-up",
        "--force",
    ]
    runner = cli_runner(create_cmd)
    result = runner.execute()
    assert runner.return_code == 0

    # 2. CD into the agent directory
    agent_dir = Path(DEFAULT_AGENT_NAME)
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
            f"{DEFAULT_AUTHOR}/metrics",
        ]
        runner.execute(eject_cmd)
        assert f'Agent "{DEFAULT_AGENT_NAME}" successfully saved in packages folder.' in runner.output
        assert f"Agent packages/{DEFAULT_AUTHOR}/agents/{DEFAULT_AGENT_NAME} created successfully." in runner.output
        assert runner.return_code == 0


def test_eject_metrics_skill_skip_deps(cli_runner, test_filesystem):
    """Test ejecting the metrics skill with skip-dependencies flag."""
    assert str(Path.cwd()) == test_filesystem
    # 1. Create agent with eightballer/base template
    create_cmd = [
        "adev",
        "-v",
        "create",
        f"{DEFAULT_AUTHOR}/{DEFAULT_AGENT_NAME}",
        "-t",
        "eightballer/base",
        "--no-clean-up",
        "--force",
    ]
    runner = cli_runner(create_cmd)
    result = runner.execute()
    assert runner.return_code == 0

    # 2. CD into the agent directory
    agent_dir = Path(DEFAULT_AGENT_NAME)
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
            f"{DEFAULT_AUTHOR}/metrics",
            "--skip-dependencies",
        ]
        runner.execute(eject_cmd)
        assert f'Agent "{DEFAULT_AGENT_NAME}" successfully saved in packages folder.' in runner.output
        assert f"Agent packages/{DEFAULT_AUTHOR}/agents/{DEFAULT_AGENT_NAME} created successfully." in runner.output
        assert runner.return_code == 0
