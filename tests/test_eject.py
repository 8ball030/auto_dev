"""Tests for the eject command."""

from pathlib import Path

from auto_dev.constants import AUTO_DEV_FOLDER, DEFAULT_AGENT_NAME
from auto_dev.workflow_manager import WorkflowManager


def test_eject_metrics_skill_workflow(test_filesystem):
    """Test the complete workflow of creating an agent and ejecting the metrics skill."""
    assert str(Path.cwd()) == test_filesystem
    # 1. Create agent with eightballer/base template
    wf_manager: WorkflowManager = WorkflowManager().from_yaml(
        file_path=Path(AUTO_DEV_FOLDER) / "data" / "workflows" / "eject_component.yaml"
    )
    create_agent_task = wf_manager.workflows[0].tasks[0]
    task = create_agent_task.work()
    agent_dir = Path(DEFAULT_AGENT_NAME)
    assert agent_dir.exists(), f"Agent directory {agent_dir} was not created"
    assert all([task.is_done, not task.is_failed]), f"Task failed: {task.client.output}"
    task_2 = wf_manager.workflows[0].tasks[1].work()
    assert all([task_2.is_done, not task_2.is_failed]), f"Task failed: {task_2.client.output}"
    assert str(Path.cwd()) == test_filesystem
    ejected_skill_path = Path(DEFAULT_AGENT_NAME) / "skills" / "simple_fsm"
    assert ejected_skill_path.exists(), "Ejected skill directory not found"
    # Verify the original vendor skill was removed
    vendor_skill_path = Path(DEFAULT_AGENT_NAME) / "vendor" / "skills" / "metrics"
    assert not vendor_skill_path.exists(), "Vendor skill directory still exists"


def test_eject_metrics_skill_skip_deps(test_filesystem):
    """Test ejecting the metrics skill with skip-dependencies flag."""
    assert str(Path.cwd()) == test_filesystem
    # 1. Create agent with eightballer/base template
    wf_manager: WorkflowManager = WorkflowManager().from_yaml(
        file_path=Path(AUTO_DEV_FOLDER) / "data" / "workflows" / "eject_component.yaml"
    )
    create_agent_task = wf_manager.workflows[0].tasks[0]
    task_1 = create_agent_task.work()
    agent_dir = Path(DEFAULT_AGENT_NAME)
    assert agent_dir.exists(), f"Agent directory {agent_dir} was not created"
    initial_vendor_components = list((Path(DEFAULT_AGENT_NAME) / "vendor").rglob("*.yaml"))
    assert all([task_1.is_done, not task_1.is_failed]), f"Task failed: {task_1.client.output}"
    task_2 = wf_manager.workflows[0].tasks[1]
    task_2.command = "adev eject skill eightballer/metrics author/metrics --skip-dependencies"
    task_2.work()
    assert all([task_2.is_done, not task_2.is_failed]), f"Task failed: {task_2.client.output}"

    # Verify only the skill was ejected
    assert "Successfully ejected 1 components" in task_2.client.output
    assert "(skill, author/metrics:0.1.0)" in task_2.client.output
    assert all([task_2.is_done, not task_2.is_failed]), f"Task failed: {task_2.client.output}"

    # Verify only the skill was ejected
    ejected_skill_path = Path(DEFAULT_AGENT_NAME) / "skills" / "metrics"
    assert ejected_skill_path.exists(), "Ejected skill directory not found"

    # Verify dependencies were not ejected (should have same number of vendor components minus one)
    final_vendor_components = list((Path(DEFAULT_AGENT_NAME) / "vendor").rglob("*.yaml"))
    assert len(final_vendor_components) == len(initial_vendor_components) - 1, "Dependencies were incorrectly ejected"


def test_eject_http_protocol(test_filesystem):
    """Test ejecting the metrics skill with skip-dependencies flag."""
    assert str(Path.cwd()) == test_filesystem
    # 1. Create agent with eightballer/base template
    wf_manager: WorkflowManager = WorkflowManager().from_yaml(
        file_path=Path(AUTO_DEV_FOLDER) / "data" / "workflows" / "eject_component.yaml"
    )
    create_agent_task = wf_manager.workflows[0].tasks[0]
    task_1 = create_agent_task.work()
    agent_dir = Path(DEFAULT_AGENT_NAME)
    assert agent_dir.exists(), f"Agent directory {agent_dir} was not created"
    list((Path(DEFAULT_AGENT_NAME) / "vendor").rglob("*.yaml"))
    assert all([task_1.is_done, not task_1.is_failed]), f"Task failed: {task_1.client.output}"
    task_2 = wf_manager.workflows[0].tasks[1]
    task_2.command = "adev eject protocol eightballer/http author/http"
    task_2.work()
    assert all([task_2.is_done, not task_2.is_failed]), f"Task failed: {task_2.client.output}"
    assert "Successfully ejected 5 components" in task_2.client.output
    assert "(skill, author/metrics:0.1.0)" in task_2.client.output
    assert all([task_2.is_done, not task_2.is_failed]), f"Task failed: {task_2.client.output}"

    # Verify only the skill was ejected
    ejected_skill_path = Path(DEFAULT_AGENT_NAME) / "skills" / "metrics"
    assert ejected_skill_path.exists(), "Ejected skill directory not found"

    # Verify dependencies were not ejected (should have same number of vendor components minus one)
    final_vendor_components = list((Path(DEFAULT_AGENT_NAME) / "vendor").rglob("*.yaml"))
    assert len(final_vendor_components) > 1, "Dependencies were incorrectly ejected"
