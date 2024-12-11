"""Base exceptions for the auto_dev package."""


class OperationError(Exception):
    """Operation error."""


class NotFound(FileNotFoundError):
    """File not found error."""


class NetworkTimeoutError(Exception):
    """Network error."""


class AuthenticationError(Exception):
    """Authentication error."""


class UserInputError(Exception):
    """User input error."""


class ScaffolderError(Exception):
    """Scaffolder error."""
