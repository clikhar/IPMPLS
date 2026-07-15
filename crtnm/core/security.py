"""Password hashing, encryption, and JSON Web Token helpers."""
from datetime import UTC, datetime, timedelta
from typing import Any
import base64
import hashlib
import hmac
import os
import jwt
from cryptography.fernet import Fernet
from crtnm.core.config import get_settings


def hash_password(password: str) -> str:
    """Derive a password hash using PBKDF2-HMAC-SHA256."""
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 600_000)
    return f"{base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a submitted password without timing leaks."""
    try:
        salt_text, digest_text = stored_hash.split("$", 1)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), base64.b64decode(salt_text), 600_000)
        return hmac.compare_digest(base64.b64encode(digest).decode(), digest_text)
    except (ValueError, TypeError):
        return False


def create_access_token(subject: str, role: str) -> str:
    """Create a short-lived signed access token."""
    settings = get_settings()
    payload: dict[str, Any] = {"sub": subject, "role": role, "exp": datetime.now(UTC) + timedelta(minutes=settings.token_expiry_minutes)}
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_access_token(token: str) -> dict[str, Any]:
    """Validate a signed access token."""
    return jwt.decode(token, get_settings().secret_key, algorithms=["HS256"])


def encrypt_secret(value: str) -> str:
    """Encrypt a credential before persistence."""
    key = get_settings().fernet_key
    if not key:
        raise RuntimeError("CRTNM_FERNET_KEY must be configured before storing credentials")
    return Fernet(key.encode()).encrypt(value.encode()).decode()


def decrypt_secret(value: str) -> str:
    """Decrypt a persisted credential only immediately before connection use."""
    key = get_settings().fernet_key
    if not key:
        raise RuntimeError("CRTNM_FERNET_KEY must be configured before using credentials")
    return Fernet(key.encode()).decrypt(value.encode()).decode()
