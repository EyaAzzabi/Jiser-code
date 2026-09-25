"""One-time password (OTP) verification and sessions for onboarding.

Security choices:
* 6-digit code from `secrets` (CSPRNG), stored only as a salted SHA-256 hash.
* Code valid 5 minutes, at most 5 attempts, then it is burnt.
* Resend throttled to one code per 30 seconds per destination.
* Constant-time comparison (hmac.compare_digest).
* Session token: 256-bit random, server-side, expires after 8 hours.

Prototype limitation: no SMS/e-mail gateway is wired. With JISER_DEMO_OTP=1 (default) the
code is returned in the API response and shown on screen, clearly labelled as demo mode.
In production, `_deliver` would call an SMS gateway or an SMTP server and never return the code.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
import re
import secrets
import time
from dataclasses import dataclass, field

log = logging.getLogger("jiser.auth")

OTP_TTL_S = 5 * 60
OTP_MAX_ATTEMPTS = 5
OTP_RESEND_S = 30
SESSION_TTL_S = 8 * 3600
DEMO_OTP = os.getenv("JISER_DEMO_OTP", "1") == "1"

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$")
PHONE_RE = re.compile(r"^\+216[2-9]\d{7}$")   # Tunisian mobile/landline: +216 followed by 8 digits


class AuthError(ValueError):
    pass


@dataclass
class _Otp:
    salt: bytes
    digest: bytes
    expires: float
    sent_at: float
    attempts: int = 0


@dataclass
class Session:
    token: str
    destination: str
    canal: str
    expires: float
    profil: dict = field(default_factory=dict)


_otps: dict[str, _Otp] = {}
_sessions: dict[str, Session] = {}


def normalize(canal: str, destination: str) -> str:
    destination = destination.strip()
    if canal == "email":
        destination = destination.lower()
        if not EMAIL_RE.match(destination):
            raise AuthError("Adresse e-mail invalide.")
    elif canal == "sms":
        digits = re.sub(r"[\s.-]", "", destination)
        if not digits.startswith("+216"):
            digits = "+216" + digits.lstrip("0")
        if not PHONE_RE.match(digits):
            raise AuthError("Numéro tunisien invalide : 8 chiffres attendus (ex. 22 123 456).")
        destination = digits
    else:
        raise AuthError("Canal inconnu : choisissez SMS ou e-mail.")
    return destination


def _hash(salt: bytes, code: str) -> bytes:
    return hashlib.sha256(salt + code.encode()).digest()


def _mask(destination: str) -> str:
    if "@" in destination:
        name, domain = destination.split("@", 1)
        return f"{name[:2]}***@{domain}"
    return f"{destination[:4]} ** *** {destination[-3:]}"


def _deliver(canal: str, destination: str, code: str) -> None:
    # Production: SMS gateway / SMTP. Never log the code outside demo mode.
    log.info("OTP sent via %s to %s%s", canal, _mask(destination), f" (demo code {code})" if DEMO_OTP else "")


def request_otp(canal: str, destination: str) -> dict:
    dest = normalize(canal, destination)
    now = time.time()
    previous = _otps.get(dest)
    if previous and now - previous.sent_at < OTP_RESEND_S:
        wait = int(OTP_RESEND_S - (now - previous.sent_at)) + 1
        raise AuthError(f"Veuillez patienter {wait} secondes avant de demander un nouveau code.")
    code = f"{secrets.randbelow(10**6):06d}"
    salt = secrets.token_bytes(16)
    _otps[dest] = _Otp(salt=salt, digest=_hash(salt, code), expires=now + OTP_TTL_S, sent_at=now)
    _deliver(canal, dest, code)
    out = {"destination_masquee": _mask(dest), "expire_dans_s": OTP_TTL_S, "renvoi_dans_s": OTP_RESEND_S,
           "tentatives_max": OTP_MAX_ATTEMPTS}
    if DEMO_OTP:
        out["code_demo"] = code
    return out


def verify_otp(canal: str, destination: str, code: str) -> Session:
    dest = normalize(canal, destination)
    entry = _otps.get(dest)
    if entry is None:
        raise AuthError("Aucun code en cours : demandez un nouveau code.")
    if time.time() > entry.expires:
        _otps.pop(dest, None)
        raise AuthError("Code expiré : demandez un nouveau code.")
    entry.attempts += 1
    if not hmac.compare_digest(entry.digest, _hash(entry.salt, code.strip())):
        left = OTP_MAX_ATTEMPTS - entry.attempts
        if left <= 0:
            _otps.pop(dest, None)
            raise AuthError("Trop de tentatives : le code est annulé, demandez-en un nouveau.")
        raise AuthError(f"Code incorrect. Il vous reste {left} tentative(s).")
    _otps.pop(dest, None)   # single use
    token = secrets.token_urlsafe(32)
    session = Session(token=token, destination=dest, canal=canal, expires=time.time() + SESSION_TTL_S)
    _sessions[token] = session
    return session


def get_session(token: str | None) -> Session:
    if not token:
        raise AuthError("Session absente.")
    session = _sessions.get(token)
    if session is None or time.time() > session.expires:
        _sessions.pop(token or "", None)
        raise AuthError("Session expirée : reconnectez-vous.")
    return session


def logout(token: str) -> None:
    _sessions.pop(token, None)
