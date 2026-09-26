"""Real-time messaging company <-> administration (REST + WebSocket)."""
from __future__ import annotations

import asyncio
import base64

from fastapi import APIRouter, Depends, HTTPException, Response, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from ..deps import permission
from ..services import auth, messagerie
from ..services.db import repo
from ..services.permissions import a_permission, perimetre

router = APIRouter(prefix="/api/messagerie", tags=["messagerie"])
LECTEURS = ("messagerie:entreprise", "messagerie:administration")


@router.get("/conversations")
def conversations(session: dict = Depends(permission(*LECTEURS))):
    return messagerie.liste(session)


class OuvrirRequest(BaseModel):
    analyse_id: str


@router.post("/conversations")
def ouvrir(req: OuvrirRequest, session: dict = Depends(permission("messagerie:entreprise"))):
    try:
        return messagerie.ouvrir(session, req.analyse_id)
    except LookupError as e:
        raise HTTPException(404, str(e)) from e


@router.get("/conversations/{cid}")
def conversation(cid: str, session: dict = Depends(permission(*LECTEURS))):
    try:
        return messagerie.conversation(session, cid)
    except PermissionError as e:
        raise HTTPException(404, "Conversation introuvable") from e


@router.get("/dossier/{dossier_id}")
def conversation_du_dossier(dossier_id: str, session: dict = Depends(permission("messagerie:administration"))):
    conv = next((c for c in repo().conversations_all() if c.get("dossier_id") == dossier_id), None)
    if conv is None or not messagerie.peut_acceder(session, conv):
        return {"conversation": None}
    return {"conversation": {"id": conv["id"], "reference": conv["reference"]}}


class PieceJointe(BaseModel):
    nom: str
    mime: str
    contenu: str


class MessageRequest(BaseModel):
    contenu: str = ""
    piece: PieceJointe | None = None


@router.post("/conversations/{cid}/messages")
async def envoyer(cid: str, req: MessageRequest, session: dict = Depends(permission(*LECTEURS))):
    try:
        piece = messagerie.valider_piece(req.piece.nom, req.piece.mime, req.piece.contenu) if req.piece else None
        return await messagerie.envoyer(session, cid, req.contenu, piece)
    except PermissionError as e:
        raise HTTPException(404, "Conversation introuvable") from e
    except ValueError as e:
        raise HTTPException(422, str(e)) from e


@router.get("/messages/{mid}/piece")
def piece(mid: str, session: dict = Depends(permission(*LECTEURS))):
    m = repo().message_piece(mid)
    conv = repo().conversation_get(m["conversation_id"]) if m else None
    if not m or not m.get("piece_contenu") or not conv or not messagerie.peut_acceder(session, conv):
        raise HTTPException(404, "Pièce introuvable")
    return Response(base64.b64decode(m["piece_contenu"]), media_type=m["piece_mime"],
                    headers={"Content-Disposition": f'inline; filename="{m["piece_nom"]}"', "Cache-Control": "no-store"})


class AideRequest(BaseModel):
    action: str   # resume | suggestion | pieces


@router.post("/conversations/{cid}/ia", response_model=messagerie.AideIA)
def aide(cid: str, req: AideRequest, session: dict = Depends(permission(*LECTEURS))):
    try:
        return messagerie.aide_ia(session, cid, req.action)
    except PermissionError as e:
        raise HTTPException(404, "Conversation introuvable") from e
    except ValueError as e:
        raise HTTPException(422, str(e)) from e


@router.websocket("/ws")
async def temps_reel(ws: WebSocket):
    """Authenticate with the first message ({"type": "auth", "token"}), so the token never appears in a URL."""
    await ws.accept()
    messagerie._boucle = asyncio.get_running_loop()
    try:
        first = await asyncio.wait_for(ws.receive_json(), timeout=10)
        s = await run_in_threadpool(auth.get_session, str(first.get("token", "")))
        user = await run_in_threadpool(repo().get_user, s["email"]) if s.get("utilisateur_id") else None
        if not user or (user.get("statut") or "actif") != "actif" or not any(a_permission(user["role"], p) for p in LECTEURS):
            await ws.close(code=4403)
            return
    except Exception:
        await ws.close(code=4401)
        return
    session = {**s, "role": user["role"], "utilisateur_id": user["id"], "user": user}
    hub = messagerie.hub
    hub.rejoindre(f"user:{user['id']}", ws)
    if user["role"] != "entreprise":
        hub.rejoindre(f"zone:{perimetre(user) or '*'}", ws)
    await ws.send_json({"type": "pret"})
    try:
        while True:
            ev = await ws.receive_json()
            cid = str(ev.get("conversation_id", ""))
            if ev.get("type") in {"rejoindre", "ecrit"}:
                conv = await run_in_threadpool(repo().conversation_get, cid)
                if not conv or not messagerie.peut_acceder(session, conv):
                    continue
                if ev["type"] == "rejoindre":
                    hub.rejoindre(f"conv:{cid}", ws)
                else:
                    await hub.diffuser(f"conv:{cid}", {"type": "ecrit", "conversation_id": cid, "auteur_role": user["role"]}, sauf=ws)
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        hub.quitter(ws)
