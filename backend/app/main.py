"""JISER API — the bridge between taxpayers and the tax administration.

Run from the repo root:
    .venv/Scripts/python -m uvicorn app.main:app --reload --app-dir backend
Docs (Swagger): http://127.0.0.1:8000/docs

Access control (deps.py): every private route declares a permission; the role is re-read from the
database on each request; pending accounts see nothing; administration users only see the files of
their centre; the minister only sees anonymous aggregates.
"""
from __future__ import annotations

import json
import logging
import re
import threading
from datetime import date

import httpx
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from pydantic import BaseModel

from .config import CORS_ORIGINS, DATA_DIR, LEGAL_DIR, SYNTHETIC_DIR
from .deps import compte, current_session, journaliser_acces, n8n_auth, permission
from .domain import DELAI_REPONSE_JOURS
from .routers import comptes as comptes_router
from .routers import confidentialite, messagerie as messagerie_router, pilotage as pilotage_router, veille as veille_router
from .schemas import AnalyseNotification
from .services import (administration, ai_admin, analysis, assistant, auth, drafting, export_pdf, extraction, llm, pilotage, rappels,
                       securite, veille, voix)
from .services.db import repo
from .services.legal_rag import get_index
from .services.permissions import CENTRES, CENTRES_A, ROLE_LABELS, peut_voir_dossier, perimetre
from .services.store import TODAY, get_store

logging.basicConfig(level=logging.INFO)
app = FastAPI(title="JISER API", version="0.3.0",
              description="Plateforme IA pour le contentieux fiscal tunisien.")
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])
for r in (comptes_router, pilotage_router, messagerie_router, confidentialite, veille_router):
    app.include_router(r.router)


@app.exception_handler(httpx.TransportError)
async def reseau_indisponible(_request, exc: httpx.TransportError):
    """Internet or the database briefly unreachable (Wi-Fi drop, DNS): a clear message instead of a 500."""
    logging.getLogger("jiser").warning("network error: %s", exc)
    return JSONResponse(status_code=503, content={"detail": "Connexion momentanément perdue avec la base de données. "
                                                            "Vérifiez la connexion internet puis réessayez."})


@app.on_event("startup")
def warm_up() -> None:
    get_index()
    get_store()
    repo()
    threading.Thread(target=llm.probe, daemon=True).start()
    rappels.demarrer_planificateur()
    veille.demarrer_planificateur()


# ---- Public ---------------------------------------------------------------------------------

@app.get("/api/status", tags=["public"])
def status() -> dict:
    return {"ok": True, "llm": llm.status(), "articles": len(get_index().articles), "base": repo().kind,
            "date": TODAY.isoformat(), "recherche_hybride": get_index().hybride}


@app.get("/api/public/chiffres", tags=["public"])
def chiffres() -> dict:
    metrics = administration.dashboard().get("modele")
    return {"articles": len(get_index().articles), "modele": metrics}


@app.get("/api/public/referentiel", tags=["public"])
def referentiel() -> dict:
    """Roles and regional centres used by the onboarding."""
    return {"centres": CENTRES, "centres_a": CENTRES_A, "roles": ROLE_LABELS}


@app.get("/api/donnees-officielles", tags=["public"])
def donnees_officielles():
    """Real public figures on tax control and litigation (ministère des Finances), used by the dashboards."""
    return json.loads((DATA_DIR / "real" / "indicateurs_officiels.json").read_text(encoding="utf-8"))


# ---- Authentification (OTP par e-mail) --------------------------------------------------------

class OtpRequest(BaseModel):
    email: str
    intention: str = "inscription"     # inscription | connexion | admin


class OtpVerify(BaseModel):
    email: str
    code: str


REQUIRED_FIELDS = {
    "entreprise": ["raison_sociale", "matricule_fiscal", "forme_juridique", "secteur", "gouvernorat", "effectif", "regime"],
    "contentieux": ["centre", "matricule_agent", "grade"],
    "chef_centre": ["centre", "matricule_agent"],
    "ministre": ["cabinet"],
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
        raise HTTPException(e.status, str(e)) from e


@app.post("/api/auth/otp/verifier", tags=["authentification"])
def otp_verifier(req: OtpVerify):
    try:
        out = auth.verify_otp(req.email, req.code)
    except auth.AuthError as e:
        raise HTTPException(e.status, str(e)) from e
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
    if req.role in {"contentieux", "chef_centre"} and req.details.get("centre") not in CENTRES:
        raise HTTPException(422, "Centre régional inconnu.")
    if not (req.consentements.get("cgu") and req.consentements.get("donnees_personnelles")):
        raise HTTPException(422, "Les conditions d'utilisation et le traitement des données (loi 2004-63) doivent être acceptés.")
    try:
        user = auth.complete_signup(session, req.model_dump())
    except auth.AuthError as e:
        raise HTTPException(e.status, str(e)) from e
    get_store().log("inscription", f"{req.prenom} {req.nom} ({req.role})", "Demande d'accès créée après vérification OTP",
                    "securite", user["email"])
    return {"ok": True, "utilisateur": user}


@app.get("/api/auth/moi", tags=["authentification"])
def moi(session: dict = Depends(current_session)):
    user = repo().get_user(session["email"])
    role = session.get("role") if session.get("role") == "admin" else (user["role"] if user else session.get("role"))
    return {"role": role, "email": auth.mask(session["email"]), "utilisateur": auth.public_user(user) if user else None}


@app.post("/api/auth/deconnexion", tags=["authentification"])
def deconnexion(authorization: str | None = Header(default=None)):
    auth.logout((authorization or "").removeprefix("Bearer ").strip())
    return {"ok": True}


# ---- Espace entreprise --------------------------------------------------------------------------

ENTREPRISE = permission("analyses:propres")


def _langue(v: str | None) -> str:
    """Languages: French or Modern Standard Arabic ("derja", from the first version, now means Arabic)."""
    return "ar" if v in ("ar", "derja") else "fr"


def _save_analysis(result: AnalyseNotification, session: dict) -> AnalyseNotification:
    row = repo().analysis_add({
        "utilisateur_id": session["utilisateur_id"], "reference": result.notification.reference,
        "entreprise": result.notification.entreprise.nom, "montant_total": result.montant_total,
        "montant_contestable": result.montant_contestable, "date_limite": result.date_limite_reponse.isoformat(),
        "nb_vices": sum(p.statut == "vice" for p in result.procedure), "resultat": result.model_dump(mode="json")})
    result.analyse_id = row["id"]
    rappels.echeance_enregistree(row, session["user"])
    return result


@app.post("/api/contribuable/analyser", response_model=AnalyseNotification, tags=["contribuable"])
async def analyser_fichier(fichier: UploadFile | None = File(None), pages: list[UploadFile] | None = File(None),
                           pieces_ratio: float = Form(analysis.DEFAULT_PIECES_RATIO), langue: str = Form("fr"),
                           session: dict = Depends(ENTREPRISE)):
    """Upload a notification (PDF, photo(s) - one per page - or text), get the full analysis, saved encrypted."""
    from starlette.concurrency import run_in_threadpool
    envois = [f for f in ([fichier] if fichier else []) + list(pages or []) if f is not None]
    if not envois:
        raise HTTPException(422, "Aucun fichier reçu.")
    if sum(f.size or 0 for f in envois) > 40 * 1024 * 1024:
        raise HTTPException(413, "Fichiers trop volumineux (40 Mo au total).")
    fichiers = [(await f.read(), f.filename or "", f.content_type) for f in envois]

    def run() -> AnalyseNotification:
        try:
            notif, _mode = extraction.from_uploads(fichiers)
        except extraction.ExtractionError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e
        result = analysis.analyse(notif, pieces_ratio, today=TODAY, langue=_langue(langue))
        _save_analysis(result, session)
        get_store().log("analyse_notification", notif.reference,
                        f"{sum(c.contestabilite != 'solide' for c in result.chefs)} chef(s) contestable(s)", result.mode, session["email"])
        return result
    return await run_in_threadpool(run)


@app.get("/api/contribuable/analyses", tags=["contribuable"])
def mes_analyses(session: dict = Depends(ENTREPRISE)):
    rows = repo().analyses_for(session["utilisateur_id"])
    return [{k: r[k] for k in ("id", "reference", "entreprise", "montant_total", "montant_contestable", "date_limite",
                               "nb_vices", "cree_le")} | {"jours_restants": (date.fromisoformat(str(r["date_limite"])) - TODAY).days}
            for r in rows]


@app.get("/api/contribuable/analyses/{analyse_id}", response_model=AnalyseNotification, tags=["contribuable"])
def une_analyse(analyse_id: str, langue: str | None = None, session: dict = Depends(ENTREPRISE)):
    row = repo().analysis_get(analyse_id, session["utilisateur_id"])
    if row is None:
        raise HTTPException(404, "Analyse introuvable")
    ancienne = row["resultat"].get("langue") == "derja"   # dialect text from the first version: regenerate in Arabic
    result = AnalyseNotification.model_validate(row["resultat"])
    if ancienne or (langue and _langue(langue) != result.langue):   # switch language on demand (FR <-> AR)
        result = analysis.analyse(result.notification, today=TODAY, langue=_langue(langue or result.langue))
    result.analyse_id = analyse_id
    return result


class ReponseRequest(BaseModel):
    analyse_id: str
    signataire: str = "Le Gérant"


@app.post("/api/contribuable/brouillon", tags=["contribuable"])
def brouillon(req: ReponseRequest, session: dict = Depends(ENTREPRISE)):
    row = repo().analysis_get(req.analyse_id, session["utilisateur_id"])
    if row is None:
        raise HTTPException(404, "Analyse introuvable")
    a = AnalyseNotification.model_validate(row["resultat"])
    text, mode = drafting.draft_reply(a, req.signataire)
    repo().reponse_add({"analyse_id": req.analyse_id, "utilisateur_id": session["utilisateur_id"], "lettre": text, "mode": mode})
    get_store().log("brouillon_reponse", a.notification.reference, "Brouillon de réponse généré", mode, session["email"])
    return {"lettre": text, "mode": mode}


@app.get("/api/contribuable/reponses", tags=["contribuable"])
def mes_reponses(session: dict = Depends(ENTREPRISE)):
    return repo().reponses_for(session["utilisateur_id"])


class QuestionRequest(BaseModel):
    question: str
    langue: str = "fr"
    historique: list[assistant.Echange] = []
    analyse_id: str | None = None


COPILOTE = permission("copilote")


@app.post("/api/contribuable/assistant", response_model=assistant.AssistantAnswer, tags=["contribuable"])
def assistant_ia(req: QuestionRequest, session: dict = Depends(COPILOTE)):
    out = assistant.answer(req.question, req.langue, req.historique, _assistant_context(req, session))
    get_store().log("assistant", "Question à l'assistant", "Réponse avec articles cités", out.mode, session["email"])
    return out


def _assistant_context(req: QuestionRequest, session: dict) -> dict | None:
    contexte = None
    if req.analyse_id and session.get("role") == "entreprise":
        row = repo().analysis_get(req.analyse_id, session["utilisateur_id"])
        if row:
            r = row["resultat"]
            contexte = {"reference": r["notification"]["reference"], "date_limite": r["date_limite_reponse"],
                        "resume": r["resume"], "chefs": [{"libelle": c["chef"]["libelle"], "contestabilite": c["contestabilite"],
                                                          "montant": c["chef"]["montant_principal"]} for c in r["chefs"]],
                        "vices": [p["detail"] for p in r["procedure"] if p["statut"] == "vice"]}
    return contexte


@app.post("/api/contribuable/assistant/stream", tags=["contribuable"])
def assistant_stream(req: QuestionRequest, session: dict = Depends(COPILOTE)):
    """Streamed answer (NDJSON events: articles, delta…, fin)."""
    contexte = _assistant_context(req, session)
    get_store().log("assistant", "Question à l'assistant", "Réponse en direct avec articles cités", "ia", session["email"])
    ids = securite.identifiants_de(session.get("user"))
    consent = ((session.get("user") or {}).get("consentements") or {}).get("analyse_ia", True)

    def events():
        # the response is produced after the request context: set the confidentiality context again
        with securite.contexte(ids, bool(consent)):
            for ev in assistant.answer_stream(req.question, req.langue, req.historique, contexte):
                yield json.dumps(ev, ensure_ascii=False) + "\n"
    return StreamingResponse(events(), media_type="application/x-ndjson", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/api/exemples", tags=["contribuable"])
def exemples(_: dict = Depends(compte)) -> list[dict]:
    return [{"nom": p.stem, "fichier": p.name} for p in sorted((SYNTHETIC_DIR / "samples").glob("*.pdf"))]


@app.get("/api/exemples/{nom}", tags=["contribuable"])
def exemple(nom: str, _: dict = Depends(compte)):
    path = (SYNTHETIC_DIR / "samples" / nom).resolve()
    if path.parent != (SYNTHETIC_DIR / "samples").resolve() or not path.exists():
        raise HTTPException(404, "Exemple introuvable")
    return FileResponse(path, media_type="application/pdf", filename=nom)


class VoixRequest(BaseModel):
    texte: str
    source: str = "fr"     # language of the text: fr | ar
    langue: str = "fr"     # language to listen in: fr | en | ar


@app.post("/api/voix", tags=["contribuable"], response_class=Response)
def lire_a_voix_haute(req: VoixRequest, _: dict = Depends(compte)):
    """Text-to-speech of an explanation, in French, English or Arabic (MP3). Names are never sent."""
    if not req.texte.strip():
        raise HTTPException(422, "Texte vide.")
    try:
        audio = voix.synthese(req.texte, _langue(req.source), req.langue if req.langue == "en" else _langue(req.langue))
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


FAVORIS = permission("favoris")


def _user_id(session: dict) -> str:
    if not session.get("utilisateur_id"):
        raise HTTPException(403, "Les favoris sont réservés aux comptes utilisateurs.")
    return session["utilisateur_id"]


@app.get("/api/favoris", tags=["favoris"])
def mes_favoris(session: dict = Depends(FAVORIS)):
    try:
        return repo().favoris_list(_user_id(session))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(503, "Favoris indisponibles : la table « favoris » n'existe pas encore dans la base.") from e


@app.post("/api/favoris", tags=["favoris"])
def ajouter_favori(req: FavoriRequest, session: dict = Depends(FAVORIS)):
    if req.type not in {"dossier", "article", "reponse", "assistant", "dossier_admin"}:
        raise HTTPException(422, "Type de favori inconnu.")
    return repo().favoris_add({"utilisateur_id": _user_id(session), "type": req.type, "ref": req.ref[:200],
                               "titre": req.titre[:200], "extrait": req.extrait[:1000], "lien": req.lien[:300]})


@app.delete("/api/favoris/{fav_id}", tags=["favoris"])
def retirer_favori(fav_id: str, session: dict = Depends(FAVORIS)):
    repo().favoris_delete(fav_id, _user_id(session))
    return {"ok": True}


@app.get("/api/notifications", tags=["notifications"])
def notifications(session: dict = Depends(compte)):
    """In-app bell: reply deadlines for taxpayers, expiring reply windows and approvals for the administration."""
    items = []
    role, user = session.get("role"), session.get("user")
    if role == "entreprise":
        for r in repo().analyses_for(session["utilisateur_id"]):
            d = date.fromisoformat(str(r["date_limite"]))
            jours = (d - TODAY).days
            if jours > 15:
                continue
            items.append({"id": r["id"], "niveau": "urgent" if jours <= 3 else "bientot" if jours <= 7 else "info",
                          "titre": ("Délai dépassé" if jours < 0 else f"J-{jours} · répondre à {r['reference']}"),
                          "detail": f"{r['entreprise']} · date limite {d:%d/%m/%Y}", "lien": f"/entreprise/dossiers/{r['id']}",
                          "jours": jours})
    elif role in {"contentieux", "chef_centre"}:
        for f in get_store().open_files.values():
            if f.dossier.etape != "Notification" or not peut_voir_dossier(user, role, f.dossier.notification.entreprise.gouvernorat):
                continue
            fin = f.dossier.notification.date_notification.toordinal() + DELAI_REPONSE_JOURS - TODAY.toordinal()
            if 0 <= fin <= 7:
                items.append({"id": f.dossier.id, "niveau": "urgent" if fin <= 2 else "bientot",
                              "titre": f"J-{fin} · fin du délai de réponse du contribuable",
                              "detail": f"{f.dossier.notification.entreprise.nom} · taxation d'office possible ensuite (art. 47)",
                              "lien": f"/administration/dossier/{f.dossier.id}", "jours": fin})
        if role == "chef_centre":
            for c in pilotage.conciliations_a_valider(user):
                items.append({"id": c["id"], "niveau": "urgent", "titre": f"Conciliation à valider · {c['reference']}",
                              "detail": f"Proposée par un agent de votre centre : {c['montant_propose']:,.0f} DT".replace(",", " "),
                              "lien": "/administration/equipe", "jours": -1})
    items.sort(key=lambda x: x["jours"])
    return {"total": len(items), "urgents": sum(i["niveau"] == "urgent" for i in items), "items": items[:15]}


@app.get("/api/contribuable/analyses/{analyse_id}/pdf", tags=["contribuable"])
def analyse_pdf(analyse_id: str, session: dict = Depends(ENTREPRISE)):
    row = repo().analysis_get(analyse_id, session["utilisateur_id"])
    if row is None:
        raise HTTPException(404, "Analyse introuvable")
    a = AnalyseNotification.model_validate(row["resultat"])
    lettre = next((r["lettre"] for r in repo().reponses_for(session["utilisateur_id"]) if r["analyse_id"] == analyse_id), None)
    pdf = export_pdf.rapport_analyse(a, lettre)
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="JISER_{a.notification.reference}.pdf"'})


# ---- Espace administration fiscale (périmètre du centre) ------------------------------------------

AGENT = permission("dossiers:lire")


def _dossier_autorise(dossier_id: str, session: dict):
    d = get_store().dossiers.get(dossier_id)
    if d is None or not peut_voir_dossier(session.get("user"), session["role"], d.notification.entreprise.gouvernorat):
        raise HTTPException(404, "Dossier introuvable")   # same answer whether it exists elsewhere or not
    # the company's identity never reaches an external AI in clear
    securite.ajouter_identifiants({d.notification.entreprise.nom: "ENTREPRISE", d.notification.entreprise.matricule_fiscal: "MATRICULE"})
    return d


@app.get("/api/admin/dossiers", tags=["administration"])
def dossiers(limit: int = 100, gouvernorat: str | None = None, etape: str | None = None, groupe: str | None = None,
             mes: bool = False, session: dict = Depends(AGENT)):
    zone = perimetre(session.get("user"))
    out = administration.triage(5000 if mes else limit, zone or gouvernorat, etape, groupe)
    affect = repo().affectations_all()
    for row in out["dossiers"]:
        a = affect.get(row["id"])
        row["affecte_a"] = a["agent_nom"] if a else None
        row["affecte_a_moi"] = bool(a and a.get("agent_id") == session.get("utilisateur_id"))
    if mes:
        out["dossiers"] = [r for r in out["dossiers"] if r["affecte_a_moi"]][:limit]
    out["perimetre"] = zone or "National"
    return out


@app.get("/api/admin/dossiers/{dossier_id}", tags=["administration"])
def dossier(dossier_id: str, session: dict = Depends(AGENT)):
    d = _dossier_autorise(dossier_id, session)
    detail = administration.dossier_detail(dossier_id, session["email"])
    journaliser_acces(d.notification.reference, session, "Consultation du dossier")
    a = repo().affectations_all().get(dossier_id)
    return {**detail, "affectation": a}


@app.get("/api/admin/dossiers/{dossier_id}/pdf", tags=["administration"])
def dossier_pdf(dossier_id: str, avec_avis: bool = True, session: dict = Depends(AGENT)):
    d = _dossier_autorise(dossier_id, session)
    detail = administration.dossier_detail(dossier_id, session["email"])
    avis = ai_admin.avis_dossier(detail).model_dump() if avec_avis else None
    journaliser_acces(d.notification.reference, session, "Export PDF du dossier")
    pdf = export_pdf.fiche_dossier(detail, avis)
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="JISER_dossier_{d.notification.reference}.pdf"'})


@app.post("/api/admin/controle-qualite", response_model=AnalyseNotification, tags=["administration"])
async def controle_qualite(fichier: UploadFile = File(...), session: dict = Depends(permission("controle_qualite"))):
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
def tableau_de_bord(session: dict = Depends(permission("stats:centre"))):
    return administration.dashboard(perimetre(session.get("user")))


@app.get("/api/admin/synthese-ia", response_model=ai_admin.Synthese, tags=["administration"])
def synthese_ia(session: dict = Depends(permission("stats:centre"))):
    out = ai_admin.synthese_stock(administration.dashboard(perimetre(session.get("user"))))
    get_store().log("synthese_stock", "Stock de dossiers", out.actions[0].titre if out.actions else "Synthèse", out.mode, session["email"])
    return out


@app.get("/api/admin/dossiers/{dossier_id}/avis-ia", response_model=ai_admin.AvisDossier, tags=["administration"])
def avis_ia(dossier_id: str, session: dict = Depends(permission("dossier:avis"))):
    d = _dossier_autorise(dossier_id, session)
    detail = administration.dossier_detail(dossier_id, session["email"])
    out = ai_admin.avis_dossier(detail)
    get_store().log("avis_juridique", d.notification.reference, "Avis et projet de conciliation", out.mode, session["email"])
    return out


class DecisionRequest(BaseModel):
    decision: str   # "validee" | "refusee"


@app.post("/api/admin/dossiers/{dossier_id}/decision", tags=["administration"])
def decision(dossier_id: str, req: DecisionRequest, session: dict = Depends(permission("conciliation:proposer"))):
    """The officer's decision on the AI's settlement proposal. Above the threshold, the head of centre must approve."""
    if req.decision not in {"validee", "refusee"}:
        raise HTTPException(422, "Décision invalide.")
    d = _dossier_autorise(dossier_id, session)
    if req.decision == "refusee":
        repo().journal_add({"action": "decision_conciliation", "cible": d.notification.reference, "recommandation": "Proposition de conciliation",
                            "mode": "humain", "decision_humaine": "refusée", "utilisateur": session["email"]})
        return {"ok": True, "statut": "refusee", "message": "Proposition refusée."}
    return pilotage.proposer_conciliation(session, dossier_id)


@app.post("/api/admin/ameliorer-notification", response_model=ai_admin.Ameliorations, tags=["administration"])
def ameliorer(a: AnalyseNotification, session: dict = Depends(permission("controle_qualite"))):
    out = ai_admin.ameliorer_notification(a)
    get_store().log("amelioration_motivation", a.notification.reference, f"{len(out.ameliorations)} motivation(s) proposée(s)", out.mode, session["email"])
    return out


@app.get("/api/admin/conciliations", tags=["administration"])
def conciliations(limit: int = 30, session: dict = Depends(AGENT)):
    """Files where an amicable settlement recovers the most compared with litigation (within the centre)."""
    store = get_store()
    zone = perimetre(session.get("user"))
    rows = []
    for f in sorted((f for f in store.open_files.values() if zone is None or f.dossier.notification.entreprise.gouvernorat == zone),
                    key=lambda f: f.priority, reverse=True)[:150]:
        c = administration.settlement(f.dossier)
        rows.append({**administration.file_summary(f), "montant_propose": c["montant_propose"],
                     "montant_attendu_contentieux": c["montant_attendu_contentieux"],
                     "gain_immediat": round(c["montant_propose"] - c["montant_attendu_contentieux"], 3)})
    rows.sort(key=lambda r: r["montant_propose"], reverse=True)
    return rows[:limit]


# ---- Admin plateforme (privé, e-mails autorisés uniquement) --------------------------------------

PLATEFORME = permission("plateforme")


@app.get("/api/plateforme/utilisateurs", tags=["admin plateforme"])
def utilisateurs(_: dict = Depends(PLATEFORME)):
    return [auth.public_user(u) | {"cree_le": u.get("cree_le"), "derniere_connexion": u.get("derniere_connexion")}
            for u in repo().list_users()]


@app.get("/api/plateforme/journal", tags=["admin plateforme"])
def journal(limit: int = 500, _: dict = Depends(PLATEFORME)):
    return repo().journal_list(limit)


SOURCES_CODES = {"cdpf": "Édition officielle 2024 (jibaya.tn, ministère des Finances)", "ctva": "Jurisite Tunisie",
                 "cirppis": "Jurisite Tunisie"}


@app.get("/api/plateforme/base-juridique", tags=["admin plateforme"])
def base_juridique(_: dict = Depends(PLATEFORME)):
    out = []
    for path in sorted(LEGAL_DIR.glob("*.json")):
        arts = json.loads(path.read_text(encoding="utf-8"))
        if arts and isinstance(arts, list):
            out.append({"code": arts[0]["code"], "nom": arts[0]["code_name"], "articles": len(arts),
                        "source": SOURCES_CODES.get(arts[0]["code"], "—")})
    return out


@app.get("/api/plateforme/recherche-juridique", tags=["admin plateforme"])
def recherche(q: str, k: int = 5, _: dict = Depends(PLATEFORME)):
    return get_index().search(q, k=k, hybride=True)


@app.post("/api/plateforme/rappels", tags=["admin plateforme"])
def lancer_rappels(_: dict = Depends(PLATEFORME)):
    """Send now every deadline reminder that is due (they also run automatically every 6 hours)."""
    return rappels.envoyer_rappels()


@app.get("/api/plateforme/systeme", tags=["admin plateforme"])
def systeme(_: dict = Depends(PLATEFORME)):
    from .config import N8N_NOTIF_WEBHOOK_URL, N8N_OTP_WEBHOOK_URL, N8N_RAPPEL_WEBHOOK_URL, N8N_WELCOME_WEBHOOK_URL
    return {"llm": llm.status(), "base": repo().kind, "n8n_otp": bool(N8N_OTP_WEBHOOK_URL),
            "n8n_bienvenue": bool(N8N_WELCOME_WEBHOOK_URL), "n8n_rappels": bool(N8N_RAPPEL_WEBHOOK_URL),
            "n8n_notifications": bool(N8N_NOTIF_WEBHOOK_URL), "recherche_hybride": get_index().hybride,
            "modele": administration.dashboard().get("modele")}


# ---- Intégration n8n (rappels d'échéances) ----------------------------------------------------

@app.get("/api/n8n/echeances", tags=["n8n"])
def echeances(jours: int = 7, _: None = Depends(n8n_auth)):
    """Called daily by the n8n reminder workflow: replies due within `jours` days."""
    return repo().upcoming_deadlines(jours)
