"""Real-time messaging between a company and the tax administration, one conversation per notification.

* A conversation is opened by the company from one of its analysed notifications; it is linked to the
  administration's file with the same reference, so it lands in the inbox of the right centre.
* Who can read it: the company itself; in the administration, the case officer the file is assigned
  to (or any officer of the centre while it is unassigned) and the head of centre. Nobody else,
  not even the minister or the platform administrator.
* Message texts and attachments are encrypted at rest (db.py). E-mail alerts never contain the text.
* Delivery is instant over WebSocket (`Hub`), with typing indicators and read receipts.
"""
from __future__ import annotations

import asyncio
import base64
import logging
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import WebSocket
from pydantic import BaseModel

from ..domain import CHEF_TYPES
from . import llm, securite
from .comptes import notifier
from .db import repo
from .permissions import perimetre
from .store import get_store

log = logging.getLogger("jiser.messagerie")

TAILLE_MAX_PIECE = 5 * 1024 * 1024
TYPES_PIECES = {"application/pdf", "image/jpeg", "image/png", "image/webp"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---- access rules --------------------------------------------------------------------------------

def peut_acceder(session: dict, conv: dict) -> bool:
    role, user = session.get("role"), session.get("user") or {}
    if role == "entreprise":
        return conv["entreprise_id"] == session.get("utilisateur_id")
    if role not in {"contentieux", "chef_centre"}:
        return False
    zone = perimetre(user)
    if zone and conv["gouvernorat"] != zone:
        return False
    if role == "contentieux" and conv.get("dossier_id"):
        a = repo().affectations_all().get(conv["dossier_id"])
        if a and a.get("agent_id") != session.get("utilisateur_id"):
            return False   # assigned to a colleague
    return True


def _dossier_par_reference(reference: str):
    return next((d for d in get_store().dossiers.values() if d.notification.reference == reference), None)


# ---- conversations --------------------------------------------------------------------------------

def ouvrir(session: dict, analyse_id: str) -> dict:
    row = repo().analysis_get(analyse_id, session["utilisateur_id"])
    if row is None:
        raise LookupError("Analyse introuvable")
    ref = row["reference"]
    conv = repo().conversation_par_reference(ref, session["utilisateur_id"])
    if conv:
        return conv
    dossier = _dossier_par_reference(ref)
    gouv = dossier.notification.entreprise.gouvernorat if dossier else row["resultat"]["notification"]["entreprise"]["gouvernorat"]
    conv = repo().conversation_add({"reference": ref, "dossier_id": dossier.id if dossier else None, "analyse_id": analyse_id,
                                    "entreprise_id": session["utilisateur_id"], "entreprise_nom": row["entreprise"], "gouvernorat": gouv})
    return conv


def liste(session: dict) -> list[dict]:
    uid = session.get("utilisateur_id") or session["email"]
    affect = repo().affectations_all()
    out = []
    for c in repo().conversations_all():
        if not peut_acceder(session, c):
            continue
        msgs = repo().messages_for(c["id"])
        dernier = msgs[-1] if msgs else None
        a = affect.get(c.get("dossier_id") or "")
        out.append({**c, "non_lus": sum(uid not in (m.get("lu_par") or []) for m in msgs),
                    "dernier": {"auteur_nom": dernier["auteur_nom"], "auteur_role": dernier["auteur_role"],
                                "extrait": (dernier["contenu"] or "")[:120], "cree_le": dernier["cree_le"]} if dernier else None,
                    "agent": a["agent_nom"] if a else None})
    return out


def conversation(session: dict, cid: str) -> dict:
    conv = repo().conversation_get(cid)
    if conv is None or not peut_acceder(session, conv):
        raise PermissionError("Conversation inaccessible.")
    uid = session.get("utilisateur_id") or session["email"]
    avant = repo().messages_for(cid)
    if any(uid not in (m.get("lu_par") or []) for m in avant):   # signal only real changes (no ping-pong)
        repo().messages_marquer_lus(cid, uid)
        signaler_lecture(cid)
    a = repo().affectations_all().get(conv.get("dossier_id") or "")
    return {**conv, "messages": repo().messages_for(cid), "agent": a["agent_nom"] if a else None}


def auteur(session: dict) -> tuple[str, str]:
    u = session.get("user") or {}
    nom = f"{u.get('prenom', '')} {u.get('nom', '')}".strip() or session["email"]
    if session["role"] != "entreprise":
        centre = (u.get("details") or {}).get("centre")
        nom = f"{nom} · {'Chef de centre' if session['role'] == 'chef_centre' else 'Chargé(e) du contentieux'}" + (f" · CRCI {centre}" if centre else "")
    return session.get("utilisateur_id") or session["email"], nom


async def envoyer(session: dict, cid: str, contenu: str, piece: dict | None = None) -> dict:
    from starlette.concurrency import run_in_threadpool
    conv = await run_in_threadpool(repo().conversation_get, cid)
    if conv is None or not peut_acceder(session, conv):
        raise PermissionError("Conversation inaccessible.")
    contenu = contenu.strip()[:4000]
    if not contenu and not piece:
        raise ValueError("Message vide.")
    aid, nom = auteur(session)
    row = {"conversation_id": cid, "auteur_id": aid, "auteur_role": session["role"], "auteur_nom": nom, "contenu": contenu}
    if piece:
        row |= {"piece_nom": piece["nom"][:120], "piece_mime": piece["mime"], "piece_contenu": piece["contenu"]}
    msg = await run_in_threadpool(repo().message_add, row)
    await run_in_threadpool(repo().conversation_update, cid, dernier_message_le=_now())
    await run_in_threadpool(repo().journal_add, {"action": "message", "cible": conv["reference"], "recommandation": "Message échangé",
                                                 "mode": "humain", "decision_humaine": "—", "utilisateur": session["email"]})
    await hub.diffuser(f"conv:{cid}", {"type": "message", "conversation_id": cid, "message": msg})
    for zone in (conv["gouvernorat"], "*"):   # the centre's inbox, and national (legacy) officers
        await hub.diffuser(f"zone:{zone}", {"type": "activite", "conversation_id": cid})
    await hub.diffuser(f"user:{conv['entreprise_id']}", {"type": "activite", "conversation_id": cid})
    # e-mail the company when the administration writes and the company is not connected (never the text)
    if session["role"] != "entreprise" and not hub.en_ligne(f"user:{conv['entreprise_id']}"):
        ent = await run_in_threadpool(repo().get_user_by_id, conv["entreprise_id"])
        if ent:
            await run_in_threadpool(notifier, ent["email"], "Nouveau message de l'administration fiscale", f"Bonjour {ent['prenom']},",
                                    f"Vous avez reçu un nouveau message au sujet de la notification {conv['reference']}. "
                                    "Pour des raisons de confidentialité, son contenu n'est visible que dans votre espace JISER.")
    return msg


def valider_piece(nom: str, mime: str, data_b64: str) -> dict:
    if mime not in TYPES_PIECES:
        raise ValueError("Format non accepté (PDF, JPG, PNG ou WEBP).")
    taille = len(base64.b64decode(data_b64, validate=True))
    if taille > TAILLE_MAX_PIECE:
        raise ValueError("Fichier trop volumineux (5 Mo maximum).")
    return {"nom": nom, "mime": mime, "contenu": data_b64, "taille": taille}


# ---- AI assistance inside a conversation ----------------------------------------------------------

class AideIA(BaseModel):
    texte: str
    points: list[str]
    mode: str = "ia"


def aide_ia(session: dict, cid: str, action: str) -> AideIA:
    conv = repo().conversation_get(cid)
    if conv is None or not peut_acceder(session, conv):
        raise PermissionError("Conversation inaccessible.")
    msgs = repo().messages_for(cid)[-30:]
    fil = "\n".join(f"- {m['auteur_role']} ({m['cree_le'][:10]}) : {m['contenu']}" + (f" [pièce jointe : {m['piece_nom']}]" if m.get("piece_nom") else "")
                    for m in msgs) or "(aucun message)"
    dossier = _dossier_par_reference(conv["reference"])
    securite.ajouter_identifiants({conv["entreprise_nom"]: "ENTREPRISE", **({dossier.notification.entreprise.nom: "ENTREPRISE",
                                   dossier.notification.entreprise.matricule_fiscal: "MATRICULE"} if dossier else {})})
    chefs = [{"libelle": c.libelle, "type": c.type, "montant": c.montant_principal + c.penalites} for c in dossier.notification.chefs] if dossier else []
    pieces_attendues = sorted({p for c in (dossier.notification.chefs if dossier else []) for p in CHEF_TYPES.get(c.type, {}).get("pieces", [])})
    cote = "l'administration fiscale (agent du contentieux)" if session["role"] != "entreprise" else "l'entreprise (contribuable)"
    consignes = {
        "resume": "Résume cet échange en 3 phrases, puis liste les points en suspens et la prochaine action à mener.",
        "suggestion": f"Propose une réponse courtoise et précise à envoyer par {cote}, fondée uniquement sur les faits de l'échange. "
                      "Mets le texte de la réponse dans « texte » et les points clés dans « points ».",
        "pieces": "Compare les pièces attendues pour ces chefs de redressement avec les pièces déjà échangées, et liste celles "
                  "qui manquent encore (une par point). « texte » : une phrase de synthèse.",
    }
    if action not in consignes:
        raise ValueError("Action inconnue.")
    prompt = (f"{consignes[action]}\n\nRéférence : {conv['reference']}\nChefs de redressement : {chefs}\n"
              f"Pièces attendues pour ces chefs : {pieces_attendues}\n\nÉchange :\n{fil}")
    try:
        return llm.parse(f"msg-{action}", prompt, AideIA, max_tokens=1500, cache=False)
    except llm.LLMUnavailable:
        if action == "pieces":
            deja = " ".join((m.get("piece_nom") or "") + " " + (m.get("contenu") or "") for m in msgs).lower()
            manquantes = [p for p in pieces_attendues if p.split()[0].lower() not in deja]
            return AideIA(texte=f"{len(manquantes)} pièce(s) attendue(s) non encore mentionnée(s).", points=manquantes, mode="hors_ligne")
        return AideIA(texte="Assistance IA indisponible pour le moment.", points=[], mode="hors_ligne")


def signaler_lecture(cid: str) -> None:
    """Read receipt: tell the other side (called from a worker thread)."""
    if _boucle is not None and hub.en_ligne(f"conv:{cid}"):
        asyncio.run_coroutine_threadsafe(hub.diffuser(f"conv:{cid}", {"type": "lu", "conversation_id": cid}), _boucle)


_boucle: asyncio.AbstractEventLoop | None = None


# ---- WebSocket hub ------------------------------------------------------------------------------

class Hub:
    """Channels: conv:<id> (a conversation), zone:<governorate> (an administration inbox), user:<id>."""

    def __init__(self) -> None:
        self.canaux: dict[str, set[WebSocket]] = defaultdict(set)

    def rejoindre(self, canal: str, ws: WebSocket) -> None:
        self.canaux[canal].add(ws)

    def quitter(self, ws: WebSocket) -> None:
        for sockets in self.canaux.values():
            sockets.discard(ws)

    def en_ligne(self, canal: str) -> bool:
        return bool(self.canaux.get(canal))

    async def diffuser(self, canal: str, event: dict, sauf: WebSocket | None = None) -> None:
        for ws in list(self.canaux.get(canal, ())):
            if ws is sauf:
                continue
            try:
                await asyncio.wait_for(ws.send_json(event), timeout=5)
            except Exception:
                self.quitter(ws)


hub = Hub()
