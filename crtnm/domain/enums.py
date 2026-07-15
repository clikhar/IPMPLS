"""Stable domain enumerations."""
from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


class DeviceType(StrEnum):
    LER = "ler"
    L2_SWITCH = "l2_switch"
    L3_SWITCH = "l3_switch"
    GPON = "gpon"
    FXS_GATEWAY = "fxs_gateway"
    VOIP_GATEWAY = "voip_gateway"

