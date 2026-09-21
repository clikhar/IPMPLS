"""Domain enumerations for CRTNM."""
from enum import StrEnum


class UserRole(StrEnum):
    SUPER_ADMIN = "super_admin"
    NETWORK_ADMIN = "network_admin"
    NETWORK_ENGINEER = "network_engineer"
    OPERATOR = "operator"
    VIEWER = "viewer"
    AUDITOR = "auditor"


class DeviceType(StrEnum):
    LER = "ler"
    LSR = "lsr"
    L3_SWITCH = "l3_switch"
    L2_SWITCH = "l2_switch"
    ACCESS_SWITCH = "access_switch"
    POE_SWITCH = "poe_switch"
    ROUTER = "router"
    MPLS_ROUTER = "mpls_router"
    GPON_OLT = "gpon_olt"
    GPON_ONU = "gpon_onu"
    IP_PHONE = "ip_phone"
    VOIP_GATEWAY = "voip_gateway"
    FXS_GATEWAY = "fxs_gateway"
    SERVER = "server"
    UPS = "ups"
    CCTV = "cctv"
    WIRELESS_AP = "wireless_ap"
    WIRELESS_CONTROLLER = "wireless_controller"
    FIREWALL = "firewall"
    GENERIC_SNMP = "generic_snmp"
    OTHER = "other"


class DeviceStatus(StrEnum):
    UNKNOWN = "unknown"
    REACHABLE = "reachable"
    UNREACHABLE = "unreachable"
    SNMP_UNAVAILABLE = "snmp_unavailable"
    AUTH_FAILURE = "auth_failure"
    MAINTENANCE = "maintenance"


class SnmpVersion(StrEnum):
    V1 = "v1"
    V2C = "v2c"
    V3 = "v3"


class SnmpV3AuthProtocol(StrEnum):
    MD5 = "md5"
    SHA = "sha"
    SHA256 = "sha256"


class SnmpV3PrivProtocol(StrEnum):
    DES = "des"
    AES = "aes"
    AES256 = "aes256"


class InterfaceStatus(StrEnum):
    UP = "up"
    DOWN = "down"
    TESTING = "testing"
    UNKNOWN = "unknown"
    DORMANT = "dormant"
    NOT_PRESENT = "not_present"
    LOWER_LAYER_DOWN = "lower_layer_down"


class AlarmSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    MINOR = "minor"
    MAJOR = "major"
    CRITICAL = "critical"


class AlarmStatus(StrEnum):
    NORMAL = "normal"
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    SUPPRESSED = "suppressed"
    RESOLVED = "resolved"
    CLEARED = "cleared"


class EventType(StrEnum):
    LINK_DOWN = "link_down"
    LINK_UP = "link_up"
    DEVICE_DOWN = "device_down"
    DEVICE_UP = "device_up"
    CPU_HIGH = "cpu_high"
    MEMORY_HIGH = "memory_high"
    TEMPERATURE_HIGH = "temperature_high"
    POWER_FAILURE = "power_failure"
    FAN_FAILURE = "fan_failure"
    BGP_NEIGHBOR_DOWN = "bgp_neighbor_down"
    BGP_NEIGHBOR_UP = "bgp_neighbor_up"
    OSPF_NEIGHBOR_DOWN = "ospf_neighbor_down"
    OSPF_NEIGHBOR_UP = "ospf_neighbor_up"
    ISIS_NEIGHBOR_DOWN = "isis_neighbor_down"
    ISIS_NEIGHBOR_UP = "isis_neighbor_up"
    LDP_NEIGHBOR_DOWN = "ldp_neighbor_down"
    LDP_NEIGHBOR_UP = "ldp_neighbor_up"
    CONFIG_CHANGED = "config_changed"
    STP_TOPOLOGY_CHANGE = "stp_topology_change"
    AUTHENTICATION_FAILURE = "authentication_failure"
    SNMP_TRAP = "snmp_trap"
    SYSLOG = "syslog"
    CUSTOM = "custom"


class NotificationChannelType(StrEnum):
    EMAIL = "email"
    TELEGRAM = "telegram"
    SLACK = "slack"
    TEAMS = "teams"
    SMS = "sms"
    WEBHOOK = "webhook"
    SYSLOG = "syslog"


class ProtocolType(StrEnum):
    SSH = "ssh"
    TELNET = "telnet"
    SNMP = "snmp"
    ICMP = "icmp"
    NETCONF = "netconf"
    RESTCONF = "restconf"
    HTTP = "http"
    HTTPS = "https"


class ConfigSourceType(StrEnum):
    RUNNING = "running"
    STARTUP = "startup"
    CANDIDATE = "candidate"
    ARCHIVED = "archived"


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class TopologyLayer(StrEnum):
    LAYER2 = "layer2"
    LAYER3 = "layer3"
    PHYSICAL = "physical"
    LOGICAL = "logical"
    MPLS = "mpls"


class DiscoveryStatus(StrEnum):
    DISCOVERED = "discovered"
    UNKNOWN = "unknown"
    REACHABLE = "reachable"
    UNREACHABLE = "unreachable"
    SNMP_UNAVAILABLE = "snmp_unavailable"
    AUTH_FAILURE = "auth_failure"
    NEW_DEVICE = "new_device"
    EXISTING_DEVICE = "existing_device"
    APPROVED = "approved"
    REJECTED = "rejected"

