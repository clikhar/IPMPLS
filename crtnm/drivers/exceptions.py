"""Driver-specific exceptions that do not leak credentials."""


class DriverError(Exception):
    """Base error for controlled network-driver failures."""


class ConnectionFailed(DriverError):
    """The device could not be reached or authenticated."""


class CommandRejected(DriverError):
    """The device rejected a command or presented an unexpected prompt."""

