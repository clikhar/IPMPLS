"""Contract shared by every supported vendor driver."""
from abc import ABC, abstractmethod
from dataclasses import dataclass

from crtnm.drivers.exceptions import CommandRejected


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

    
    """def execute_readonly(self, profile: ConnectionProfile, command: str) -> str:"""
    """Run a vetted non-mutating command and return sanitized output."""
    @abstractmethod
    def execute_readonly(
        self,
        profile: ConnectionProfile,
        command: str
    ) -> str:
        """Execute an explicit allow-listed NEON show command."""

        normalized = command.strip().lower()

        if normalized not in self._ALLOWED_COMMANDS:
            raise CommandRejected(
                f"Command is not approved for read-only execution: {command}"
            )

        output, _ = self._run(
            profile,
            normalized
        )
        return output
    
    def execute_readonly_many(self,profile: ConnectionProfile,commands: list[str]) -> list[dict[str, object]]:
        """
        Execute multiple driver-approved read-only commands.

        Each command is executed independently so that a failure
        in one command does not hide successful results from the
        preceding commands.
        """

        results: list[dict[str, object]] = []

        for command in commands:

            try:

                output = self.execute_readonly(
                    profile,
                    command
                )

                results.append({
                    "command": command,
                    "success": True,
                    "output": output,
                    "error": None,
                })

            except Exception as error:

                results.append({
                    "command": command,
                    "success": False,
                    "output": "",
                    "error": str(error),
                })

        return results
