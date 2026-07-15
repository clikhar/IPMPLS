"""Tests for offline configuration safety logic."""
from crtnm.application.configuration_service import ConfigurationService
from crtnm.application.audit_service import AuditService


def test_redacts_secrets_before_persistence() -> None:
    content = "username ops password secret-value\nsnmp community public\ninterface ge0/0"
    clean = ConfigurationService(AuditService())._sanitize(content)
    assert "secret-value" not in clean
    assert "public" not in clean
    assert "interface ge0/0" in clean
