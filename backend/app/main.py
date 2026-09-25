"""JISER API — the bridge between taxpayers and the tax administration.

Run from the repo root:
    .venv/Scripts/python -m uvicorn app.main:app --reload --app-dir backend
Docs (Swagger): http://127.0.0.1:8000/docs
"""
from __future__ import annotations

import json
import logging
import re
import threading

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .config import CORS_ORIGINS, LEGAL_DIR, SYNTHETIC_DIR
from .schemas import AnalyseNotification, Notification
from .services import administration, analysis, auth, drafting, extraction, llm
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
    threading.Thread(target=llm.probe, daemon=True).start()


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


# ---- Onboarding sécurisé (OTP) --------------------------------------------------------------

class OtpRequest(BaseModel):
    canal: str
    destination: str


class OtpVerify(OtpRequest):
    code: str


ROLES = {"entreprise", "conseil", "verificateur", "contentieux", "admin"}
# Fields each role must provide during onboarding (validated server-side, not only in the UI)
REQUIRED_FIELDS = {
    "entreprise": ["raison_sociale", "matricule_fiscal", "forme_juridique", "secteur", "gouvernorat", "effectif", "regime"],
    "conseil": ["cabinet", "profession", "numero_inscription", "gouvernorat"],
    "verificateur": ["matricule_agent", "grade", "structure", "gouvernorat"],
    "contentieux": ["structure", "perimetre", "objectifs"],
    "admin": ["structure", "perimetre"],
}
MATRICULE_RE = re.compile(r"^\d{7}[A-Z]/[A-Z]/[A-Z]/\d{3}$")


class ProfilRequest(BaseModel):
    role: str
    nom: str
    prenom: str
    fonction: str = ""
    langue: str = "fr"
    details: dict
    consentements: dict[str, bool]


def _session(authorization: str | None):
    token = (authorization or "").removeprefix("Bearer ").strip()
    try:
        return auth.get_session(token)
    except auth.AuthError as e:
        raise HTTPException(401, str(e)) from e


@app.post("/api/auth/otp/demander", tags=["authentification"])
def otp_demander(req: OtpRequest):
    try:
        return auth.request_otp(req.canal, req.destination)
    except auth.AuthError as e:
        raise HTTPException(400, str(e)) from e


@app.post("/api/auth/otp/verifier", tags=["authentification"])
def otp_verifier(req: OtpVerify):
    try:
        s = auth.verify_otp(req.canal, req.destination, req.code)
    except auth.AuthError as e:
        raise HTTPException(400, str(e)) from e
    get_store().log("otp_verifie", auth._mask(s.destination), "Identité vérifiée par code à usage unique", "securite")
    return {"token": s.token, "expire_dans_s": auth.SESSION_TTL_S}


@app.post("/api/auth/profil", tags=["authentification"])
def enregistrer_profil(req: ProfilRequest, authorization: str | None = Header(default=None)):
    session = _session(authorization)
    if req.role not in ROLES:
        raise HTTPException(422, "Rôle inconnu.")
    missing = [f for f in REQUIRED_FIELDS[req.role] if not str(req.details.get(f, "")).strip()]
    if not req.nom.strip() or not req.prenom.strip():
        missing.insert(0, "nom / prénom")
    if missing:
        raise HTTPException(422, "Champs obligatoires manquants : " + ", ".join(missing))
    if req.role == "entreprise" and not MATRICULE_RE.match(str(req.details["matricule_fiscal"]).upper().replace(" ", "")):
        raise HTTPException(422, "Matricule fiscal invalide (format : 1234567A/A/M/000).")
    if not (req.consentements.get("cgu") and req.consentements.get("donnees_personnelles")):
        raise HTTPException(422, "Les conditions d'utilisation et le traitement des données (loi 2004-63) doivent être acceptés.")
    session.profil = req.model_dump() | {"contact": session.destination, "canal": session.canal}
    get_store().log("onboarding", f"{req.prenom} {req.nom} ({req.role})", "Profil créé après vérification OTP", "securite")
    return {"ok": True, "profil": session.profil}


@app.get("/api/auth/moi", tags=["authentification"])
def moi(authorization: str | None = Header(default=None)):
    s = _session(authorization)
    return {"contact": auth._mask(s.destination), "profil": s.profil}


@app.post("/api/auth/deconnexion", tags=["authentification"])
def deconnexion(authorization: str | None = Header(default=None)):
    auth.logout((authorization or "").removeprefix("Bearer ").strip())
    return {"ok": True}


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
