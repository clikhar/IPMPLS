"""Station and device inventory use cases."""
import json
from sqlalchemy import select
from sqlalchemy.orm import Session
from crtnm.application.audit_service import AuditService
from crtnm.core.security import decrypt_secret, encrypt_secret
from crtnm.drivers.contracts import ConnectionProfile, DeviceFacts
from crtnm.drivers.registry import DriverRegistry
from crtnm.infrastructure.models import DeviceModel, StationModel


class InventoryService:
    """Owns inventory persistence and credential encryption."""

    def __init__(self, audit: AuditService) -> None:
        self._audit = audit

    def create_station(self, session: Session, actor: str, name: str, division: str, location: str | None) -> StationModel:
        """Add a station to the railway network registry."""
        station = StationModel(name=name, division=division, location=location)
        session.add(station)
        self._audit.record(session, actor, "station.create", name)
        session.commit()
        session.refresh(station)
        return station

    def create_device(self, session: Session, actor: str, data: dict[str, str | int | None]) -> DeviceModel:
        """Add a device and encrypt its supplied credential before storage."""
        station = session.get(StationModel, data["station_id"])
        if station is None:
            raise LookupError("Station does not exist")
        password = data.pop("password", None)
        enable_password = data.pop("enable_password", None)
        ciphertext = encrypt_secret(json.dumps({"password": password, "enable_password": enable_password})) if password else None
        device = DeviceModel(**data, credential_ciphertext=ciphertext)
        session.add(device)
        self._audit.record(session, actor, "device.create", str(data["name"]), f"Station: {station.name}")
        session.commit()
        session.refresh(device)
        return device

    def list_stations(self, session: Session) -> list[StationModel]:
        return list(session.scalars(select(StationModel).order_by(StationModel.name)))

    def list_devices(self, session: Session) -> list[DeviceModel]:
        return list(session.scalars(select(DeviceModel).order_by(DeviceModel.name)))

    def get_device(self, session: Session, device_id: int) -> DeviceModel:
        """Return a single device."""
        device = session.get(DeviceModel, device_id)
        if device is None:
            raise LookupError("Device does not exist")
        return device


    def update_device(
        self,
        session: Session,
        actor: str,
        device_id: int,
        data: dict[str, str | int | None],
    ) -> DeviceModel:
        """Update an existing device and optionally replace stored credentials."""

        device = session.get(DeviceModel, device_id)
        if device is None:
            raise LookupError("Device does not exist")

        station = session.get(StationModel, data["station_id"])
        if station is None:
            raise LookupError("Station does not exist")

        device.station_id = data["station_id"]
        device.name = data["name"]
        device.device_type = data["device_type"]
        device.vendor = data["vendor"]
        device.management_ip = data["management_ip"]
        device.protocol = data["protocol"]
        device.connection_username = data["connection_username"]

        if "port" in data:
            device.port = data["port"]

        password = data.pop("password", None)
        enable_password = data.pop("enable_password", None)

        if password:
            device.credential_ciphertext = encrypt_secret(
                json.dumps(
                    {
                        "password": password,
                        "enable_password": enable_password,
                    }
                )
            )

        session.commit()
        session.refresh(device)

        self._audit.record(
            session,
            actor,
            "device.update",
            device.name,
            f"Station: {station.name}",
        )

        session.commit()

        return device


    def delete_device(
        self,
        session: Session,
        actor: str,
        device_id: int,
    ) -> None:
        """Delete a device from inventory."""

        device = session.get(DeviceModel, device_id)

        if device is None:
            raise LookupError("Device does not exist")

        name = device.name

        session.delete(device)

        self._audit.record(
            session,
            actor,
            "device.delete",
            name,
        )

        session.commit()

    def test_device(self, session: Session, actor: str, device_id: int, registry: DriverRegistry) -> DeviceFacts:
        """Use the device's driver to perform a controlled read-only connection test."""
        device = session.get(DeviceModel, device_id)
        if device is None:
            raise LookupError("Device does not exist")
        if not device.connection_username or not device.credential_ciphertext:
            raise ValueError("Device has no connection credentials configured")
        secrets = json.loads(decrypt_secret(device.credential_ciphertext))
        profile = ConnectionProfile(host=device.management_ip, username=device.connection_username, password=secrets["password"], enable_password=secrets.get("enable_password"), protocol=device.protocol)
        try:
            return registry.resolve(device.vendor).test_connection(profile)
        finally:
            self._audit.record(session, actor, "device.connection_test", device.name, "Read-only show version test requested")
            session.commit()

    def execute_readonly(self, session: Session, actor: str, device_id: int, command: str, registry: DriverRegistry) -> str:
        """Run a driver-allow-listed show command and create an audit event."""
        device = session.get(DeviceModel, device_id)
        if device is None:
            raise LookupError("Device does not exist")
        if not device.connection_username or not device.credential_ciphertext:
            raise ValueError("Device has no connection credentials configured")
        secrets = json.loads(decrypt_secret(device.credential_ciphertext))
        profile = ConnectionProfile(host=device.management_ip, username=device.connection_username, password=secrets["password"], enable_password=secrets.get("enable_password"), protocol=device.protocol)
        try:
            return registry.resolve(device.vendor).execute_readonly(profile, command)
        finally:
            self._audit.record(session, actor, "device.readonly_command", device.name, f"Command: {command}")
            session.commit()
