"""E-mail OTP authentication, sessions and role-based access.

Security choices:
* 6-digit code from `secrets` (CSPRNG); only a salted SHA-256 hash is stored (database or memory).
* Code valid 5 minutes, 5 attempts max, single use, resend throttled to one per 30 seconds.
* Constant-time comparison (hmac.compare_digest).
* The code is delivered by e-mail through an n8n workflow and is NEVER returned by the API.
  If no n8n webhook is configured, it is written to the server log only (developer setup).
* Session token: 256-bit random; only its SHA-256 is stored; expires after 8 hours.
* The platform administration space only accepts e-mails listed in ADMIN_EMAILS.
* New accounts start "en_attente": nothing is accessible until a validator approves them (comptes.py).
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import re
import secrets
from datetime import datetime, timedelta, timezone

import requests

from ..config import ADMIN_EMAILS, APP_URL, N8N_OTP_WEBHOOK_URL, N8N_SHARED_SECRET, N8N_WELCOME_WEBHOOK_URL
from .db import repo
from .permissions import ROLE_LABELS, SELF_SERVICE_ROLES

log = logging.getLogger("jiser.auth")

OTP_TTL = timedelta(minutes=5)
OTP_MAX_ATTEMPTS = 5
OTP_RESEND = timedelta(seconds=30)
SESSION_TTL = timedelta(hours=8)
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$")


class AuthError(ValueError):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_ts(v) -> datetime:
    if isinstance(v, datetime):
        return v
    return datetime.fromisoformat(str(v).replace("Z", "+00:00"))


def normalize_email(email: str) -> str:
    email = email.strip().lower()
    if not EMAIL_RE.match(email):
        raise AuthError("Adresse e-mail invalide.")
    return email


def mask(email: str) -> str:
    name, _, domain = email.partition("@")
    return f"{name[:2]}***@{domain}"


def _hash(salt: str, code: str) -> str:
    return hashlib.sha256((salt + code).encode()).hexdigest()


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _post_n8n(url: str, payload: dict) -> bool:
    headers = {"X-Jiser-Secret": N8N_SHARED_SECRET} if N8N_SHARED_SECRET else {}
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=15)
        r.raise_for_status()
        return True
    except requests.RequestException as e:
        log.error("n8n webhook failed: %s", e)
        return False


def _deliver_otp(email: str, code: str, intention: str) -> str:
    if N8N_OTP_WEBHOOK_URL:
        ok = _post_n8n(N8N_OTP_WEBHOOK_URL, {"email": email, "code": code, "intention": intention,
                                             "expire_minutes": int(OTP_TTL.total_seconds() // 60)})
        if not ok:
            raise AuthError("L'e-mail n'a pas pu être envoyé. Réessayez dans un instant.", 503)
        return "email"
    log.warning("N8N_OTP_WEBHOOK_URL not set: OTP for %s written to server log only: %s", mask(email), code)
    return "journal_serveur"


def send_welcome(user: dict) -> None:
    if N8N_WELCOME_WEBHOOK_URL:
        _post_n8n(N8N_WELCOME_WEBHOOK_URL, {"email": user["email"], "prenom": user["prenom"], "nom": user["nom"],
                                            "role": user["role"], "role_label": ROLE_LABELS.get(user["role"], user["role"]),
                                            "lien": APP_URL})


def request_otp(email: str, intention: str) -> dict:
    email = normalize_email(email)
    db = repo()
    user = db.get_user(email)
    if intention == "connexion" and not user:
        raise AuthError("Aucun compte pour cette adresse : créez votre espace.", 404)
    if intention == "inscription" and user:
        raise AuthError("Un compte existe déjà pour cette adresse : connectez-vous.", 409)
    if intention == "admin" and email not in ADMIN_EMAILS:
        # same message whether or not the address exists, to avoid revealing the admin list
        raise AuthError("Accès réservé.", 403)
    if intention not in {"inscription", "connexion", "admin"}:
        raise AuthError("Intention inconnue.")

    previous = db.otp_get(email)
    if previous and _now() - _parse_ts(previous["sent_at"]) < OTP_RESEND:
        wait = int((OTP_RESEND - (_now() - _parse_ts(previous["sent_at"]))).total_seconds()) + 1
        raise AuthError(f"Veuillez patienter {wait} secondes avant de demander un nouveau code.", 429)

    code = f"{secrets.randbelow(10**6):06d}"
    salt = secrets.token_hex(16)
    db.otp_set(email, {"salt": salt, "digest": _hash(salt, code), "expires_at": (_now() + OTP_TTL).isoformat(),
                       "sent_at": _now().isoformat(), "attempts": 0, "intention": intention})
    livraison = _deliver_otp(email, code, intention)
    return {"destination_masquee": mask(email), "expire_dans_s": int(OTP_TTL.total_seconds()),
            "renvoi_dans_s": int(OTP_RESEND.total_seconds()), "tentatives_max": OTP_MAX_ATTEMPTS, "livraison": livraison}


def verify_otp(email: str, code: str) -> dict:
    email = normalize_email(email)
    db = repo()
    entry = db.otp_get(email)
    if entry is None:
        raise AuthError("Aucun code en cours : demandez un nouveau code.")
    if _now() > _parse_ts(entry["expires_at"]):
        db.otp_delete(email)
        raise AuthError("Code expiré : demandez un nouveau code.")
    attempts = int(entry["attempts"]) + 1
    if not hmac.compare_digest(entry["digest"], _hash(entry["salt"], code.strip())):
        if attempts >= OTP_MAX_ATTEMPTS:
            db.otp_delete(email)
            raise AuthError("Trop de tentatives : le code est annulé, demandez-en un nouveau.")
        db.otp_update(email, attempts=attempts)
        raise AuthError(f"Code incorrect. Il vous reste {OTP_MAX_ATTEMPTS - attempts} tentative(s).")
    db.otp_delete(email)   # single use

    intention = entry.get("intention", "inscription")
    user = db.get_user(email)
    role = "admin" if intention == "admin" else (user["role"] if user else None)
    token = secrets.token_urlsafe(32)
    db.session_create({"token_hash": _token_hash(token), "email": email, "role": role,
                       "utilisateur_id": user["id"] if user else None,
                       "expires_at": (_now() + SESSION_TTL).isoformat()})
    if user:
        db.touch_login(email)
    return {"token": token, "role": role, "utilisateur": public_user(user) if user else None,
            "expire_dans_s": int(SESSION_TTL.total_seconds())}


def get_session(token: str | None) -> dict:
    if not token:
        raise AuthError("Connexion requise.", 401)
    db = repo()
    th = _token_hash(token)
    s = db.session_get(th)
    if s is None or _now() > _parse_ts(s["expires_at"]):
        if s:
            db.session_delete(th)
        raise AuthError("Session expirée : reconnectez-vous.", 401)
    return {**s, "token_hash": th}


def complete_signup(session: dict, profile: dict) -> dict:
    """Create the user after a verified 'inscription' OTP."""
    db = repo()
    if session.get("utilisateur_id") or db.get_user(session["email"]):
        raise AuthError("Ce compte existe déjà.", 409)
    if profile["role"] not in SELF_SERVICE_ROLES:
        raise AuthError("Rôle non autorisé.", 403)
    # nothing is accessible before a validator approves the account (see comptes.py)
    user = db.create_user({"email": session["email"], **profile, "statut": "en_attente", "verification": {}})
    db.session_update(session["token_hash"], role=user["role"], utilisateur_id=user["id"])
    return public_user(user)


def public_user(user: dict) -> dict:
    v = user.get("verification") or {}
    return {**{k: user.get(k) for k in ("id", "email", "role", "nom", "prenom", "fonction", "langue", "details")},
            "statut": user.get("statut") or "actif", "consentements": user.get("consentements") or {},
            "verification": {"soumis_le": v.get("soumis_le"), "decision": v.get("decision"), "motif": v.get("motif"),
                             "score": (v.get("pre_verification") or {}).get("score"), "validateur": v.get("validateur")}}


def logout(token: str) -> None:
    repo().session_delete(_token_hash(token))
