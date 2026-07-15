"""Tests for safe monitoring output parsing."""
from crtnm.application.monitoring_parser import MonitoringParser


def test_extracts_health_metrics() -> None:
    result = MonitoringParser.health("CPU utilization: 87%\nMemory: 61%\nTemperature: 47.5 C")
    assert (result.cpu_percent, result.memory_percent, result.temperature_celsius) == (87.0, 61.0, 47.5)


def test_extracts_interfaces_and_neighbors() -> None:
    assert MonitoringParser.interfaces("ge0/1 up Uplink\nge0/2 down") [0].description == "Uplink"
    assert MonitoringParser.neighbors("ge0/1 Core-RTR ge0/48")[0].neighbor == "Core-RTR"
