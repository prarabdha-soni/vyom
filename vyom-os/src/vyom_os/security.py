"""Passwords, session tokens and policy-table authorisation.

Standard library only: scrypt for passwords, HMAC-SHA256 signed tokens
(JWT compact form) for sessions. The token carries the tenant; every request
also sends ``X-Tenant-ID`` and a mismatch is refused.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import threading
import time
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

ISSUER = "vyom-os"
AUDIENCE = "vyom-console"
ROLES = ("reviewer", "safety_physician", "qppv", "admin", "ops")
MIN_PASSWORD_LENGTH = 12

_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1


class InvalidToken(ValueError):
    """Session token is malformed, tampered with or expired."""


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def hash_password(password: str) -> str:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Passwords must be at least {MIN_PASSWORD_LENGTH} characters")
    salt = os.urandom(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, dklen=32
    )
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, n, r, p, salt, digest = encoded.split("$")
        if scheme != "scrypt":
            return False
        expected = _unb64(digest)
        candidate = hashlib.scrypt(
            password.encode("utf-8"),
            salt=_unb64(salt),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(candidate, expected)


# Used when an email is unknown so a failed sign-in costs the same time.
_DUMMY_HASH = hash_password("not-a-real-password-placeholder")


def verify_password_or_dummy(password: str, encoded: str | None) -> bool:
    if encoded is None:
        verify_password(password, _DUMMY_HASH)
        return False
    return verify_password(password, encoded)


@dataclass(frozen=True)
class SessionClaims:
    user_id: str
    email: str
    role: str
    tenant_id: str
    tenant_slug: str
    issued_at: int
    expires_at: int


def issue_token(
    *,
    user_id: str,
    email: str,
    role: str,
    tenant_id: str,
    tenant_slug: str,
    secret: bytes,
    ttl_seconds: int,
    now: int | None = None,
) -> tuple[str, SessionClaims]:
    if role not in ROLES:
        raise ValueError("unknown role")
    issued = int(now if now is not None else time.time())
    claims = SessionClaims(
        user_id=user_id,
        email=email,
        role=role,
        tenant_id=tenant_id,
        tenant_slug=tenant_slug,
        issued_at=issued,
        expires_at=issued + ttl_seconds,
    )
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": user_id,
        "email": email,
        "role": role,
        "tid": tenant_id,
        "tsl": tenant_slug,
        "iat": claims.issued_at,
        "exp": claims.expires_at,
    }
    signing_input = f"{_b64(_json(header))}.{_b64(_json(payload))}"
    signature = hmac.new(secret, signing_input.encode("ascii"), hashlib.sha256).digest()
    return f"{signing_input}.{_b64(signature)}", claims


def verify_token(token: str, *, secret: bytes, now: int | None = None) -> SessionClaims:
    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
        header = json.loads(_unb64(header_b64))
        payload = json.loads(_unb64(payload_b64))
        signature = _unb64(signature_b64)
    except (ValueError, json.JSONDecodeError) as error:
        raise InvalidToken("malformed token") from error
    if header != {"alg": "HS256", "typ": "JWT"}:
        raise InvalidToken("unsupported token header")
    expected = hmac.new(
        secret, f"{header_b64}.{payload_b64}".encode("ascii"), hashlib.sha256
    ).digest()
    if not hmac.compare_digest(signature, expected):
        raise InvalidToken("bad signature")
    if payload.get("iss") != ISSUER or payload.get("aud") != AUDIENCE:
        raise InvalidToken("wrong issuer or audience")
    current = int(now if now is not None else time.time())
    try:
        expires_at = int(payload["exp"])
        issued_at = int(payload["iat"])
        claims = SessionClaims(
            user_id=str(payload["sub"]),
            email=str(payload["email"]),
            role=str(payload["role"]),
            tenant_id=str(payload["tid"]),
            tenant_slug=str(payload["tsl"]),
            issued_at=issued_at,
            expires_at=expires_at,
        )
    except (KeyError, TypeError, ValueError) as error:
        raise InvalidToken("incomplete claims") from error
    if current >= expires_at:
        raise InvalidToken("expired")
    if issued_at > current + 60:
        raise InvalidToken("issued in the future")
    if claims.role not in ROLES:
        raise InvalidToken("unknown role")
    return claims


def _json(value: Any) -> bytes:
    return json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")


class Authorizer:
    """Policy table semantics: any deny wins, otherwise an allow is required."""

    def __init__(self, rows: Iterable[tuple[str, str, str]]):
        self._allow: dict[str, set[str]] = {}
        self._deny: dict[str, set[str]] = {}
        for role, action, effect in rows:
            target = self._deny if effect == "deny" else self._allow
            target.setdefault(role, set()).add(action)

    def allowed(self, role: str, action: str) -> bool:
        if action in self._deny.get(role, set()):
            return False
        return action in self._allow.get(role, set())

    def permissions(self, role: str) -> list[str]:
        return sorted(self._allow.get(role, set()) - self._deny.get(role, set()))

    @classmethod
    def load(cls, connection: Any) -> Authorizer:
        with connection.cursor() as cursor:
            cursor.execute("select role, action, effect from authorization_policies")
            return cls(cursor.fetchall())


class SignInThrottle:
    """Per-email failure counter: five failures lock sign-in for 15 minutes."""

    def __init__(self, *, limit: int = 5, window_seconds: int = 900):
        self.limit = limit
        self.window = window_seconds
        self._failures: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def blocked(self, key: str, now: float | None = None) -> bool:
        current = now if now is not None else time.monotonic()
        with self._lock:
            recent = [t for t in self._failures.get(key, []) if current - t < self.window]
            self._failures[key] = recent
            return len(recent) >= self.limit

    def failed(self, key: str, now: float | None = None) -> None:
        current = now if now is not None else time.monotonic()
        with self._lock:
            self._failures.setdefault(key, []).append(current)

    def succeeded(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)
