"""Small telnet transport tailored to NEON's interactive login sequence."""
import telnetlib3
from crtnm.drivers.contracts import ConnectionProfile
from crtnm.drivers.exceptions import ConnectionFailed
from crtnm.drivers.neon.prompts import find_prompt


class NeonTelnetClient:
    """Handles NEON telnet login without logging terminal secrets."""

    def __init__(self, timeout_seconds: int = 15) -> None:
        self._timeout = timeout_seconds

    def connect(self, profile: ConnectionProfile) -> tuple[telnetlib3.Telnet, str]:
        """Log in and return an open session plus its detected prompt."""
        try:
            client = telnetlib3.Telnet(profile.host, profile.port or 23, self._timeout)
            client.read_until(b"Login:", self._timeout)
            client.write(profile.username.encode() + b"\n")
            client.read_until(b"Password:", self._timeout)
            client.write(profile.password.encode() + b"\n")
            output = client.read_until(b">", self._timeout).decode(errors="replace")
            prompt = find_prompt(output)
            if prompt is None:
                client.close()
                raise ConnectionFailed("NEON login completed without a recognized user prompt")
            return client, prompt
        except (OSError, EOFError) as error:
            raise ConnectionFailed("Telnet connection failed") from error

