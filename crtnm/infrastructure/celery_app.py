"""Celery application for asynchronous read-only network operations."""
from celery import Celery
from crtnm.core.config import get_settings

settings = get_settings()
celery_app = Celery("crtnm", broker=settings.celery_broker_url, backend=settings.celery_result_backend, include=["crtnm.infrastructure.tasks"])
celery_app.conf.update(task_serializer="json", result_serializer="json", accept_content=["json"], timezone="Asia/Kolkata", enable_utc=True, task_acks_late=True, worker_prefetch_multiplier=1, beat_schedule={"poll-managed-devices-every-five-minutes": {"task": "crtnm.poll_all_devices", "schedule": 300.0}})
