"""Tolerant parsers for common NEON monitoring command output."""
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class HealthReading:
    cpu_percent: float | None
    memory_percent: float | None
    temperature_celsius: float | None


@dataclass(frozen=True)
class InterfaceReading:
    name: str
    status: str
    description: str | None


@dataclass(frozen=True)
class NeighborReading:
    local_interface: str
    neighbor: str
    neighbor_interface: str | None


class MonitoringParser:
    """Extracts stable operational facts without assuming one firmware layout."""

    @staticmethod
    def health(output: str) -> HealthReading:
        """Read percentage and temperature fields if a device provides them."""
        def number(label: str) -> float | None:
            found = re.search(rf"{label}\s*[:=]\s*(\d+(?:\.\d+)?)\s*%?", output, re.IGNORECASE)
            return float(found.group(1)) if found else None
        temperature = re.search(r"(?:temperature|temp)\s*[:=]\s*(\d+(?:\.\d+)?)", output, re.IGNORECASE)
        return HealthReading(number("cpu(?: utilization)?"), number("memory(?: utilization)?"), float(temperature.group(1)) if temperature else None)

    @staticmethod
    def interfaces(output: str) -> list[InterfaceReading]:
        """Parse simple `interface status [description]` rows."""
        readings: list[InterfaceReading] = []
        for line in output.splitlines():
            match = re.match(r"^\s*([\w/-]+)\s+(up|down|administratively down)\b\s*(.*)$", line, re.IGNORECASE)
            if match:
                readings.append(InterfaceReading(match.group(1), match.group(2).lower(), match.group(3) or None))
        return readings

    @staticmethod
    def neighbors(output: str) -> list[NeighborReading]:
        """Parse common three-column LLDP neighbor rows."""
        readings: list[NeighborReading] = []
        for line in output.splitlines():
            match = re.match(r"^\s*([\w/-]+)\s+([\w.-]+)(?:\s+([\w/-]+))?\s*$", line)
            if match and match.group(1).lower() not in {"local", "interface"}:
                readings.append(NeighborReading(match.group(1), match.group(2), match.group(3)))
        return readings
