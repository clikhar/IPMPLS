"""NEON memory utilization parser."""

from __future__ import annotations

import re
from typing import Any


def parse_memory(output: str) -> dict[str, Any]:
    """
    Parse output from:

        show memory

    NEON reports memory values in kB.
    """

    result: dict[str, Any] = {
        "total_kb": None,
        "free_kb": None,
        "used_kb": None,
        "utilization_percent": None,
        "threshold_percent": None,
        "recover_threshold_percent": None,
        "interval_seconds": None,
    }

    match = re.search(
        r"memory utilization threshold\s*:\s*(\d+)%?",
        output,
        re.IGNORECASE,
    )

    if match:
        result["threshold_percent"] = int(match.group(1))

    match = re.search(
        r"memory utilization thresholdrecover\s*:\s*(\d+)%?",
        output,
        re.IGNORECASE,
    )

    if match:
        result["recover_threshold_percent"] = int(match.group(1))

    match = re.search(
        r"memory interval\(second\)\s*:\s*(\d+)",
        output,
        re.IGNORECASE,
    )

    if match:
        result["interval_seconds"] = int(match.group(1))

    match = re.search(
        r"^\s*(\d+)\s+(\d+)\s+(\d+)\s*$",
        output,
        re.MULTILINE,
    )

    if match:
        result["total_kb"] = int(match.group(1))
        result["free_kb"] = int(match.group(2))
        result["used_kb"] = int(match.group(3))

    match = re.search(
        r"memory utilization\s*:\s*([\d.]+)%",
        output,
        re.IGNORECASE,
    )

    if match:
        result["utilization_percent"] = float(
            match.group(1)
        )

    return result