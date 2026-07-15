"""Read-only monitoring collection and alarm evaluation."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from crtnm.application.audit_service import AuditService
from crtnm.application.configuration_service import ConfigurationService
from crtnm.application.monitoring_parser import MonitoringParser
from crtnm.drivers.registry import DriverRegistry
from crtnm.infrastructure.models import AlarmModel, DeviceModel, HealthSnapshotModel, InterfaceStatusModel, LldpNeighborModel


class MonitoringService:
    """Collects telemetry with no configuration-changing device interaction."""

    def __init__(self, audit: AuditService) -> None:
        self._audit = audit

    def poll(self, session: Session, actor: str, device_id: int, registry: DriverRegistry) -> HealthSnapshotModel:
        """Collect supported health, interface, and LLDP views from one device."""
        device = session.get(DeviceModel, device_id)
        if device is None:
            raise LookupError("Device does not exist")
        profile = ConfigurationService._profile(device)
        driver = registry.resolve(device.vendor)
        health = MonitoringParser.health(driver.execute_readonly(profile, "show system"))
        interfaces = MonitoringParser.interfaces(driver.execute_readonly(profile, "show interface"))
        neighbors = MonitoringParser.neighbors(driver.execute_readonly(profile, "show lldp neighbors"))
        snapshot = HealthSnapshotModel(device_id=device_id, cpu_percent=health.cpu_percent, memory_percent=health.memory_percent, temperature_celsius=health.temperature_celsius, reachable=True)
        session.add(snapshot)
        session.query(InterfaceStatusModel).filter(InterfaceStatusModel.device_id == device_id).delete()
        session.query(LldpNeighborModel).filter(LldpNeighborModel.device_id == device_id).delete()
        session.add_all([InterfaceStatusModel(device_id=device_id, interface_name=item.name, status=item.status, description=item.description) for item in interfaces])
        session.add_all([LldpNeighborModel(device_id=device_id, local_interface=item.local_interface, neighbor_name=item.neighbor, neighbor_interface=item.neighbor_interface) for item in neighbors])
        self._raise_threshold_alarms(session, device, health.cpu_percent, health.memory_percent, health.temperature_celsius)
        self._audit.record(session, actor, "monitoring.poll", device.name, "Read-only health, interface, and LLDP collection")
        session.commit(); session.refresh(snapshot)
        return snapshot

    def summary(self, session: Session) -> dict[str, int]:
        """Return dashboard counts derived from persisted monitoring state."""
        devices = session.scalar(select(func.count(DeviceModel.id))) or 0
        connected = session.scalar(select(func.count(func.distinct(HealthSnapshotModel.device_id))).where(HealthSnapshotModel.reachable.is_(True))) or 0
        alarms = session.scalar(select(func.count(AlarmModel.id)).where(AlarmModel.status == "open")) or 0
        return {"devices": devices, "connected": connected, "disconnected": max(0, devices - connected), "open_alarms": alarms}

    @staticmethod
    def interfaces(session: Session, device_id: int) -> list[InterfaceStatusModel]:
        """Return the latest persisted interface table for a device."""
        return list(session.scalars(select(InterfaceStatusModel).where(InterfaceStatusModel.device_id == device_id).order_by(InterfaceStatusModel.interface_name)))

    @staticmethod
    def alarms(session: Session) -> list[AlarmModel]:
        """Return open alarms ordered by newest first."""
        return list(session.scalars(select(AlarmModel).where(AlarmModel.status == "open").order_by(AlarmModel.id.desc())))

    @staticmethod
    def topology(session: Session) -> dict[str, object]:
        """Provide device and LLDP edge data for the visual topology view."""
        devices = list(session.scalars(select(DeviceModel).order_by(DeviceModel.name)))
        names = {device.name.lower(): device.id for device in devices}
        edges = []
        for neighbor in session.scalars(select(LldpNeighborModel)):
            target_id = names.get(neighbor.neighbor_name.lower())
            if target_id and target_id != neighbor.device_id:
                edges.append({"source": neighbor.device_id, "target": target_id, "label": neighbor.local_interface})
        return {"nodes": [{"id": device.id, "name": device.name, "vendor": device.vendor, "type": device.device_type, "ip": device.management_ip} for device in devices], "edges": edges}

    def _raise_threshold_alarms(self, session: Session, device: DeviceModel, cpu: float | None, memory: float | None, temperature: float | None) -> None:
        thresholds = (("cpu", cpu, 85), ("memory", memory, 85), ("temperature", temperature, 70))
        for metric, value, threshold in thresholds:
            if value is not None and value >= threshold:
                existing = session.scalar(select(AlarmModel).where(AlarmModel.device_id == device.id, AlarmModel.metric == metric, AlarmModel.status == "open"))
                if existing is None:
                    session.add(AlarmModel(device_id=device.id, metric=metric, severity="critical" if value >= threshold + 10 else "warning", message=f"{metric.title()} threshold exceeded: {value}"))
