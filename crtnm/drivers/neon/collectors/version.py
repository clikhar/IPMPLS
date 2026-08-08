"""NEON show version parser."""

from __future__ import annotations

import re
from typing import Any


def _extract(pattern: str, output: str) -> str | None:
    """Extract the first matching value from command output."""
    normalized_output = "\n".join(
        line.strip()
        for line in output.splitlines()
    )

    match = re.search(
        pattern,
        normalized_output,
        flags=re.MULTILINE | re.IGNORECASE,
    )

    if not match:
        return None

    return match.group(1).strip()


def parse_version(output: str) -> dict[str, Any]:
    """
    Parse output from:

        show version

    Returns structured NEON device identity information.
    """

    result: dict[str, Any] = {
        "product_name": _extract(
            r"^Product Name:\s*(.+)$",
            output,
        ),
        "product_version": _extract(
            r"^Product Version:\s*(.+)$",
            output,
        ),
        "hardware_version": _extract(
            r"^Hardware Version:\s*(.+)$",
            output,
        ),
        "pcb_version": _extract(
            r"^PCB Version:\s*(.+)$",
            output,
        ),
        "software_version": _extract(
            r"^Software Version:\s*(.+)$",
            output,
        ),
        "neon_version": _extract(
            r"^NEON Version:\s*(.+)$",
            output,
        ),
        "bootrom_version": _extract(
            r"^Bootrom Version:\s*(.+)$",
            output,
        ),
        "cpld_version": _extract(
            r"^CPLD Version:\s*(.+)$",
            output,
        ),
        "fpga_version": _extract(
            r"^FPGA Version:\s*(.+)$",
            output,
        ),
        "fpga2_version": _extract(
            r"^FPGA2 Version:\s*(.+)$",
            output,
        ),
        "system_mac": _extract(
            r"^System MAC Address:\s*(.+)$",
            output,
        ),
        "serial_number": _extract(
            r"^Serial number:\s*(.+)$",
            output,
        ),
        "uptime": _extract(
            r"^System uptime is\s+(.+)$",
            output,
        ),
    }

    # NEON memory information.
    dram = re.search(
        r"^\s*(\d+)\s*([MG])\s+bytes\s+DRAM\s*$",
        output,
        flags=re.MULTILINE | re.IGNORECASE,
    )

    flash = re.search(
        r"^\s*(\d+)\s*([MG])\s+bytes\s+Flash Memory\s*$",
        output,
        flags=re.MULTILINE | re.IGNORECASE,
    )

    emmc = re.search(
        r"^\s*(\d+)\s*([MG])\s+bytes\s+eMMC\s*$",
        output,
        flags=re.MULTILINE | re.IGNORECASE,
    )

    result["memory"] = {
        "dram": (
            f"{dram.group(1)}{dram.group(2)}"
            if dram
            else None
        ),
        "flash": (
            f"{flash.group(1)}{flash.group(2)}"
            if flash
            else None
        ),
        "emmc": (
            f"{emmc.group(1)}{emmc.group(2)}"
            if emmc
            else None
        ),
    }

    return result