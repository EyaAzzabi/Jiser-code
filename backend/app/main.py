"""JISER API — the bridge between taxpayers and the tax administration.

Run from the repo root:
    .venv/Scripts/python -m uvicorn app.main:app --reload --app-dir backend
Docs (Swagger): http://127.0.0.1:8000/docs
"""
from __future__ import annotations

import json
import logging

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .config import CORS_ORIGINS, LEGAL_DIR, SYNTHETIC_DIR
from .schemas import AnalyseNotification, Notification
from .services import administration, analysis, drafting, extraction, llm
from .services.legal_rag import get_index
from .services.store import TODAY, get_store

logging.basicConfig(level=logging.INFO)
app = FastAPI(title="JISER API", version="0.1.0",
              description="Plateforme IA pour le contentieux fiscal tunisien (prototype, données synthétiques).")
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
def warm_up() -> None:
    get_index()
    get_store()


@app.get("/api/status", tags=["système"])
def status() -> dict:
    store = get_store()
    return {"ok": True, "llm": llm.status(), "articles": len(get_index().articles),
            "dossiers": len(store.dossiers), "date_demo": TODAY.isoformat()}


# ---- Côté contribuable ----------------------------------------------------------------------

class AnalyseRequest(BaseModel):
    notification: Notification
    pieces_ratio: float = analysis.DEFAULT_PIECES_RATIO


@app.post("/api/contribuable/analyser", response_model=AnalyseNotification, tags=["contribuable"])
async def analyser_fichier(fichier: UploadFile = File(...), pieces_ratio: float = Form(analysis.DEFAULT_PIECES_RATIO)):
    """Upload a notification (PDF, image or text) and get the full analysis."""
    data = await fichier.read()
    try:
        notif, _mode = extraction.from_upload(data, fichier.filename or "", fichier.content_type)
    except extraction.ExtractionError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    result = analysis.analyse(notif, pieces_ratio, today=TODAY)
    get_store().log("analyse_notification", notif.reference,
                    f"{sum(c.contestabilite != 'solide' for c in result.chefs)} chef(s) contestable(s)", result.mode)
    return result


@app.post("/api/contribuable/analyser-json", response_model=AnalyseNotification, tags=["contribuable"])
def analyser_json(req: AnalyseRequest):
    return analysis.analyse(req.notification, req.pieces_ratio, today=TODAY)


class ReponseRequest(BaseModel):
    analyse: AnalyseNotification
    signataire: str = "Le Gérant"


@app.post("/api/contribuable/brouillon", tags=["contribuable"])
def brouillon(req: ReponseRequest) -> dict:
    text, mode = drafting.draft_reply(req.analyse, req.signataire)
    get_store().log("brouillon_reponse", req.analyse.notification.reference, "Brouillon de réponse généré", mode)
    return {"lettre": text, "mode": mode}


@app.get("/api/exemples", tags=["contribuable"])
def exemples() -> list[dict]:
    """Demo notifications available for download in the UI."""
    return [{"nom": p.stem, "fichier": p.name} for p in sorted((SYNTHETIC_DIR / "samples").glob("*.pdf"))]


@app.get("/api/exemples/{nom}", tags=["contribuable"])
def exemple(nom: str):
    from fastapi.responses import FileResponse
    path = (SYNTHETIC_DIR / "samples" / nom).resolve()
    if path.parent != (SYNTHETIC_DIR / "samples").resolve() or not path.exists():
        raise HTTPException(404, "Exemple introuvable")
    return FileResponse(path, media_type="application/pdf", filename=nom)


# ---- Côté administration --------------------------------------------------------------------

@app.get("/api/admin/dossiers", tags=["administration"])
def dossiers(limit: int = 100, gouvernorat: str | None = None, etape: str | None = None, groupe: str | None = None):
    return administration.triage(limit, gouvernorat, etape, groupe)


@app.get("/api/admin/dossiers/{dossier_id}", tags=["administration"])
def dossier(dossier_id: str):
    detail = administration.dossier_detail(dossier_id)
    if detail is None:
        raise HTTPException(404, "Dossier introuvable")
    return detail


@app.post("/api/admin/controle-qualite", response_model=AnalyseNotification, tags=["administration"])
async def controle_qualite(fichier: UploadFile = File(...)):
    """Auditor uploads a draft notification before sending it: same checks, to fix weaknesses first."""
    data = await fichier.read()
    try:
        notif, _ = extraction.from_upload(data, fichier.filename or "", fichier.content_type)
    except extraction.ExtractionError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    result = analysis.analyse(notif, pieces_ratio=0.3, today=notif.date_notification)
    get_store().log("controle_qualite", notif.reference,
                    f"{sum(p.statut == 'vice' for p in result.procedure)} point(s) de procédure à corriger", result.mode)
    return result


@app.get("/api/admin/tableau-de-bord", tags=["administration"])
def tableau_de_bord():
    return administration.dashboard()


# ---- Admin plateforme -----------------------------------------------------------------------

USERS = [
    {"nom": "Sami Ben Salah", "role": "entreprise", "structure": "Société Distribution El Amen SARL"},
    {"nom": "Leila Trabelsi", "role": "conseil", "structure": "Cabinet Trabelsi, conseil fiscal"},
    {"nom": "Karim Jaziri", "role": "verificateur", "structure": "CRCI Sfax"},
    {"nom": "Nadia Mansouri", "role": "cheffe_contentieux", "structure": "Unité du contentieux, DGI"},
    {"nom": "Admin DSI", "role": "admin", "structure": "Ministère des Finances"},
]


@app.get("/api/plateforme/utilisateurs", tags=["admin plateforme"])
def utilisateurs():
    return USERS


@app.get("/api/plateforme/journal", tags=["admin plateforme"])
def journal(limit: int = 100):
    return get_store().journal[:limit]


@app.get("/api/plateforme/base-juridique", tags=["admin plateforme"])
def base_juridique():
    out = []
    for path in sorted(LEGAL_DIR.glob("*.json")):
        arts = json.loads(path.read_text(encoding="utf-8"))
        if arts:
            out.append({"code": arts[0]["code"], "nom": arts[0]["code_name"], "articles": len(arts),
                        "source": "Jurisite Tunisie (jurisitetunisie.com)"})
    return out


@app.get("/api/plateforme/recherche-juridique", tags=["admin plateforme"])
def recherche(q: str, k: int = 5):
    return get_index().search(q, k=k)
