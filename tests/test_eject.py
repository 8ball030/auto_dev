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
        result = cli_runner(eject_cmd)
        result.execute()
        assert "Successfully ejected 1 components" in result.output
        assert f"(skill, {DEFAULT_AUTHOR}/metrics:0.1.0)" in result.output
        assert result.return_code == 0

        # Verify the skill was ejected to the correct location
        ejected_skill_path = Path("skills/metrics")
        assert ejected_skill_path.exists(), "Ejected skill directory not found"

        # Verify the original vendor skill was removed
        vendor_skill_path = Path("vendor/eightballer/skills/metrics")
        assert not vendor_skill_path.exists(), "Vendor skill directory still exists"


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
        # Store initial vendor components for comparison
        initial_vendor_components = list(Path("vendor").rglob("*.yaml"))

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
        result = cli_runner(eject_cmd)
        result.execute()
        assert "Successfully ejected 1 components" in result.output
        assert f"(skill, {DEFAULT_AUTHOR}/metrics:0.1.0)" in result.output
        assert result.return_code == 0

        # Verify only the skill was ejected
        ejected_skill_path = Path("skills/metrics")
        assert ejected_skill_path.exists(), "Ejected skill directory not found"

        # Verify dependencies were not ejected (should have same number of vendor components minus one)
        final_vendor_components = list(Path("vendor").rglob("*.yaml"))
        assert (
            len(final_vendor_components) == len(initial_vendor_components) - 1
        ), "Dependencies were incorrectly ejected"
