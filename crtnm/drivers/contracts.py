"""Contract shared by every supported vendor driver."""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ConnectionProfile:
    """Connection data supplied at execution time and never persisted in logs."""

    host: str
    username: str
    password: str
    enable_password: str | None = None
    protocol: str = "ssh"
    port: int | None = None


@dataclass(frozen=True)
class DeviceFacts:
    """Vendor-neutral data gathered during a safe connection test."""

    hostname: str
    prompt: str
    version: str | None


class NetworkDriver(ABC):
    """Minimum surface implemented by all driver plug-ins."""

    vendor: str

    @abstractmethod
    def test_connection(self, profile: ConnectionProfile) -> DeviceFacts:
        """Authenticate and collect read-only identity information."""

    @abstractmethod
    def execute_readonly(self, profile: ConnectionProfile, command: str) -> str:
        """Run a vetted non-mutating command and return sanitized output."""

