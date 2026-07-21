"""Read-only NEON driver using SSH or telnet transport."""
"""from contextlib import closing"""
from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoBaseException
from crtnm.drivers.contracts import ConnectionProfile, DeviceFacts, NetworkDriver
from crtnm.drivers.exceptions import CommandRejected, ConnectionFailed
from crtnm.drivers.neon.prompts import PAGINATION_MARKERS, contains_confirmation, find_prompt
from crtnm.drivers.neon.telnet_client import NeonTelnetClient


class NeonDriver(NetworkDriver):
    """NEON driver with exact prompt, enable, pagination, and confirmation safeguards."""

    vendor = "neon"
    _ALLOWED_COMMANDS = frozenset({"show version", "show interface", "show running-config", "show lldp neighbors", "show system"})

    def test_connection(self, profile: ConnectionProfile) -> DeviceFacts:
        """Test reachability using only `show version`."""
        output, prompt = self._run(profile, "show version")
        return DeviceFacts(hostname=prompt.rstrip(">#").split("(")[0], prompt=prompt, version=output[:4000])

    def execute_readonly(self, profile: ConnectionProfile, command: str) -> str:
        """Execute an explicit allow-listed NEON show command."""
        if command.strip().lower() not in self._ALLOWED_COMMANDS:
            raise CommandRejected("Only approved read-only NEON commands may be executed")
        output, _ = self._run(profile, command)
        return output

    def _run(self, profile: ConnectionProfile, command: str) -> tuple[str, str]:
        if profile.protocol == "telnet":
            return self._run_telnet(profile, command)
        if profile.protocol != "ssh":
            raise ConnectionFailed("Unsupported protocol; choose SSH or telnet")
        return self._run_ssh(profile, command)

    """def _run_ssh(self, profile: ConnectionProfile, command: str) -> tuple[str, str]:
        try:
            with closing(ConnectHandler(device_type="terminal_server", host=profile.host, username=profile.username, password=profile.password, secret=profile.enable_password or "", port=profile.port or 22, timeout=15, auth_timeout=15, banner_timeout=15)) as connection:
                prompt = connection.find_prompt().strip()
                if not find_prompt(prompt):
                    raise ConnectionFailed("Device did not provide a recognized NEON prompt")
                if prompt.endswith(">") and profile.enable_password:
                    connection.enable(cmd="EN", enable_pattern=r"#")
                output = connection.send_command(command, expect_string=r"[>#]", read_timeout=30)
                return self._validate_output(output), connection.find_prompt().strip()
        except NetmikoBaseException as error:
            raise ConnectionFailed("SSH connection or authentication failed") from error
    """
    def _run_ssh(self, profile: ConnectionProfile, command: str) -> tuple[str, str]:
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

            if prompt.endswith(">") and profile.enable_password:
                connection.enable(
                    cmd="EN",
                    enable_pattern=r"#"
                )

            output = connection.send_command(
                command,
                expect_string=r"[>#]",
                read_timeout=30
            )

            return (
                self._validate_output(output),
                connection.find_prompt().strip()
            )

        except NetmikoBaseException as error:
            raise ConnectionFailed(
                "SSH connection or authentication failed"
            ) from error

        finally:
            if connection:
                connection.disconnect()

    def _run_telnet(self, profile: ConnectionProfile, command: str) -> tuple[str, str]:
        client, prompt = NeonTelnetClient().connect(profile)

        try:
                client.write(command.encode() + b"\n")
                raw = client.read_until(
                    prompt.encode(),
                    30
                ).decode(errors="replace")

                return self._validate_output(raw), prompt

        finally:
                client.close()

    @staticmethod
    def _validate_output(output: str) -> str:
        if any(marker in output for marker in PAGINATION_MARKERS):
            raise CommandRejected("Paged output requires interactive continuation and was stopped safely")
        if contains_confirmation(output):
            raise CommandRejected("Interactive confirmation detected; command was stopped")
        return output
