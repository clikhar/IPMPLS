"""Station and device inventory use cases."""
import json,time
from sqlalchemy import select
from sqlalchemy.orm import Session
from crtnm.application.audit_service import AuditService
from crtnm.core.security import decrypt_secret, encrypt_secret
from crtnm.drivers.contracts import (ConnectionProfile, DeviceFacts,)
from crtnm.drivers.registry import DriverRegistry
from crtnm.drivers.exceptions import DriverError
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

    def collect_facts(self,session: Session,actor: str,device_id: int,registry: DriverRegistry,) -> dict:
        """
        Collect structured operational facts from the device's
        vendor driver.

        Credentials are decrypted only for the duration of the
        connection operation and are never returned or logged.
        """

        device = session.get(
            DeviceModel,
            device_id,
        )

        if device is None:
            raise LookupError(
                "Device does not exist"
            )

        if (
            not device.connection_username
            or not device.credential_ciphertext
        ):
            raise ValueError(
                "Device has no connection credentials configured"
            )

        secrets = json.loads(
            decrypt_secret(
                device.credential_ciphertext
            )
        )

        profile = ConnectionProfile(
            host=device.management_ip,
            username=device.connection_username,
            password=secrets["password"],
            enable_password=secrets.get(
                "enable_password"
            ),
            protocol=device.protocol,
            
        )

        try:
            driver = registry.resolve(
                device.vendor
            )

            # The structured collector is intentionally
            # vendor-specific behind the driver boundary.
            if not hasattr(driver, "collect_facts"):
                raise DriverError(
                    f"Driver '{device.vendor}' "
                    "does not support structured fact collection"
                )

            facts = driver.collect_facts(
                profile
            )

            return {
                "device_id": device.id,
                "name": device.name,
                "management_ip": device.management_ip,
                "vendor": device.vendor,
                "device_type": str(
                    device.device_type
                ),
                "facts": facts,
            }

        finally:
            self._audit.record(
                session,
                actor,
                "device.facts_collect",
                device.name,
                "Collected structured read-only device facts",
            )

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

    def execute_readonly_many(self,session: Session,actor: str,device_id: int,commands: list[str],registry: DriverRegistry,) -> tuple[list[dict[str, object]], float]:
        """Execute multiple driver-approved read-only commands.
        Credentials are decrypted only for the duration of the operation.
        The command output itself is returned to the caller but credentials are never included in the audit record."""

        device = session.get(DeviceModel, device_id)

        if device is None:
            raise LookupError("Device does not exist")

        if (
            not device.connection_username
            or not device.credential_ciphertext
        ):
            raise ValueError(
                "Device has no connection credentials configured"
            )

        if not commands:
            raise ValueError(
                "At least one command is required"
            )

        if len(commands) > 10:
            raise ValueError(
                "A maximum of 10 commands can be executed at once"
            )

        normalized_commands = [
            command.strip()
            for command in commands
            if command.strip()
        ]

        if not normalized_commands:
            raise ValueError(
                "At least one non-empty command is required"
            )

        secrets = json.loads(
            decrypt_secret(
                device.credential_ciphertext
            )
        )

        profile = ConnectionProfile(
            host=device.management_ip,
            username=device.connection_username,
            password=secrets["password"],
            enable_password=secrets.get("enable_password"),
            protocol=device.protocol,
            port=getattr(device, "port", None),
        )

        start_time = time.perf_counter()

        try:

            driver = registry.resolve(
                device.vendor
            )

            results = driver.execute_readonly_many(
                profile,
                normalized_commands
            )

            execution_time = (
                time.perf_counter() - start_time
            )

            successful = all(
                bool(result["success"])
                for result in results
            )

            self._audit.record(
                session,
                actor,
                "device.readonly_commands",
                device.name,
                (
                    "Commands: "
                    + ", ".join(normalized_commands)
                ),
            )

            session.commit()

            return results, execution_time

        except Exception:

            execution_time = (
                time.perf_counter() - start_time
            )

            self._audit.record(
                session,
                actor,
                "device.readonly_commands.failed",
                device.name,
                (
                    "Commands: "
                    + ", ".join(normalized_commands)
                ),
            )

            session.commit()

            raise