"""Per-site one-time supervisor capability tokens; QR workers remain anonymous."""
from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Any

from fastapi import HTTPException

from .config import DEMO_MODE


def create_site_access() -> tuple[str, str, str]:
    token = secrets.token_urlsafe(32)
    salt = secrets.token_hex(16)
    digest = hashlib.sha256(bytes.fromhex(salt) + token.encode()).hexdigest()
    return token, salt, digest


def verify_site_access(site: dict[str, Any], authorization: str | None) -> None:
    if site.get("demo_fixture") and DEMO_MODE:
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail={"error": "supervisor_token_required", "message": "Use the one-time site supervisor token returned at setup."})
    supplied = authorization.removeprefix("Bearer ").strip()
    salt = site.get("admin_token_salt")
    expected = site.get("admin_token_hash")
    if not salt or not expected:
        raise HTTPException(status_code=403, detail={"error": "site_access_not_configured", "message": "Supervisor access has not been configured for this site."})
    actual = hashlib.sha256(bytes.fromhex(str(salt)) + supplied.encode()).hexdigest()
    if not hmac.compare_digest(actual, str(expected)):
        raise HTTPException(status_code=403, detail={"error": "invalid_supervisor_token", "message": "The site supervisor token is invalid."})
