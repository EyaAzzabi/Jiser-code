"""Taxpayer rights (loi organique 2004-63): access log, export, erasure, consents, AI preview."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from ..deps import permission
from ..services import auth, securite
from ..services.db import repo
from ..services.permissions import ROLE_LABELS

router = APIRouter(prefix="/api/confidentialite", tags=["confidentialité"])
PROPRE = permission("donnees:propres")

# Register of processing activities (art. 7 and following of loi 2004-63), shown in the app
REGISTRE = [
    {"traitement": "Compte et vérification d'identité", "finalite": "Réserver l'accès aux personnes vérifiées",
     "donnees": "Identité, e-mail, fonction, matricule fiscal, justificatifs (chiffrés)", "base": "Consentement, mesures précontractuelles",
     "duree": "Durée du compte ; justificatifs supprimés 1 an après validation", "destinataires": "Validateur habilité (administrateur ou chef de centre)"},
    {"traitement": "Analyse des notifications", "finalite": "Expliquer la notification, contrôler la procédure, préparer la réponse",
     "donnees": "Contenu de la notification, montants, réponses (chiffrés)", "base": "Consentement",
     "duree": "Jusqu'à la suppression par l'utilisateur, au plus 10 ans (prescription fiscale)", "destinataires": "L'utilisateur seul"},
    {"traitement": "Messagerie avec l'administration", "finalite": "Échanger sur un dossier de redressement",
     "donnees": "Messages et pièces jointes (chiffrés)", "base": "Consentement, mission de service public",
     "duree": "Durée du dossier + 10 ans", "destinataires": "Agent affecté au dossier et chef de centre"},
    {"traitement": "IA générative (explications, assistant, rédaction)", "finalite": "Rendre la notification compréhensible",
     "donnees": "Textes pseudonymisés : aucun nom, matricule, e-mail ni téléphone", "base": "Consentement (retirable à tout moment)",
     "duree": "Non conservé par JISER au-delà du cache pseudonymisé", "destinataires": "Fournisseur d'IA (texte pseudonymisé uniquement)"},
    {"traitement": "Pilotage statistique", "finalite": "Piloter le contentieux au niveau national et régional",
     "donnees": "Agrégats anonymes (groupes de moins de 5 dossiers masqués)", "base": "Mission de service public",
     "duree": "Indéterminée (données anonymes)", "destinataires": "Ministre, chefs de centre"},
    {"traitement": "Journal d'audit et des accès", "finalite": "Tracer chaque recommandation de l'IA, décision et consultation",
     "donnees": "Action, rôle, date ; pas le contenu des dossiers", "base": "Obligation de sécurité (art. 18 et 19)",
     "duree": "5 ans", "destinataires": "Administrateur plateforme ; l'entreprise voit les accès à ses dossiers"},
]


@router.get("/registre")
def registre():
    return {"responsable": "JISER", "loi": "Loi organique n° 2004-63 du 27 juillet 2004 (INPDP)", "traitements": REGISTRE}


def _references(uid: str) -> list[str]:
    return sorted({a["reference"] for a in repo().analyses_for(uid)})


@router.get("/acces")
def acces(session: dict = Depends(PROPRE)):
    """Who consulted my files: role and centre of the reader, date, action."""
    return [{**a, "role_label": ROLE_LABELS.get(a["role"], a["role"])} for a in repo().acces_pour(_references(session["utilisateur_id"]))]


@router.get("/export")
def exporter(session: dict = Depends(PROPRE)):
    """Right of access: everything JISER holds about the user, decrypted, in one JSON file."""
    uid, user = session["utilisateur_id"], session["user"]
    convs = [c for c in repo().conversations_all() if c["entreprise_id"] == uid]
    data = {
        "export_du": datetime.now(timezone.utc).isoformat(),
        "profil": auth.public_user(user) | {"consentements": user.get("consentements"), "cree_le": user.get("cree_le")},
        "analyses": [{k: a[k] for k in ("id", "reference", "entreprise", "montant_total", "date_limite", "cree_le", "resultat")}
                     for a in repo().analyses_for(uid)],
        "reponses": repo().reponses_for(uid),
        "conversations": [{**c, "messages": repo().messages_for(c["id"])} for c in convs],
        "favoris": repo().favoris_list(uid),
        "justificatifs": repo().pieces_for(uid),
        "acces_a_mes_dossiers": repo().acces_pour(_references(uid)),
    }
    return Response(json.dumps(data, ensure_ascii=False, indent=2, default=str), media_type="application/json",
                    headers={"Content-Disposition": 'attachment; filename="JISER_mes_donnees.json"'})


class Suppression(BaseModel):
    confirmation: str


@router.post("/suppression")
def supprimer(req: Suppression, session: dict = Depends(PROPRE)):
    """Right to erasure: account, analyses, replies, messages, documents and favourites are deleted."""
    if req.confirmation.strip().upper() != "SUPPRIMER":
        raise HTTPException(422, "Tapez SUPPRIMER pour confirmer.")
    repo().journal_add({"action": "suppression_compte", "cible": auth.mask(session["email"]), "recommandation": "Droit à l'effacement",
                        "mode": "humain", "decision_humaine": "exécutée", "utilisateur": auth.mask(session["email"])})
    repo().delete_user(session["utilisateur_id"])
    return {"ok": True}


class Consentements(BaseModel):
    analyse_ia: bool
    communications: bool = False


@router.put("/consentements")
def consentements(req: Consentements, session: dict = Depends(PROPRE)):
    user = session["user"]
    c = {**(user.get("consentements") or {}), "analyse_ia": req.analyse_ia, "communications": req.communications,
         "modifie_le": datetime.now(timezone.utc).isoformat()}
    repo().update_user(user["id"], consentements=c)
    return {"ok": True, "consentements": c}


@router.get("/apercu-ia")
def apercu_ia(analyse_id: str | None = None, session: dict = Depends(PROPRE)):
    """Show the user exactly what an external AI receives: identifiers replaced by tokens."""
    user = session["user"]
    texte = None
    if analyse_id:
        row = repo().analysis_get(analyse_id, user["id"])
        if row:
            n = row["resultat"]["notification"]
            texte = (f"Notification {n['reference']} adressée à {n['entreprise']['nom']} (matricule {n['entreprise']['matricule_fiscal']}). "
                     + " ".join(f"Chef {c['id']} : {c['libelle']}, {c['montant_principal']:.0f} DT." for c in n["chefs"][:3]))
    if texte is None:
        d = user.get("details") or {}
        texte = (f"Bonjour, je suis {user['prenom']} {user['nom']}, gérant de {d.get('raison_sociale', 'mon entreprise')} "
                 f"(matricule {d.get('matricule_fiscal', '1234567A/A/M/000')}). Vous pouvez me joindre au "
                 f"{d.get('telephone') or '22 123 456'} ou à {user['email']}. J'ai reçu une notification de 180 000 DT.")
    return securite.apercu(texte, securite.identifiants_de(user))
