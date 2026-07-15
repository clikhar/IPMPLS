"""Immutable backup, comparison, and non-executing recovery planning use cases."""
import difflib
import hashlib
import json
import re
from sqlalchemy import select
from sqlalchemy.orm import Session
from crtnm.application.audit_service import AuditService
from crtnm.core.security import decrypt_secret
from crtnm.drivers.contracts import ConnectionProfile
from crtnm.drivers.registry import DriverRegistry
from crtnm.infrastructure.models import ConfigurationBackupModel, DeviceModel, RecoverySimulationModel

_SECRET_LINE = re.compile(r"(?im)^(.*(?:password|secret|community|key)\s+)(\S+.*)$")


class ConfigurationService:
    """Keeps configuration data versioned, sanitized, and safe to review."""

    def __init__(self, audit: AuditService) -> None:
        self._audit = audit

    @staticmethod
    def _sanitize(configuration: str) -> str:
        """Redact inline secrets before configurations enter application storage."""
        return _SECRET_LINE.sub(r"\1<redacted>", configuration)

    @staticmethod
    def _profile(device: DeviceModel) -> ConnectionProfile:
        if not device.connection_username or not device.credential_ciphertext:
            raise ValueError("Device has no connection credentials configured")
        secrets = json.loads(decrypt_secret(device.credential_ciphertext))
        return ConnectionProfile(host=device.management_ip, username=device.connection_username, password=secrets["password"], enable_password=secrets.get("enable_password"), protocol=device.protocol)

    def capture_running(self, session: Session, actor: str, device_id: int, registry: DriverRegistry) -> ConfigurationBackupModel:
        """Retrieve and persist a sanitized running configuration as a new version."""
        device = self._device(session, device_id)
        raw = registry.resolve(device.vendor).execute_readonly(self._profile(device), "show running-config")
        content = self._sanitize(raw)
        checksum = hashlib.sha256(content.encode()).hexdigest()
        backup = ConfigurationBackupModel(device_id=device_id, content=content, checksum=checksum, created_by=actor)
        session.add(backup)
        self._audit.record(session, actor, "configuration.backup", device.name, f"SHA-256: {checksum}")
        session.commit(); session.refresh(backup)
        return backup

    def list_backups(self, session: Session, device_id: int) -> list[ConfigurationBackupModel]:
        """List immutable versions newest first."""
        self._device(session, device_id)
        return list(session.scalars(select(ConfigurationBackupModel).where(ConfigurationBackupModel.device_id == device_id).order_by(ConfigurationBackupModel.id.desc())))

    def compare(self, session: Session, left_id: int, right_id: int) -> str:
        """Produce a standard unified diff between two stored snapshots."""
        left, right = self._backup(session, left_id), self._backup(session, right_id)
        if left.device_id != right.device_id:
            raise ValueError("Configurations from different devices cannot be compared")
        return "\n".join(difflib.unified_diff(left.content.splitlines(), right.content.splitlines(), fromfile=f"backup-{left.id}", tofile=f"backup-{right.id}", lineterm=""))

    def restore_preview(self, session: Session, actor: str, backup_id: int) -> dict[str, object]:
        """Generate a reviewable restore plan without sending a device command."""
        backup = self._backup(session, backup_id)
        device = self._device(session, backup.device_id)
        plan = ["conf t", "! Apply reviewed backup content through an approved change window", "end", "write"]
        self._audit.record(session, actor, "configuration.restore_preview", device.name, f"Backup: {backup.id}")
        session.commit()
        return {"device_id": device.id, "backup_id": backup.id, "checksum": backup.checksum, "commands": plan, "configuration": backup.content}

    def simulate_recovery(self, session: Session, actor: str, device_id: int, failure_type: str, backup_id: int | None) -> RecoverySimulationModel:
        """Record a recovery plan; simulation deliberately has no network side effects."""
        device = self._device(session, device_id)
        backup = self._backup(session, backup_id) if backup_id else session.scalar(select(ConfigurationBackupModel).where(ConfigurationBackupModel.device_id == device_id).order_by(ConfigurationBackupModel.id.desc()))
        if backup is not None and backup.device_id != device_id:
            raise ValueError("Backup does not belong to selected device")
        steps = ["Validate incident approval", "Verify backup checksum", "Establish out-of-band access", "Preview configuration restore", "Require a second administrator confirmation", "Execute in a separately approved change window", "Validate services and retain rollback snapshot"]
        simulation = RecoverySimulationModel(device_id=device_id, failure_type=failure_type, backup_id=backup.id if backup else None, execution_plan=json.dumps(steps), created_by=actor)
        session.add(simulation)
        self._audit.record(session, actor, "recovery.simulation", device.name, f"Failure: {failure_type}; backup: {simulation.backup_id}")
        session.commit(); session.refresh(simulation)
        return simulation

    @staticmethod
    def _device(session: Session, device_id: int) -> DeviceModel:
        device = session.get(DeviceModel, device_id)
        if device is None:
            raise LookupError("Device does not exist")
        return device

    @staticmethod
    def _backup(session: Session, backup_id: int | None) -> ConfigurationBackupModel:
        backup = session.get(ConfigurationBackupModel, backup_id)
        if backup is None:
            raise LookupError("Configuration backup does not exist")
        return backup
