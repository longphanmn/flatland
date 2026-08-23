"""God passkey: shared-secret gate for laws, presets and world control.

First boot has no credential — `POST /api/auth/setup` registers one (the
frontend prompts for it). Afterwards every god-touching call must present the
passkey (`X-God-Key` header on REST, `key` field on WebSocket control
messages). Only a PBKDF2 hash is stored, in the `settings` table; clearing the
database wipes the credential and the next start asks to create it again.

`FLATWORLD_GOD_KEY` seeds (or overrides) the passkey from the environment —
handy for headless deploys and tests.
"""

import hashlib
import hmac
import os
import secrets

from fastapi import HTTPException, Request
from pydantic import BaseModel

from .db import Database

_PBKDF2_ITERATIONS = 120_000
_SETTING_HASH = "god_passkey_hash"
_SETTING_SALT = "god_passkey_salt"
MIN_PASSKEY_LEN = 4


def _hash(passkey: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", passkey.encode("utf-8"), salt, _PBKDF2_ITERATIONS
    ).hex()


class PasskeyAuth:
    """Lazily-loaded passkey state backed by the settings table."""

    def __init__(self, db: Database):
        self._db = db
        self._loaded = False
        self._hash_hex: str | None = None
        self._salt_hex: str | None = None
        env_key = os.environ.get("FLATWORLD_GOD_KEY")
        if env_key:
            # Environment wins: deterministic credential for headless runs.
            salt = secrets.token_bytes(16)
            self._salt_hex = salt.hex()
            self._hash_hex = _hash(env_key, salt)
            self._loaded = True

    def _load(self) -> None:
        if not self._loaded:
            self._salt_hex = self._db.get_setting(_SETTING_SALT)
            self._hash_hex = self._db.get_setting(_SETTING_HASH)
            self._loaded = True

    def configured(self) -> bool:
        self._load()
        return self._hash_hex is not None and self._salt_hex is not None

    def setup(self, passkey: str) -> None:
        """Register the first credential. Refuses if one already exists."""
        if len(passkey) < MIN_PASSKEY_LEN:
            raise ValueError(f"passkey must be at least {MIN_PASSKEY_LEN} characters")
        if self.configured():
            raise PermissionError("a god passkey already exists")
        self._write(passkey)

    def reset(self, passkey: str) -> None:
        """Overwrite any existing credential (admin recovery via CLI only)."""
        if len(passkey) < MIN_PASSKEY_LEN:
            raise ValueError(f"passkey must be at least {MIN_PASSKEY_LEN} characters")
        self._write(passkey)

    def clear(self) -> None:
        """Remove the credential entirely — next start asks to enroll again."""
        self._db.delete_setting(_SETTING_HASH)
        self._db.delete_setting(_SETTING_SALT)
        self._hash_hex = None
        self._salt_hex = None
        self._loaded = True

    def _write(self, passkey: str) -> None:
        salt = secrets.token_bytes(16)
        self._db.set_setting(_SETTING_SALT, salt.hex())
        self._db.set_setting(_SETTING_HASH, _hash(passkey, salt))
        self._salt_hex = salt.hex()
        self._hash_hex = _hash(passkey, salt)
        self._loaded = True

    def verify(self, passkey: str | None) -> bool:
        if not passkey or not self.configured():
            return False
        calc = _hash(passkey, bytes.fromhex(self._salt_hex or ""))
        return hmac.compare_digest(calc, self._hash_hex or "")


class SetupPasskey(BaseModel):
    passkey: str


def require_god(request: Request) -> None:
    """FastAPI dependency guarding every god-touching endpoint."""
    auth: PasskeyAuth = request.app.state.god_auth
    if not auth.configured():
        raise HTTPException(
            409,
            {
                "error": "god_key_not_configured",
                "detail": "no god passkey exists yet — POST /api/auth/setup first",
            },
        )
    key = request.headers.get("X-God-Key") or request.query_params.get("key")
    if not auth.verify(key):
        raise HTTPException(401, {"error": "god_key_required", "detail": "valid X-God-Key header required"})
