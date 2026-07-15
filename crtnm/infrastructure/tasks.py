"""Background polling tasks; tasks never issue configuration commands."""
import logging
from celery import shared_task
from sqlalchemy import select
from crtnm.application.audit_service import AuditService
from crtnm.application.monitoring_service import MonitoringService
from crtnm.drivers import registry
from crtnm.drivers.neon import NeonDriver
from crtnm.infrastructure.database import SessionLocal
from crtnm.infrastructure.models import DeviceModel

logger = logging.getLogger(__name__)
if not registry.has("neon"):  # one-time worker process registration
    registry.register(NeonDriver())


@shared_task(name="crtnm.poll_device", autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 2})
def poll_device(device_id: int) -> None:
    """Collect read-only telemetry for one device in an isolated transaction."""
    with SessionLocal() as session:
        MonitoringService(AuditService()).poll(session, "system:celery", device_id, registry)


@shared_task(name="crtnm.poll_all_devices")
def poll_all_devices() -> int:
    """Queue monitored devices individually so one failure cannot block the fleet."""
    with SessionLocal() as session:
        ids = list(session.scalars(select(DeviceModel.id)))
    for device_id in ids: poll_device.delay(device_id)
    logger.info("Queued monitoring for %d devices", len(ids))
    return len(ids)
