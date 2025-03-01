"""A class to manage workflows constructed.
Uses an open aea agent task manager in order to manage the workflows.
"""

import re
import sys
import time
import logging
from copy import deepcopy
from uuid import uuid4
from dataclasses import field, asdict, dataclass
from collections.abc import Callable
from multiprocessing.pool import ApplyResult

import yaml
from rich import print
from rich.text import Text
from rich.panel import Panel
from rich.table import Table
from rich.console import Console
from aea.skills.base import TaskManager

from auto_dev.enums import FileType
from auto_dev.utils import write_to_file
from auto_dev.exceptions import UserInputError
from auto_dev.cli_executor import CommandExecutor


VAR_REGEX = r"\${task.\d+\.client\.stdout}"
KWARG_REGEX = r"\${kwargs.(?P<key>\w+)}"


def get_logger(name: str = "workflow_manager", log_level: str = "INFO"):
    """Stream handler for logging."""
    log = logging.getLogger(name)
    if log.hasHandlers():
        log.handlers.clear()
    logging.getLogger().handlers.clear()
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(message)s")
    handler.setFormatter(formatter)
    log.addHandler(handler)
    log.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    log.info("Logger initialized.")
    return log


@dataclass
class Task:
    """A class to represent a task in a workflow."""

    id: str = None
    name: str = None
    description: str = None
    conditions: list[Callable] = field(default_factory=list)
    wait: bool = True
    timeout: int = 0
    args: list = field(default_factory=list)
    stream: bool = True
    command: str = None
    working_dir: str = "."
    logger = None
    pause_after: int = 0
    shell: bool = False
    continue_on_error: bool = False
    env_vars: dict = None
    verbose: bool = False

    is_done: bool = False
    is_failed: bool = False

    def work(self):
        """Perform the task's work."""
        self.client = CommandExecutor(
            self.command.split(" "),
            cwd=self.working_dir,
            logger=self.logger,
        )
        print(f"Executing command: `{self.command}`")
        self.is_failed = not self.client.execute(
            stream=self.stream, env_vars=self.env_vars, shell=self.shell, verbose=self.verbose
        )
        self.is_done = True
        return self

    def __post_init__(self):
        """Post initialization steps."""
        if not self.id:
            self.id = uuid4().hex


@dataclass
class Workflow:
    """A class to represent a workflow."""

    id: str = None
    name: str = None
    description: str = None
    tasks: list[Task] = field(default_factory=list)
    kwargs: dict = field(default_factory=dict)

    is_done: bool = False
    is_running: bool = False
    is_failed: bool = False
    is_success: bool = False

    def add_task(self, task: Task):
        """Add a task to the workflow."""
        self.tasks.append(task)

    def __post_init__(self):
        """Post initialization steps."""
        if not self.id:
            self.id = uuid4().hex

    @staticmethod
    def from_file(file_path: str):
        """Load the workflow from yaml."""
        with open(file_path, encoding="utf-8") as file:
            raw_data = yaml.safe_load(file)
        raw_data["tasks"] = [Task(**task) for task in raw_data["tasks"]]
        return Workflow(**raw_data)


class WorkflowManager:
    """A class to manage workflows constructed.
    Uses an open aea agent task manager in order to manage the workflows.
    """

    def __init__(self):
        """Initialize the workflow manager."""
        self.workflows: list[Workflow] = []
        self.task_manager = TaskManager()
        self.task_manager.start()
        self.console = Console()
        self.table = self.create_table("Workflows")
        self.cli_output = ""
        self.logger = get_logger()
        self.logger.clear = lambda: self.update_cli_output("", clear=True)

    def update_cli_output(self, output: str, clear: bool = False):
        """Update the CLI output panel with the latest output."""
        if clear:
            self.cli_output = ""
        self.cli_output += output
        if len(self.cli_output) > 0:
            self.display_table()

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

    def check_if_conditions_met(self, task: Task, workflow_id: str):
        """Check if the conditions for a task are met."""
        conditions = []
        if task.conditions:
            for condition in task.conditions:
                matches = re.findall(VAR_REGEX, condition)
                if matches and len(matches) > 0:
                    for match in matches:
                        conditions.append(self.evaluate_condition(condition, match, workflow_id))
        return all(conditions)

    def evaluate_condition(self, condition: str, match: str, workflow_id: str):
        """Evaluate a condition for a task."""
        referenced_task_id = str(match.split(".")[1])
        referenced_task = self.get_task_from_workflow(workflow_id, referenced_task_id)
        condition = condition.replace(match, "\n".join(referenced_task.client.stdout))
        try:
            result = eval(condition)
        except Exception as e:
            msg = f"Condition {condition} is invalid: {e}"
            raise UserInputError(msg) from e
        return result

    def submit_task(self, task: Task, workflow_id: str) -> str:
        """Submit a task to the task manager.
        - id: '6'
          name: get_branch
          description: get the current branch
          command: git branch --show-current.

        - id: '7'
          name: push_changes
          description: Push changes to git
          command: git push origin ${task.6.client.stdout}
        """

        self.logger.clear()
        task.logger = self.logger

        for attr in ["command", "working_dir"]:
            if not getattr(task, attr):
                continue
            current_value = getattr(task, attr)
            new_value = self.check_if_command_has_kwarg_vars(current_value, workflow_id)
            new_value = self.check_if_command_has_ref_vars(new_value, workflow_id)
            setattr(task, attr, new_value)

        task.process_id = self.task_manager.enqueue_task(task.work)
        return task.process_id

    def check_if_command_has_ref_vars(self, string: str, workflow_id: str) -> str:
        """Check if a command has variables."""
        matches = re.findall(VAR_REGEX, string)
        if matches and len(matches) > 0:
            for match in matches:
                task_id = str(match.split(".")[1])
                referenced_task = self.get_task_from_workflow(workflow_id, task_id)
                string = string.replace(match, "\n".join(referenced_task.client.stdout))
        return string

    def check_if_command_has_kwarg_vars(self, string: str, workflow_id: str) -> str:
        """Check if a command has variables."""
        wf = self.get_workflow(workflow_id)
        wf_kwargs = getattr(wf, "kwargs", {})
        # Find all matches
        matches = re.findall(KWARG_REGEX, string)

        if matches and len(matches) > 0:
            for match in matches:
                key = match
                if key not in wf_kwargs:
                    msg = f"Key {key} not found in kwargs provided to wf"
                    raise UserInputError(msg)
                match_pattern = "${kwargs." + key + "}"  # Form the full match string
                string = string.replace(match_pattern, str(wf_kwargs[key]))
        return string

    def get_task(self, task_id: str) -> ApplyResult:
        """Get a task by its id."""
        return self.task_manager.get_task_result(task_id)

    def get_task_from_workflow(self, workflow_id: str, task_id: str) -> Task:
        """Get a task from a workflow by its id."""
        workflow = self.get_workflow(workflow_id)
        for task in workflow.tasks:
            if task.id == task_id:
                return task
        return None

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
                        workflow.is_done = True
                    workflow.is_running = False
                    workflow.is_done = True
                if workflow.is_done:
                    self.remove_workflow(workflow.id)
            break

    def remove_workflow(self, workflow_id: str):
        """Remove a workflow by its id."""
        index = None
        for workflow in self.workflows:
            if workflow.id == workflow_id:
                index = self.workflows.index(workflow)
                break
        if index is not None:
            self.workflows.pop(index)
            return True
        return False

    def to_yaml(self):
        """Convert the workflow manager to yaml."""

        workflows = []

        for workflow in self.workflows:
            for task in workflow.tasks:
                tasks = []
                for task in workflow.tasks:
                    tasks.append(asdict(task))
            workflows.append(
                {"id": workflow.id, "name": workflow.name, "description": workflow.description, "tasks": tasks}
            )

        write_to_file("workflow_data.yaml", workflows, FileType.YAML)

    @staticmethod
    def from_yaml(file_path: str):
        """Load the workflow manager from yaml."""
        raw_data = WorkflowManager.load_yaml(file_path)
        raw_data["tasks"] = [Task(**task) for task in raw_data["tasks"]]
        wf = WorkflowManager()
        wf.add_workflow(Workflow(**raw_data))
        return wf

    @staticmethod
    def load_yaml(file_path: str):
        """Load a yaml file."""
        with open(file_path, encoding="utf-8") as file:
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
        for task in workflow.tasks:
            # Submit task and update table with 'Queued' status
            if not self.check_if_conditions_met(task, workflow_id):
                task.is_done = True
                self.update_table(self.table, task, "Skipped", display_process)
                continue

            self.update_table(self.table, task, "In-Progress", display_process)
            self.submit_task(task, workflow_id)

            if wait:
                task_result = self.get_task(task.process_id)
                task_result.wait()
                if task.pause_after:
                    time.sleep(task.pause_after)
                # Simulate task completion message
                # Update task status to 'Completed'
                status = "Completed" if task_result.successful() and not task.is_failed and task.is_done else "Failed"
                self.update_table(self.table, task, status, display_process)
                if status == "Failed":
                    self.logger.error(f"Task {task.id} failed.")
                    if exit_on_failure and not task.continue_on_error:
                        sys.exit(1)

                    if not task.continue_on_error:
                        workflow.is_failed = True
                        workflow.is_success = False
                        return False
        return True

    def create_table(self, workflow_name: str) -> Table:
        """Creates a table for displaying the workflow status."""
        table = Table(
            title=f"Workflow: {workflow_name}",
        )
        table.add_column("Task ID", justify="center", style="bold", width=10)
        table.add_column("Description", justify="left", style="cyan")
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
        elif status == "Skipped":
            status_color = "magenta"

        # Update the status in the table with the appropriate color
        table.columns[2]._cells[index_of_task] = f"[{status_color}]{status}[/{status_color}]"  # noqa

        # Display the updated table if display_process is True
        if display_process:
            self.console.clear()
            self.display_table()
            return None
        return None

    def display_table(self):
        """Display the table with visual enhancements."""
        self.console.clear()
        if self.table:
            table_panel = Panel(self.table, title="Workflow Status", border_style="bold blue", padding=(1, 2))

            # Create the panel for the CLI output (can be updated during task execution)
            self.console.print(table_panel, justify="center")
            if self.cli_output:
                res = Text(self.cli_output, style="system", justify="left")
                cli_panel = Panel(res or "No output yet", title="CLI Output", border_style="bold green", padding=(1, 2))
                self.console.print(cli_panel, highlight=True)

            # Clear the console and print the panels


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
            pause_after=5,
        ),
        Task(
            id="2",
            name="create_skill",
            description="Fork an existing skill",
            command="adev eject skill eightballer/metrics new_author/new_skill",
            working_dir="agent",
            pause_after=5,
        ),
        Task(
            id="3",
            name="update_ejected_components",
            description="Publish forked code to local registry",
            command="aea -s publish --push-missing --local",
            working_dir="agent",
            pause_after=5,
        ),
    ]

    for task in tasks:
        create_wf.add_task(task)
    workflow_manager.add_workflow(create_wf)
    workflow_manager.run_workflow("1")
    workflow_manager.to_yaml()


if __name__ == "__main__":
    main()
