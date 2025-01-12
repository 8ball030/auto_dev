"""Enums for auto_dev."""

from enum import Enum


class FileType(Enum):
    """File type enum."""

    YAML = "yaml"
    JSON = "json"
    TEXT = "txt"
    PYTHON = "py"


class FileOperation(Enum):
    """File operation enum."""

    READ = "read"
    WRITE = "write"
    APPEND = "append"
    DELETE = "delete"
    COPY = "copy"
    MOVE = "move"
    RENAME = "rename"
    CREATE = "create"
    EXISTS = "exists"


class UserInput(Enum):
    """User input enum."""

    YES = "yes"
    NO = "no"
    ALL = "all"
    NONE = "none"
    CANCEL = "cancel"
    SKIP = "skip"
    CONTINUE = "continue"
    QUIT = "quit"
    EXIT = "exit"
    BACK = "back"
    NEXT = "next"
    PREVIOUS = "previous"
    FINISH = "finish"
    START = "start"
    HELP = "help"
    INFO = "info"


class BehaviourTypes(Enum):
    """Behaviour types enum."""

    metrics = "metrics"
    simple_fsm = "simple_fsm"
