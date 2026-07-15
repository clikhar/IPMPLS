"""Unit tests for the NEON driver safety parser."""
import pytest
from crtnm.drivers.exceptions import CommandRejected
from crtnm.drivers.neon.driver import NeonDriver
from crtnm.drivers.neon.prompts import contains_confirmation, find_prompt


def test_finds_operational_and_configuration_prompts() -> None:
    assert find_prompt("login complete\r\nRouter> ") == "Router>"
    assert find_prompt("Router(config-if)#\n") == "Router(config-if)#"


def test_detects_confirmation() -> None:
    assert contains_confirmation("Are you sure [y/n]")


def test_rejects_unapproved_commands() -> None:
    with pytest.raises(CommandRejected):
        NeonDriver().execute_readonly(object(), "write")  # type: ignore[arg-type]
