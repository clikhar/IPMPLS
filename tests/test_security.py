"""Unit tests for security primitives."""
from cryptography.fernet import Fernet
from crtnm.core.config import get_settings
from crtnm.core.security import create_access_token, decode_access_token, hash_password, verify_password


def test_password_hash_round_trip(monkeypatch) -> None:
    monkeypatch.setenv("CRTNM_SECRET_KEY", "test-secret")
    get_settings.cache_clear()
    assert verify_password("correct horse battery staple", hash_password("correct horse battery staple"))
    assert not verify_password("wrong password", hash_password("correct horse battery staple"))


def test_token_round_trip(monkeypatch) -> None:
    monkeypatch.setenv("CRTNM_SECRET_KEY", "test-secret")
    monkeypatch.setenv("CRTNM_FERNET_KEY", Fernet.generate_key().decode())
    get_settings.cache_clear()
    assert decode_access_token(create_access_token("7", "admin"))["sub"] == "7"

