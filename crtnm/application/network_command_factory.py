"""NEON command preview generation for validated change requests."""
import ipaddress
from crtnm.presentation.schemas import InterfacePlanCreate, MplsPlanCreate, StaticRoutePlanCreate, VlanPlanCreate


class NetworkCommandFactory:
    """Converts typed change requests to transparent, reviewable NEON CLI commands."""

    @staticmethod
    def vlan(data: VlanPlanCreate) -> tuple[str, list[str], str]:
        commands = ["conf t", f"vlan {data.vlan_id}", f"name {data.name}"]
        if data.interface:
            commands.extend([f"interface {data.interface}", f"switchport mode {data.mode}", f"switchport {'access vlan' if data.mode == 'access' else 'trunk allowed vlan add'} {data.vlan_id}"])
        commands.extend(["end", "write"])
        return "vlan", commands, f"Create VLAN {data.vlan_id} ({data.name})"

    @staticmethod
    def interface(data: InterfacePlanCreate) -> tuple[str, list[str], str]:
        action = "no shutdown" if data.action == "no_shutdown" else data.action
        command = f"description {data.value}" if data.action == "description" else action
        if data.action == "description" and not data.value:
            raise ValueError("An interface description requires a value")
        return "interface", ["conf t", f"interface {data.interface}", command, "end", "write"], f"Interface {data.interface}: {data.action}"

    @staticmethod
    def static_route(data: StaticRoutePlanCreate) -> tuple[str, list[str], str]:
        try:
            ipaddress.ip_network(data.destination, strict=False)
        except ValueError as error:
            raise ValueError("Route destination must be a valid IPv4 network") from error
        prefix = f"ip route vrf {data.vrf}" if data.vrf else "ip route"
        return "static_route", ["conf t", f"{prefix} {data.destination} {data.next_hop}", "end", "write"], f"Add static route {data.destination} via {data.next_hop}"

    @staticmethod
    def mpls(data: MplsPlanCreate) -> tuple[str, list[str], str]:
        templates = {
            "vrf": [f"ip vrf {data.name}", f"rd {data.value}"],
            "loopback": [f"interface loopback {data.name}", f"ip address {data.value}"],
            "l2vpn": [f"l2vpn {data.name}", f"pseudowire {data.value}"],
            "l3vpn": [f"ip vrf {data.name}", f"route-target {data.value}"],
            "isis": [f"router isis {data.name}", f"net {data.value}"],
            "bgp": [f"router bgp {data.name}", f"neighbor {data.value}"],
            "ldp": ["mpls ldp", f"router-id {data.value}"],
            "pseudowire": [f"pseudowire {data.name}", f"peer {data.value}"],
        }
        return f"mpls_{data.service}", ["conf t", *templates[data.service], "end", "write"], f"Configure {data.service}: {data.name}"
