"""A class to manage workflows constructed.
Uses an open aea agent task manager in order to manage the workflows.
"""

import time
from copy import deepcopy
from dataclasses import asdict, field, dataclass
from collections.abc import Callable
from multiprocessing.pool import ApplyResult

from rich.table import Table
from rich.console import Console
from aea.skills.base import TaskManager
import yaml

from rich.table import Table
from rich.console import Console
from rich.progress import Progress
from rich.panel import Panel
from rich.text import Text


from auto_dev.cli_executor import CommandExecutor
from auto_dev.enums import FileType
from auto_dev.utils import write_to_file


@dataclass
class Task:
    """A class to represent a task in a workflow."""

    id: str = None
    name: str = None
    description: str = None
    conditions: list[Callable] = field(default_factory=list)
    wait: bool = False
    timeout: int = 0
    args: list = field(default_factory=list)
    stream: bool = False
    command: str = None
    working_dir: str = "."

    is_done: bool = False
    is_failed: bool = False

    def work(self):
        """Perform the task's work."""
        self.client = CommandExecutor(self.command.split(" "), cwd=self.working_dir)
        self.is_failed = not self.client.execute()
        self.is_done = True
        return self


@dataclass
class Workflow:
    """A class to represent a workflow."""

    id: str = None
    name: str = None
    description: str = None
    tasks: list[Task] = field(default_factory=list)

    is_done: bool = False
    is_running: bool = False
    is_failed: bool = False
    is_success: bool = False

    def add_task(self, task: Task):
        """Add a task to the workflow."""
        self.tasks.append(task)


class WorkflowManager:
    """A class to manage workflows constructed.
    Uses an open aea agent task manager in order to manage the workflows.
    """

    def __init__(self):
        """Initialize the workflow manager."""
        self.workflows = []
        self.task_manager = TaskManager()
        self.task_manager.start()
        self.console = Console()
        self.table = self.create_table("Workflows")

    def add_workflow(self, workflow: Workflow):
        """Add a workflow to the manager."""
        self.workflows.append(workflow)
        self.table = self.create_table(workflow.name)
        for task in workflow.tasks:
            self.update_table(self.table, task, "Queued", display_process=False)
        self.display_table()

    def get_workflow(self, workflow_id: str) -> Workflow:
        """Get a workflow by its id."""
        for workflow in self.workflows:
            if workflow.id == workflow_id:
                return workflow
        return None

    def submit_task(self, task: Task):
        """Submit a task to the task manager."""
        task.process_id = self.task_manager.enqueue_task(task.work)
        return task.process_id

    def get_task(self, task_id: str) -> ApplyResult:
        """Get a task by its id."""
        return self.task_manager.get_task_result(task_id)

    def run(self):
        """Run the workflow manager."""
        while True:
            for workflow in deepcopy(self.workflows):
                if not workflow.is_running:
                    result = self.run_workflow(workflow.id, exit_on_failure=True)
                    if result:
                        workflow.is_success = True
                    else:
                        workflow.is_failed = True
                    workflow.is_running = False
                    workflow.is_done = True
                if workflow.is_done:
                    self.workflows.remove(workflow)

            time.sleep(5)

    def to_yaml(self):
        """Convert the workflow manager to yaml."""

        workflows = []

        for workflow in self.workflows:
            for task in workflow.tasks:
                tasks = []
                for task in workflow.tasks:
                    tasks.append(asdict(task))
            workflows.append({"id": workflow.id, "name": workflow.name, "description": workflow.description, "tasks": tasks})
        
        write_to_file("workflow_data.yaml", workflows, FileType.YAML)

    @staticmethod
    def from_yaml(cls):
        """Load the workflow manager from yaml."""
        raw_data = cls.load_yaml("workflows.yaml")
        return cls(**raw_data)
    
    def load_yaml(self, file_path: str):
        """Load a yaml file."""
        with open(file_path, "r") as file:
            return yaml.safe_load(file)

    def run_workflow(
        self, workflow_id: str, wait: bool = True, exit_on_failure: bool = True, display_process: bool = True
    ):
        """Run a workflow by its ID and update a table for visual status.
        If display_process is True, show the workflow's progress in real-time.
        """
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            return False
        workflow.is_running = True

        # Display the workflow table header if display_process is True
        if display_process:
            self.table = self.create_table(self.workflow.name)
            self.display_table()

        for task in workflow.tasks:
            # Submit task and update table with 'Queued' status
            self.submit_task(task)
            self.update_table(self.table, task, "In-Progress", display_process)

            if wait:
                task_result = self.get_task(task.process_id)
                task_result.wait()

                # Simulate task completion message
                # Update task status to 'Completed'
                if task_result.successful() and task.is_done and not task.is_failed:
                    self.update_table(self.table, task, "Completed", display_process)
                    continue
                self.update_table(self.table, task, "Failed", display_process)
                if exit_on_failure:
                    return False
        return True

    def create_table(self, workflow_name: str) -> Table:
        """Creates a table for displaying the workflow status."""
        table = Table(title=f"Workflow: {workflow_name}", box="ROUND", show_header=True, header_style="bold magenta")
        table.add_column("Task ID", justify="center", style="bold", width=10)
        table.add_column("Description", justify="left", style="bold green")
        table.add_column("Status", justify="center", style="bold")
        return table

    def update_table(self, table: Table, task: Task, status: str, display_process: bool):
        """Update the table with the task status."""
        # Find the row index based on task ID
        try:
            index_of_task = table.columns[0]._cells.index(str(task.id))  # noqa
        except ValueError:
            table.add_row(str(task.id), task.description, status)
            return self.update_table(table, task, status, display_process)

        # Apply color based on task status
        if status == "Queued":
            status_color = "yellow"
        elif status == "In-Progress":
            status_color = "blue"
        elif status == "Completed":
            status_color = "green"
        elif status == "Failed":
            status_color = "red"
        
        # Update the status in the table with the appropriate color
        table.columns[2]._cells[index_of_task] = f"[{status_color}]{status}[/{status_color}]"

        # Display the updated table if display_process is True
        if display_process:
            self.console.clear()
            self.display_table()

    def display_table(self):
        """Display the table with visual enhancements."""
        if self.table:
            self.console.print(Panel(self.table, title="Workflow Status", border_style="bold blue", padding=(1, 2)))

    def display_table(self):
        """Display the table."""
        self.console.print(self.table)

def main():
    """Run the main function."""
    workflow_manager = WorkflowManager()
    workflow = Workflow(id="1", name="test_workflow", description="A test workflow")

    for task in range(2):
        task_1 = Task(
            id=str(task),
            name=f"test_task_{task}",
            description=f"A test task {task}",
            command=f"echo 'Hello, World! {task}'",
        )
        task_2 = Task(id=str(task) + "a", name=f"test_task_{task}", description=f"A sleep {task}", command="sleep 1")
        workflow.add_task(task_1)
        workflow.add_task(task_2)

    create_wf = Workflow(id="1", name="create_workflow", description="A create workflow")

    tasks = [
        Task(
            id="1",
            name="create_agent",
            description="Make a new agent",
            command="adev create author/agent -t eightballer/base --no-clean-up --force",
        ),
        Task(
            id="2",
            name="create_skill",
            description="Fork an existing skill",
            command="adev eject skill eightballer/metrics new_author/new_skill",
            working_dir="agent",
        ),
        Task(
            id="3",
            name="update_ejected_components",
            description="Publish forked code to local registry",
            command="aea -s publish --push-missing --local",
            working_dir="agent",
        ),
    ]

    for task in tasks:
        create_wf.add_task(task)
    workflow_manager.add_workflow(create_wf)
    workflow_manager.run_workflow("1")
    workflow_manager.to_yaml()


if __name__ == "__main__":
    main()
