"""Base exceptions for the auto_dev package."""


class OperationError(Exception):
    """Operation error."""


class NotFound(FileNotFoundError):
    """File not found error."""


class NetworkTimeoutError(Exception):
    """Network error."""


class APIError(Exception):
    """API error."""


class AuthenticationError(Exception):
    """Authentication error."""


class UserInputError(Exception):
    """User input error."""


class ScaffolderError(Exception):
    """Scaffolder error."""


class UnsupportedSolidityVersion(Exception):
    """Exception raised when processing ABIs from unsupported Solidity versions."""


class ConfigUpdateError(Exception):
    """Raised when there is an error updating component configuration."""


class DependencyTreeError(Exception):
    """Raised when there is an error building the dependency tree."""
