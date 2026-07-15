"""Tests for dry-run network command construction."""
import pytest
from crtnm.application.network_command_factory import NetworkCommandFactory
from crtnm.presentation.schemas import InterfacePlanCreate, VlanPlanCreate


def test_vlan_plan_is_explicit_and_nonexecuting() -> None:
    _, commands, _ = NetworkCommandFactory.vlan(VlanPlanCreate(vlan_id=100, name="VOICE", interface="ge0/1"))
    assert commands == ["conf t", "vlan 100", "name VOICE", "interface ge0/1", "switchport mode access", "switchport access vlan 100", "end", "write"]


def test_interface_description_requires_value() -> None:
    with pytest.raises(ValueError):
        NetworkCommandFactory.interface(InterfacePlanCreate(interface="ge0/1", action="description"))
