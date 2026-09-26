"""JISER API — the bridge between taxpayers and the tax administration.

Run from the repo root:
    .venv/Scripts/python -m uvicorn app.main:app --reload --app-dir backend
Docs (Swagger): http://127.0.0.1:8000/docs
"""
from __future__ import annotations

import hmac
import json
import logging
import re
import threading
from datetime import date

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, StreamingResponse
from pydantic import BaseModel

from .config import CORS_ORIGINS, LEGAL_DIR, N8N_SHARED_SECRET, SYNTHETIC_DIR
from .domain import DELAI_REPONSE_JOURS
from .schemas import AnalyseNotification
from .services import (administration, ai_admin, analysis, assistant, auth, drafting, export_pdf, extraction, llm, rappels,
                       voix)
from .services.db import repo
from .services.legal_rag import get_index
from .services.store import TODAY, get_store

logging.basicConfig(level=logging.INFO)
app = FastAPI(title="JISER API", version="0.2.0",
              description="Plateforme IA pour le contentieux fiscal tunisien.")
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])

CONTRIBUABLE = {"entreprise", "conseil"}
ADMINISTRATION = {"verificateur", "contentieux", "admin"}


@app.on_event("startup")
def warm_up() -> None:
    get_index()
    get_store()
    repo()
    threading.Thread(target=llm.probe, daemon=True).start()
    rappels.demarrer_planificateur()


# ---- Access control -------------------------------------------------------------------------

def current_session(authorization: str | None = Header(default=None)) -> dict:
    try:
        return auth.get_session((authorization or "").removeprefix("Bearer ").strip())
    except auth.AuthError as e:
        raise HTTPException(e.status, str(e)) from e


def require(*roles: str):
    def dep(session: dict = Depends(current_session)) -> dict:
        if session.get("role") not in roles:
            raise HTTPException(403, "Accès non autorisé pour votre profil.")
        return session
    return dep


def _raise(e: auth.AuthError):
    raise HTTPException(e.status, str(e)) from e


# ---- Public ---------------------------------------------------------------------------------

@app.get("/api/status", tags=["public"])
def status() -> dict:
    return {"ok": True, "llm": llm.status(), "articles": len(get_index().articles), "base": repo().kind,
            "date": TODAY.isoformat()}


@app.get("/api/public/chiffres", tags=["public"])
def chiffres() -> dict:
    metrics = administration.dashboard().get("modele")
    return {"articles": len(get_index().articles), "modele": metrics}


# ---- Authentification (OTP par e-mail) --------------------------------------------------------

class OtpRequest(BaseModel):
    email: str
    intention: str = "inscription"     # inscription | connexion | admin


class OtpVerify(BaseModel):
    email: str
    code: str


REQUIRED_FIELDS = {
    "entreprise": ["raison_sociale", "matricule_fiscal", "forme_juridique", "secteur", "gouvernorat", "effectif", "regime"],
    "conseil": ["cabinet", "profession", "numero_inscription", "gouvernorat"],
    "verificateur": ["matricule_agent", "grade", "structure", "gouvernorat"],
    "contentieux": ["structure", "perimetre", "objectifs"],
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


@app.post("/api/auth/otp/demander", tags=["authentification"])
def otp_demander(req: OtpRequest):
    try:
        return auth.request_otp(req.email, req.intention)
    except auth.AuthError as e:
        _raise(e)


@app.post("/api/auth/otp/verifier", tags=["authentification"])
def otp_verifier(req: OtpVerify):
    try:
        out = auth.verify_otp(req.email, req.code)
    except auth.AuthError as e:
        _raise(e)
    get_store().log("otp_verifie", auth.mask(req.email.strip().lower()), "Identité vérifiée par code à usage unique",
                    "securite", req.email.strip().lower())
    return out


@app.post("/api/auth/profil", tags=["authentification"])
def enregistrer_profil(req: ProfilRequest, session: dict = Depends(current_session)):
    if req.role not in REQUIRED_FIELDS:
        raise HTTPException(422, "Rôle inconnu.")
    missing = [f for f in REQUIRED_FIELDS[req.role] if not str(req.details.get(f, "")).strip()]
    if not req.nom.strip() or not req.prenom.strip():
        missing.insert(0, "nom / prénom")
    if missing:
        raise HTTPException(422, "Champs obligatoires manquants : " + ", ".join(missing))
    if req.role == "entreprise":
        mf = str(req.details["matricule_fiscal"]).upper().replace(" ", "")
        if not MATRICULE_RE.match(mf):
            raise HTTPException(422, "Matricule fiscal invalide (format : 1234567A/A/M/000).")
        req.details["matricule_fiscal"] = mf
    if not (req.consentements.get("cgu") and req.consentements.get("donnees_personnelles")):
        raise HTTPException(422, "Les conditions d'utilisation et le traitement des données (loi 2004-63) doivent être acceptés.")
    try:
        user = auth.complete_signup(session, req.model_dump())
    except auth.AuthError as e:
        _raise(e)
    get_store().log("inscription", f"{req.prenom} {req.nom} ({req.role})", "Compte créé après vérification OTP", "securite", user["email"])
    return {"ok": True, "utilisateur": user}


@app.get("/api/auth/moi", tags=["authentification"])
def moi(session: dict = Depends(current_session)):
    user = repo().get_user(session["email"])
    return {"role": session.get("role"), "email": auth.mask(session["email"]),
            "utilisateur": auth.public_user(user) if user else None}


@app.post("/api/auth/deconnexion", tags=["authentification"])
def deconnexion(authorization: str | None = Header(default=None)):
    auth.logout((authorization or "").removeprefix("Bearer ").strip())
    return {"ok": True}


# ---- Espace entreprise (contribuable et conseil) -----------------------------------------------

def _save_analysis(result: AnalyseNotification, session: dict) -> AnalyseNotification:
    row = repo().analysis_add({
        "utilisateur_id": session["utilisateur_id"], "reference": result.notification.reference,
        "entreprise": result.notification.entreprise.nom, "montant_total": result.montant_total,
        "montant_contestable": result.montant_contestable, "date_limite": result.date_limite_reponse.isoformat(),
        "nb_vices": sum(p.statut == "vice" for p in result.procedure), "resultat": result.model_dump(mode="json")})
    result.analyse_id = row["id"]
    user = repo().get_user(session["email"])
    if user:
        rappels.echeance_enregistree(row, user)
    return result


@app.post("/api/contribuable/analyser", response_model=AnalyseNotification, tags=["contribuable"])
async def analyser_fichier(fichier: UploadFile = File(...), pieces_ratio: float = Form(analysis.DEFAULT_PIECES_RATIO),
                           langue: str = Form("fr"), session: dict = Depends(require(*CONTRIBUABLE))):
    """Upload a notification (PDF, image or text), get the full analysis, saved to the user's space."""
    data = await fichier.read()
    try:
        notif, _mode = extraction.from_upload(data, fichier.filename or "", fichier.content_type)
    except extraction.ExtractionError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    result = analysis.analyse(notif, pieces_ratio, today=TODAY, langue="derja" if langue == "derja" else "fr")
    _save_analysis(result, session)
    get_store().log("analyse_notification", notif.reference,
                    f"{sum(c.contestabilite != 'solide' for c in result.chefs)} chef(s) contestable(s)", result.mode, session["email"])
    return result


@app.get("/api/contribuable/analyses", tags=["contribuable"])
def mes_analyses(session: dict = Depends(require(*CONTRIBUABLE))):
    rows = repo().analyses_for(session["utilisateur_id"])
    return [{k: r[k] for k in ("id", "reference", "entreprise", "montant_total", "montant_contestable", "date_limite",
                               "nb_vices", "cree_le")} | {"jours_restants": (date.fromisoformat(str(r["date_limite"])) - TODAY).days}
            for r in rows]


@app.get("/api/contribuable/analyses/{analyse_id}", response_model=AnalyseNotification, tags=["contribuable"])
def une_analyse(analyse_id: str, langue: str | None = None, session: dict = Depends(require(*CONTRIBUABLE))):
    row = repo().analysis_get(analyse_id, session["utilisateur_id"])
    if row is None:
        raise HTTPException(404, "Analyse introuvable")
    result = AnalyseNotification.model_validate(row["resultat"])
    if langue and langue != result.langue:   # switch language on demand (FR <-> derja)
        result = analysis.analyse(result.notification, today=TODAY, langue="derja" if langue == "derja" else "fr")
    result.analyse_id = analyse_id
    return result


class ReponseRequest(BaseModel):
    analyse_id: str
    signataire: str = "Le Gérant"


@app.post("/api/contribuable/brouillon", tags=["contribuable"])
def brouillon(req: ReponseRequest, session: dict = Depends(require(*CONTRIBUABLE))):
    row = repo().analysis_get(req.analyse_id, session["utilisateur_id"])
    if row is None:
        raise HTTPException(404, "Analyse introuvable")
    a = AnalyseNotification.model_validate(row["resultat"])
    text, mode = drafting.draft_reply(a, req.signataire)
    repo().reponse_add({"analyse_id": req.analyse_id, "utilisateur_id": session["utilisateur_id"], "lettre": text, "mode": mode})
    get_store().log("brouillon_reponse", a.notification.reference, "Brouillon de réponse généré", mode, session["email"])
    return {"lettre": text, "mode": mode}


@app.get("/api/contribuable/reponses", tags=["contribuable"])
def mes_reponses(session: dict = Depends(require(*CONTRIBUABLE))):
    return repo().reponses_for(session["utilisateur_id"])


class QuestionRequest(BaseModel):
    question: str
    langue: str = "fr"
    historique: list[assistant.Echange] = []
    analyse_id: str | None = None


@app.post("/api/contribuable/assistant", response_model=assistant.AssistantAnswer, tags=["contribuable"])
def assistant_ia(req: QuestionRequest, session: dict = Depends(require(*CONTRIBUABLE, *ADMINISTRATION))):
    return assistant.answer(req.question, req.langue, req.historique, _assistant_context(req, session))


def _assistant_context(req: QuestionRequest, session: dict) -> dict | None:
    contexte = None
    if req.analyse_id and session.get("utilisateur_id"):
        row = repo().analysis_get(req.analyse_id, session["utilisateur_id"])
        if row:
            r = row["resultat"]
            contexte = {"reference": r["notification"]["reference"], "date_limite": r["date_limite_reponse"],
                        "resume": r["resume"], "chefs": [{"libelle": c["chef"]["libelle"], "contestabilite": c["contestabilite"],
                                                          "montant": c["chef"]["montant_principal"]} for c in r["chefs"]],
                        "vices": [p["detail"] for p in r["procedure"] if p["statut"] == "vice"]}
    return contexte


@app.post("/api/contribuable/assistant/stream", tags=["contribuable"])
def assistant_stream(req: QuestionRequest, session: dict = Depends(require(*CONTRIBUABLE, *ADMINISTRATION))):
    """Streamed answer (NDJSON events: articles, delta…, fin)."""
    contexte = _assistant_context(req, session)

    def events():
        for ev in assistant.answer_stream(req.question, req.langue, req.historique, contexte):
            yield json.dumps(ev, ensure_ascii=False) + "\n"
    return StreamingResponse(events(), media_type="application/x-ndjson", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/api/exemples", tags=["contribuable"])
def exemples(_: dict = Depends(current_session)) -> list[dict]:
    return [{"nom": p.stem, "fichier": p.name} for p in sorted((SYNTHETIC_DIR / "samples").glob("*.pdf"))]


@app.get("/api/exemples/{nom}", tags=["contribuable"])
def exemple(nom: str, _: dict = Depends(current_session)):
    path = (SYNTHETIC_DIR / "samples" / nom).resolve()
    if path.parent != (SYNTHETIC_DIR / "samples").resolve() or not path.exists():
        raise HTTPException(404, "Exemple introuvable")
    return FileResponse(path, media_type="application/pdf", filename=nom)


class VoixRequest(BaseModel):
    texte: str
    source: str = "fr"     # language of the text: fr | derja
    langue: str = "fr"     # language to listen in: fr | en | derja


@app.post("/api/voix", tags=["contribuable"], response_class=Response)
def lire_a_voix_haute(req: VoixRequest, _: dict = Depends(current_session)):
    """Text-to-speech of an explanation, in French, English or Tunisian derja (MP3)."""
    if not req.texte.strip():
        raise HTTPException(422, "Texte vide.")
    try:
        audio = voix.synthese(req.texte, req.source, req.langue)
    except voix.VoixIndisponible as e:
        raise HTTPException(503, str(e)) from e
    return Response(content=audio, media_type="audio/mpeg", headers={"Cache-Control": "private, max-age=86400"})


# ---- Favoris, notifications et exports (tous les espaces) ----------------------------------------

class FavoriRequest(BaseModel):
    type: str      # dossier | article | reponse | assistant | dossier_admin
    ref: str
    titre: str
    extrait: str = ""
    lien: str = ""


def _user_id(session: dict) -> str:
    if not session.get("utilisateur_id"):
        raise HTTPException(403, "Les favoris sont réservés aux comptes utilisateurs.")
    return session["utilisateur_id"]


@app.get("/api/favoris", tags=["favoris"])
def mes_favoris(session: dict = Depends(current_session)):
    try:
        return repo().favoris_list(_user_id(session))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(503, "Favoris indisponibles : la table « favoris » n'existe pas encore dans la base.") from e


@app.post("/api/favoris", tags=["favoris"])
def ajouter_favori(req: FavoriRequest, session: dict = Depends(current_session)):
    if req.type not in {"dossier", "article", "reponse", "assistant", "dossier_admin"}:
        raise HTTPException(422, "Type de favori inconnu.")
    return repo().favoris_add({"utilisateur_id": _user_id(session), "type": req.type, "ref": req.ref[:200],
                               "titre": req.titre[:200], "extrait": req.extrait[:1000], "lien": req.lien[:300]})


@app.delete("/api/favoris/{fav_id}", tags=["favoris"])
def retirer_favori(fav_id: str, session: dict = Depends(current_session)):
    repo().favoris_delete(fav_id, _user_id(session))
    return {"ok": True}


@app.get("/api/notifications", tags=["notifications"])
def notifications(session: dict = Depends(current_session)):
    """In-app bell: reply deadlines for taxpayers, expiring reply windows for the administration."""
    items = []
    if session.get("role") in CONTRIBUABLE and session.get("utilisateur_id"):
        for r in repo().analyses_for(session["utilisateur_id"]):
            d = date.fromisoformat(str(r["date_limite"]))
            jours = (d - TODAY).days
            if jours > 15:
                continue
            items.append({"id": r["id"], "niveau": "urgent" if jours <= 3 else "bientot" if jours <= 7 else "info",
                          "titre": ("Délai dépassé" if jours < 0 else f"J-{jours} · répondre à {r['reference']}"),
                          "detail": f"{r['entreprise']} · date limite {d:%d/%m/%Y}", "lien": f"/entreprise/dossiers/{r['id']}",
                          "jours": jours})
    elif session.get("role") in ADMINISTRATION:
        for f in get_store().open_files.values():
            if f.dossier.etape != "Notification":
                continue
            fin = f.dossier.notification.date_notification.toordinal() + DELAI_REPONSE_JOURS - TODAY.toordinal()
            if 0 <= fin <= 7:
                items.append({"id": f.dossier.id, "niveau": "urgent" if fin <= 2 else "bientot",
                              "titre": f"J-{fin} · fin du délai de réponse du contribuable",
                              "detail": f"{f.dossier.notification.entreprise.nom} · taxation d'office possible ensuite (art. 47)",
                              "lien": f"/administration/dossier/{f.dossier.id}", "jours": fin})
    items.sort(key=lambda x: x["jours"])
    return {"total": len(items), "urgents": sum(i["niveau"] == "urgent" for i in items), "items": items[:15]}


@app.get("/api/contribuable/analyses/{analyse_id}/pdf", tags=["contribuable"])
def analyse_pdf(analyse_id: str, session: dict = Depends(require(*CONTRIBUABLE))):
    row = repo().analysis_get(analyse_id, session["utilisateur_id"])
    if row is None:
        raise HTTPException(404, "Analyse introuvable")
    a = AnalyseNotification.model_validate(row["resultat"])
    lettre = next((r["lettre"] for r in repo().reponses_for(session["utilisateur_id"]) if r["analyse_id"] == analyse_id), None)
    pdf = export_pdf.rapport_analyse(a, lettre)
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="JISER_{a.notification.reference}.pdf"'})


@app.get("/api/admin/dossiers/{dossier_id}/pdf", tags=["administration"])
def dossier_pdf(dossier_id: str, avec_avis: bool = True, session: dict = Depends(require(*ADMINISTRATION))):
    detail = administration.dossier_detail(dossier_id, session["email"])
    if detail is None:
        raise HTTPException(404, "Dossier introuvable")
    avis = ai_admin.avis_dossier(detail).model_dump() if avec_avis else None
    pdf = export_pdf.fiche_dossier(detail, avis)
    ref = detail["dossier"]["notification"]["reference"]
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="JISER_dossier_{ref}.pdf"'})


# ---- Espace administration fiscale ------------------------------------------------------------

@app.get("/api/admin/dossiers", tags=["administration"])
def dossiers(limit: int = 100, gouvernorat: str | None = None, etape: str | None = None, groupe: str | None = None,
             _: dict = Depends(require(*ADMINISTRATION))):
    return administration.triage(limit, gouvernorat, etape, groupe)


@app.get("/api/admin/dossiers/{dossier_id}", tags=["administration"])
def dossier(dossier_id: str, session: dict = Depends(require(*ADMINISTRATION))):
    detail = administration.dossier_detail(dossier_id, session["email"])
    if detail is None:
        raise HTTPException(404, "Dossier introuvable")
    return detail


@app.post("/api/admin/controle-qualite", response_model=AnalyseNotification, tags=["administration"])
async def controle_qualite(fichier: UploadFile = File(...), session: dict = Depends(require(*ADMINISTRATION))):
    """Auditor uploads a draft notification before sending it: same checks, to fix weaknesses first."""
    data = await fichier.read()
    try:
        notif, _ = extraction.from_upload(data, fichier.filename or "", fichier.content_type)
    except extraction.ExtractionError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    result = analysis.analyse(notif, pieces_ratio=0.3, today=notif.date_notification)
    get_store().log("controle_qualite", notif.reference,
                    f"{sum(p.statut == 'vice' for p in result.procedure)} point(s) de procédure à corriger", result.mode, session["email"])
    return result


@app.get("/api/admin/tableau-de-bord", tags=["administration"])
def tableau_de_bord(_: dict = Depends(require(*ADMINISTRATION))):
    return administration.dashboard()


@app.get("/api/admin/synthese-ia", response_model=ai_admin.Synthese, tags=["administration"])
def synthese_ia(session: dict = Depends(require(*ADMINISTRATION))):
    out = ai_admin.synthese_stock(administration.dashboard())
    get_store().log("synthese_stock", "Stock de dossiers", out.actions[0].titre if out.actions else "Synthèse", out.mode, session["email"])
    return out


@app.get("/api/admin/dossiers/{dossier_id}/avis-ia", response_model=ai_admin.AvisDossier, tags=["administration"])
def avis_ia(dossier_id: str, session: dict = Depends(require(*ADMINISTRATION))):
    detail = administration.dossier_detail(dossier_id, session["email"])
    if detail is None:
        raise HTTPException(404, "Dossier introuvable")
    out = ai_admin.avis_dossier(detail)
    get_store().log("avis_juridique", detail["dossier"]["notification"]["reference"], "Avis et projet de conciliation", out.mode, session["email"])
    return out


class DecisionRequest(BaseModel):
    decision: str   # "validee" | "refusee"


@app.post("/api/admin/dossiers/{dossier_id}/decision", tags=["administration"])
def decision(dossier_id: str, req: DecisionRequest, session: dict = Depends(require(*ADMINISTRATION))):
    """The human decision on the AI's settlement proposal, recorded in the audit trail."""
    if req.decision not in {"validee", "refusee"}:
        raise HTTPException(422, "Décision invalide.")
    d = get_store().dossiers.get(dossier_id)
    if d is None:
        raise HTTPException(404, "Dossier introuvable")
    repo().journal_add({"action": "decision_conciliation", "cible": d.notification.reference,
                        "recommandation": "Proposition de conciliation", "mode": "humain",
                        "decision_humaine": "validée" if req.decision == "validee" else "refusée", "utilisateur": session["email"]})
    return {"ok": True}


@app.post("/api/admin/ameliorer-notification", response_model=ai_admin.Ameliorations, tags=["administration"])
def ameliorer(a: AnalyseNotification, session: dict = Depends(require(*ADMINISTRATION))):
    out = ai_admin.ameliorer_notification(a)
    get_store().log("amelioration_motivation", a.notification.reference, f"{len(out.ameliorations)} motivation(s) proposée(s)", out.mode, session["email"])
    return out


@app.get("/api/admin/conciliations", tags=["administration"])
def conciliations(limit: int = 30, _: dict = Depends(require(*ADMINISTRATION))):
    """Files where an amicable settlement recovers the most compared with litigation."""
    store = get_store()
    rows = []
    for f in sorted(store.open_files.values(), key=lambda f: f.priority, reverse=True)[:150]:
        c = administration.settlement(f.dossier)
        rows.append({**administration.file_summary(f), "montant_propose": c["montant_propose"],
                     "montant_attendu_contentieux": c["montant_attendu_contentieux"],
                     "gain_immediat": round(c["montant_propose"] - c["montant_attendu_contentieux"], 3)})
    rows.sort(key=lambda r: r["montant_propose"], reverse=True)
    return rows[:limit]


# ---- Admin plateforme (privé, e-mails autorisés uniquement) --------------------------------------

@app.get("/api/plateforme/utilisateurs", tags=["admin plateforme"])
def utilisateurs(_: dict = Depends(require("admin"))):
    return [auth.public_user(u) | {"cree_le": u.get("cree_le"), "derniere_connexion": u.get("derniere_connexion")}
            for u in repo().list_users()]


@app.get("/api/plateforme/journal", tags=["admin plateforme"])
def journal(limit: int = 100, _: dict = Depends(require("admin"))):
    return repo().journal_list(limit)


@app.get("/api/plateforme/base-juridique", tags=["admin plateforme"])
def base_juridique(_: dict = Depends(require("admin"))):
    out = []
    for path in sorted(LEGAL_DIR.glob("*.json")):
        arts = json.loads(path.read_text(encoding="utf-8"))
        if arts:
            out.append({"code": arts[0]["code"], "nom": arts[0]["code_name"], "articles": len(arts),
                        "source": "Jurisite Tunisie (jurisitetunisie.com)"})
    return out


@app.get("/api/plateforme/recherche-juridique", tags=["admin plateforme"])
def recherche(q: str, k: int = 5, _: dict = Depends(require("admin"))):
    return get_index().search(q, k=k)


@app.post("/api/plateforme/rappels", tags=["admin plateforme"])
def lancer_rappels(_: dict = Depends(require("admin"))):
    """Send now every deadline reminder that is due (they also run automatically every 6 hours)."""
    return rappels.envoyer_rappels()


@app.get("/api/plateforme/systeme", tags=["admin plateforme"])
def systeme(_: dict = Depends(require("admin"))):
    from .config import N8N_OTP_WEBHOOK_URL, N8N_RAPPEL_WEBHOOK_URL, N8N_WELCOME_WEBHOOK_URL
    return {"llm": llm.status(), "base": repo().kind, "n8n_otp": bool(N8N_OTP_WEBHOOK_URL),
            "n8n_bienvenue": bool(N8N_WELCOME_WEBHOOK_URL), "n8n_rappels": bool(N8N_RAPPEL_WEBHOOK_URL),
            "modele": administration.dashboard().get("modele")}


# ---- Intégration n8n (rappels d'échéances) ----------------------------------------------------

def n8n_auth(x_jiser_secret: str | None = Header(default=None)) -> None:
    if not N8N_SHARED_SECRET or not hmac.compare_digest(x_jiser_secret or "", N8N_SHARED_SECRET):
        raise HTTPException(401, "Secret n8n invalide.")


@app.get("/api/n8n/echeances", tags=["n8n"])
def echeances(jours: int = 7, _: None = Depends(n8n_auth)):
    """Called daily by the n8n reminder workflow: replies due within `jours` days."""
    return repo().upcoming_deadlines(jours)
