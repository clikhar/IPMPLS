"""NEON CPU utilization parser."""

from __future__ import annotations

import re
from typing import Any


def parse_cpu(output: str) -> dict[str, Any]:
    """
    Parse output from:

        show cpu-utilization
    """

    result: dict[str, Any] = {
        "threshold_percent": None,
        "recovering_threshold_percent": None,
        "observation_interval_seconds": None,
        "overall": {},
        "processors": [],
    }

    match = re.search(
        r"Rising\s+threshold:\s*(\d+)",
        output,
        re.IGNORECASE,
    )

    if match:
        result["threshold_percent"] = int(match.group(1))

    match = re.search(
        r"Recovering\s+threshold:\s*(\d+)",
        output,
        re.IGNORECASE,
    )

    if match:
        result["recovering_threshold_percent"] = int(
            match.group(1)
        )

    match = re.search(
        r"Trap transfer observation interval\(second\):\s*(\d+)",
        output,
        re.IGNORECASE,
    )

    if match:
        result["observation_interval_seconds"] = int(
            match.group(1)
        )

    periods = {
        "one_second": r"Last 1 second CPU utilization:\s*(\d+)%",
        "five_seconds": r"Last 5 seconds CPU utilization:\s*(\d+)%",
        "one_minute": r"Last 1 minute CPU utilization:\s*(\d+)%",
        "five_minutes": r"Last 5 minute CPU utilization:\s*(\d+)%",
        "ten_minutes": r"Last 10 minutes CPU utilization:\s*(\d+)%",
        "two_hours": r"Last 2 hours CPU utilization:\s*(\d+)%",
    }

    for name, pattern in periods.items():

        match = re.search(
            pattern,
            output,
            re.IGNORECASE,
        )

        if match:
            result["overall"][name] = int(
                match.group(1)
            )

    processor_pattern = re.compile(
        r"^\s*(\d+)\s+"
        r"(\d+)%\s+"
        r"(\d+)%\s+"
        r"(\d+)%\s+"
        r"(\d+)%\s+"
        r"(\d+)%\s+"
        r"(\d+)%\s*$",
        re.MULTILINE,
    )

    for match in processor_pattern.finditer(output):

        result["processors"].append(
            {
                "id": int(match.group(1)),
                "one_second": int(match.group(2)),
                "five_seconds": int(match.group(3)),
                "one_minute": int(match.group(4)),
                "five_minutes": int(match.group(5)),
                "ten_minutes": int(match.group(6)),
                "two_hours": int(match.group(7)),
            }
        )

    return result