"""Account verification: identity documents, submission, validation queue, decision."""
from __future__ import annotations

import base64

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from ..deps import compte, current_session
from ..services import auth, comptes
from ..services.db import repo
from ..services.permissions import a_permission

router = APIRouter(prefix="/api/comptes", tags=["comptes"])


def _demandeur(session: dict) -> dict:
    user = repo().get_user(session["email"]) if session.get("utilisateur_id") else None
    if user is None:
        raise HTTPException(403, "Profil incomplet : terminez votre inscription.")
    return user


class PieceRequest(BaseModel):
    type: str
    nom: str
    mime: str
    contenu: str   # base64


@router.post("/pieces")
def deposer_piece(req: PieceRequest, session: dict = Depends(current_session)):
    """Identity documents sent during sign-up (encrypted before storage)."""
    user = _demandeur(session)
    if user.get("statut") not in {"en_attente", None}:
        raise HTTPException(409, "Compte déjà vérifié.")
    if req.type not in comptes.PIECES_REQUISES.get(user["role"], {}):
        raise HTTPException(422, "Type de pièce inattendu pour ce profil.")
    if req.mime not in comptes.TYPES_ACCEPTES:
        raise HTTPException(422, "Format non accepté (PDF, JPG, PNG ou WEBP).")
    try:
        taille = len(base64.b64decode(req.contenu, validate=True))
    except ValueError as e:
        raise HTTPException(422, "Fichier illisible.") from e
    if taille > comptes.TAILLE_MAX:
        raise HTTPException(413, "Fichier trop volumineux (5 Mo maximum).")
    return repo().piece_add({"utilisateur_id": user["id"], "type": req.type, "nom": req.nom[:150], "mime": req.mime,
                             "taille": taille, "contenu": req.contenu})


@router.post("/soumettre")
def soumettre(session: dict = Depends(current_session)):
    """End of sign-up: automatic checks, then the request waits for a validator (24 h)."""
    user = _demandeur(session)
    if user.get("statut") != "en_attente":
        raise HTTPException(409, "Compte déjà traité.")
    return auth.public_user(comptes.soumettre(user))


@router.get("/statut")
def statut(session: dict = Depends(current_session)):
    user = _demandeur(session)
    v = user.get("verification") or {}
    return {**auth.public_user(user), "pieces": repo().pieces_for(user["id"]),
            "controles": (v.get("pre_verification") or {}).get("controles", []), "delai_heures": comptes.DELAI_VERIFICATION_H}


def _validateur(session: dict) -> dict:
    if not (a_permission(session["role"], "comptes:valider") or a_permission(session["role"], "comptes:valider_agents")):
        raise HTTPException(403, "Accès non autorisé pour votre profil.")
    return session


@router.get("/demandes")
def demandes(session: dict = Depends(compte)):
    _validateur(session)
    return comptes.demandes(session.get("user"), session["role"])


@router.get("/pieces/{piece_id}")
def voir_piece(piece_id: str, session: dict = Depends(compte)):
    _validateur(session)
    piece = repo().piece_get(piece_id)
    owner = repo().get_user_by_id(piece["utilisateur_id"]) if piece else None
    if not piece or not owner or not comptes.peut_decider(session.get("user") or {}, session["role"], owner):
        raise HTTPException(404, "Pièce introuvable")
    return Response(base64.b64decode(piece["contenu"]), media_type=piece["mime"],
                    headers={"Content-Disposition": f'inline; filename="{piece["nom"]}"', "Cache-Control": "no-store"})


class DecisionCompte(BaseModel):
    decision: str   # valide | refuse
    motif: str = ""


@router.post("/demandes/{user_id}/decision")
def decider(user_id: str, req: DecisionCompte, session: dict = Depends(compte)):
    _validateur(session)
    if req.decision not in {"valide", "refuse"}:
        raise HTTPException(422, "Décision invalide.")
    try:
        return comptes.decider(session["email"], session.get("user"), session["role"], user_id, req.decision, req.motif)
    except PermissionError as e:
        raise HTTPException(403, str(e)) from e
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
