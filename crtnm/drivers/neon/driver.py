"""Read-only NEON driver using SSH or telnet transport."""

from __future__ import annotations

from typing import Any

from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoBaseException

from crtnm.drivers.contracts import (
    ConnectionProfile,
    DeviceFacts,
    NetworkDriver,
)
from crtnm.drivers.exceptions import (
    CommandRejected,
    ConnectionFailed,
)
from crtnm.drivers.neon.prompts import (
    PAGINATION_MARKERS,
    contains_confirmation,
    find_prompt,
)
from crtnm.drivers.neon.telnet_client import NeonTelnetClient

from crtnm.drivers.neon.collectors.cpu import parse_cpu
from crtnm.drivers.neon.collectors.memory import parse_memory
from crtnm.drivers.neon.collectors.version import parse_version


class NeonDriver(NetworkDriver):
    """
    NEON driver with:

    - SSH and Telnet support
    - prompt validation
    - enable-mode handling
    - pagination protection
    - confirmation protection
    - read-only command allow-list
    - structured device fact collection
    """

    vendor = "neon"

    _ALLOWED_COMMANDS = frozenset(
        {
            "show version",
            "show interface",
            "show interface brief",
            "show running-config",
            "show lldp neighbors",
            "show system",
            "show cpu-utilization",
            "show memory",
            "show hardware",
            "show ip ospf neighbor",
            "show mpls ldp adjacency",
            "show mpls l2vc",
            "show ip vrf",
        }
    )

    # Commands used by structured collectors.
    _FACT_COMMANDS = frozenset(
        {
            "show version",
            "show memory",
            "show cpu-utilization",
        }
    )

    def test_connection(
        self,
        profile: ConnectionProfile,
    ) -> DeviceFacts:
        """
        Test reachability using only `show version`.
        """

        output, prompt = self._run(
            profile,
            "show version",
        )

        hostname = (
            prompt
            .rstrip(">#")
            .split("(")[0]
            .strip()
        )

        return DeviceFacts(
            hostname=hostname,
            prompt=prompt,
            version=output[:4000],
        )

    def execute_readonly(
        self,
        profile: ConnectionProfile,
        command: str,
    ) -> str:
        """
        Execute an explicit allow-listed NEON show command.
        """

        normalized_command = command.strip().lower()

        if normalized_command not in self._ALLOWED_COMMANDS:
            raise CommandRejected(
                "Only approved read-only NEON commands may be executed"
            )

        output, _ = self._run(
            profile,
            normalized_command,
        )

        return output

    def collect_facts(
        self,
        profile: ConnectionProfile,
    ) -> dict[str, Any]:
        """
        Collect structured operational facts from a NEON device.

        Currently collects:

        - show version
        - show memory
        - show cpu-utilization

        The individual outputs are parsed by the dedicated collector
        modules under crtnm.drivers.neon.collectors.
        """

        # ---------------------------------------------------------
        # SHOW VERSION
        # ---------------------------------------------------------

        version_output, prompt = self._run(
            profile,
            "show version",
        )

        version = parse_version(version_output)

        hostname = (
            prompt
            .rstrip(">#")
            .split("(")[0]
            .strip()
        )

        # ---------------------------------------------------------
        # SHOW MEMORY
        # ---------------------------------------------------------

        memory_output, _ = self._run(
            profile,
            "show memory",
        )

        memory = parse_memory(
            memory_output
        )

        # ---------------------------------------------------------
        # SHOW CPU
        # ---------------------------------------------------------

        cpu_output, _ = self._run(
            profile,
            "show cpu-utilization",
        )

        cpu = parse_cpu(
            cpu_output
        )

        # ---------------------------------------------------------
        # FINAL STRUCTURED RESULT
        # ---------------------------------------------------------

        return {
            "vendor": self.vendor,
            "hostname": hostname,
            "prompt": prompt,
            "version": version,
            "memory": memory,
            "cpu": cpu,
        }

    def _run(
        self,
        profile: ConnectionProfile,
        command: str,
    ) -> tuple[str, str]:

        if profile.protocol == "telnet":
            return self._run_telnet(
                profile,
                command,
            )

        if profile.protocol != "ssh":
            raise ConnectionFailed(
                "Unsupported protocol; choose SSH or telnet"
            )

        return self._run_ssh(
            profile,
            command,
        )

    def _run_ssh(
        self,
        profile: ConnectionProfile,
        command: str,
    ) -> tuple[str, str]:

        connection = None

        try:
            connection = ConnectHandler(
                device_type="terminal_server",
                host=profile.host,
                username=profile.username,
                password=profile.password,
                secret=profile.enable_password or "",
                port=profile.port or 22,
                timeout=15,
                auth_timeout=15,
                banner_timeout=15,
            )

            prompt = connection.find_prompt().strip()

            if not find_prompt(prompt):
                raise ConnectionFailed(
                    "Device did not provide a recognized NEON prompt"
                )

            # Enter enable mode if required.
            if (
                prompt.endswith(">")
                and profile.enable_password
            ):
                connection.enable(
                    cmd="EN",
                    enable_pattern=r"#",
                )

            output = connection.send_command(
                command,
                expect_string=r"[>#]",
                read_timeout=30,
            )

            current_prompt = (
                connection.find_prompt().strip()
            )

            validated = self._validate_output(
                output
            )

            cleaned = self._clean_output(
                validated,
                command,
                current_prompt,
            )

            return cleaned, current_prompt

        except NetmikoBaseException as error:
            raise ConnectionFailed(
                "SSH connection or authentication failed"
            ) from error

        finally:
            if connection:
                connection.disconnect()

    def _run_telnet(
        self,
        profile: ConnectionProfile,
        command: str,
    ) -> tuple[str, str]:

        client, prompt = (
            NeonTelnetClient().connect(profile)
        )

        try:
            client.write(
                command.encode() + b"\n"
            )

            raw = client.read_until(
                prompt.encode(),
                30,
            ).decode(
                errors="replace"
            )

            validated = self._validate_output(
                raw
            )

            cleaned = self._clean_output(
                validated,
                command,
                prompt,
            )

            return cleaned, prompt

        finally:
            client.close()

    @staticmethod
    def _validate_output(
        output: str,
    ) -> str:
        """
        Reject output that indicates pagination or
        interactive confirmation.
        """

        if any(
            marker in output
            for marker in PAGINATION_MARKERS
        ):
            raise CommandRejected(
                "Paged output requires interactive continuation "
                "and was stopped safely"
            )

        if contains_confirmation(output):
            raise CommandRejected(
                "Interactive confirmation detected; "
                "command was stopped"
            )

        return output

    @staticmethod
    def _clean_output(
        output: str,
        command: str,
        prompt: str,
    ) -> str:
        """
        Remove CLI echo and final device prompt while
        preserving the actual command output.
        """

        lines = output.splitlines()

        cleaned: list[str] = []

        normalized_command = (
            command.strip().lower()
        )

        normalized_prompt = (
            prompt.strip()
        )

        for line in lines:
            stripped = line.strip()

            # Remove command echo.
            if (
                stripped.lower()
                == normalized_command
            ):
                continue

            # Remove final device prompt.
            if (
                stripped
                == normalized_prompt
            ):
                continue

            cleaned.append(line)

        return "\n".join(
            cleaned
        ).strip()