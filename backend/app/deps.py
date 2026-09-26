"""Access control shared by every route.

* `current_session`   a valid session token (any account state), used by sign-up and status routes
* `compte`            an active account: the role is re-read from the database on every request (never
                      trusted from the browser), pending or refused accounts are stopped, and the
                      confidentiality context (identifiers to mask, AI consent) is set for the request
* `permission(p)`     `compte` + the role must hold permission `p` (see services/permissions.py)
"""
from __future__ import annotations

from fastapi import Depends, Header, HTTPException
from starlette.concurrency import run_in_threadpool

from .config import ADMIN_EMAILS
from .services import auth, securite
from .services.db import repo
from .services.permissions import a_permission


def current_session(authorization: str | None = Header(default=None)) -> dict:
    try:
        return auth.get_session((authorization or "").removeprefix("Bearer ").strip())
    except auth.AuthError as e:
        raise HTTPException(e.status, str(e)) from e


async def compte(session: dict = Depends(current_session)) -> dict:
    # async on purpose: context variables set here reach the (threaded) endpoint of this request
    if session.get("role") == "admin":
        # platform admin: identity proven by OTP on an allow-listed address, re-checked on every request
        if session["email"] not in ADMIN_EMAILS:
            raise HTTPException(403, "Accès administrateur révoqué.")
        securite.definir({}, True)
        return {**session, "user": None}
    user = await run_in_threadpool(repo().get_user, session["email"]) if session.get("utilisateur_id") else None
    if user is None:
        raise HTTPException(403, "Profil incomplet : terminez votre inscription.")
    statut = user.get("statut") or "actif"
    if statut == "en_attente":
        raise HTTPException(403, "Compte en cours de vérification : vous recevrez un e-mail dès son activation (sous 24 h).")
    if statut in {"refuse", "suspendu"}:
        raise HTTPException(403, "Accès refusé pour ce compte.")
    consent = (user.get("consentements") or {}).get("analyse_ia", True)
    securite.definir(securite.identifiants_de(user), bool(consent))
    return {**session, "role": user["role"], "utilisateur_id": user["id"], "user": user}


def permission(*perms: str):
    async def dep(session: dict = Depends(compte)) -> dict:
        if not any(a_permission(session.get("role"), p) for p in perms):
            raise HTTPException(403, "Accès non autorisé pour votre profil.")
        return session
    return dep


def n8n_auth(x_jiser_secret: str | None = Header(default=None)) -> None:
    import hmac

    from .config import N8N_SHARED_SECRET
    if not N8N_SHARED_SECRET or not hmac.compare_digest(x_jiser_secret or "", N8N_SHARED_SECRET):
        raise HTTPException(401, "Secret n8n invalide.")


def journaliser_acces(reference: str, session: dict, action: str) -> None:
    """Access log shown to the taxpayer: role and centre of the reader, never their personal identity."""
    centre = ((session.get("user") or {}).get("details") or {}).get("centre")
    repo().acces_add({"reference": reference, "role": session.get("role") or "", "centre": centre, "action": action})
