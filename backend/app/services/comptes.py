"""Account verification before access: automatic pre-checks, then a human decision within 24 hours.

Every new account starts "en_attente". JISER runs automatic checks (tax ID format, identity
documents, consistency between the documents and the form, official e-mail domain, duplicates)
and puts the result in front of the right validator:

* case officer (chargé du contentieux)  -> the head of their centre (hierarchy), or the platform admin
* company, head of centre, minister     -> the platform administrator

The decision (validated / refused with a reason) is e-mailed through n8n and written to the journal.
Identity documents are read locally (PDF text); images are never sent to an external AI.
"""
from __future__ import annotations

import base64
import io
import logging
import re
import unicodedata
from datetime import datetime, timezone

from ..config import APP_URL, N8N_NOTIF_WEBHOOK_URL, OFFICIAL_EMAIL_DOMAINS
from .db import repo
from .permissions import ADMINISTRATION, ROLE_LABELS, centre_de, validateur_de

log = logging.getLogger("jiser.comptes")

DELAI_VERIFICATION_H = 24
MATRICULE_RE = re.compile(r"^\d{7}[A-Z]/[A-Z]/[A-Z]/\d{3}$")
WEBMAILS = {"gmail.com", "yahoo.fr", "yahoo.com", "hotmail.com", "hotmail.fr", "outlook.com", "outlook.fr", "live.fr", "icloud.com"}
PIECES_REQUISES = {
    "entreprise": {"rne": "Extrait du registre national des entreprises (RNE)", "cin": "Carte d'identité du gérant"},
    "contentieux": {"carte_pro": "Carte professionnelle ou attestation de fonction"},
    "chef_centre": {"nomination": "Décision de nomination"},
    "ministre": {"nomination": "Décret de nomination"},
}
TAILLE_MAX = 5 * 1024 * 1024
TYPES_ACCEPTES = {"application/pdf", "image/jpeg", "image/png", "image/webp"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _norm(t: str) -> set[str]:
    t = unicodedata.normalize("NFKD", t.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return {w for w in re.findall(r"[a-z0-9]{3,}", t) if w not in {"sarl", "suarl", "societe", "ste", "les", "des"}}


def _texte_piece(piece: dict) -> str:
    if piece.get("mime") != "application/pdf":
        return ""
    try:
        from pypdf import PdfReader
        data = base64.b64decode(piece["contenu"])
        return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(data)).pages[:5])
    except Exception:
        return ""


def controle(nom: str, statut: str, detail: str) -> dict:
    return {"controle": nom, "statut": statut, "detail": detail}


def preverifier(user: dict) -> dict:
    """Automatic checks shown to the validator. statut: ok | alerte | echec."""
    role, d, email = user["role"], user.get("details") or {}, user["email"]
    domaine = email.split("@")[1]
    pieces = [repo().piece_get(p["id"]) for p in repo().pieces_for(user["id"])]
    types = {p["type"] for p in pieces if p}
    checks = []

    for code, label in PIECES_REQUISES.get(role, {}).items():
        checks.append(controle(f"Pièce : {label}", "ok" if code in types else "echec",
                               "Déposée" if code in types else "Manquante"))

    if role == "entreprise":
        mf = str(d.get("matricule_fiscal", ""))
        checks.append(controle("Format du matricule fiscal", "ok" if MATRICULE_RE.match(mf) else "echec", mf or "absent"))
        doublon = any(u["id"] != user["id"] and (u.get("details") or {}).get("matricule_fiscal") == mf and u.get("statut", "actif") == "actif"
                      for u in repo().list_users())
        checks.append(controle("Matricule non déjà utilisé", "alerte" if doublon else "ok",
                               "Un compte actif utilise déjà ce matricule" if doublon else "Aucun doublon"))
        rne = next((p for p in pieces if p and p["type"] == "rne"), None)
        if rne:
            texte = _texte_piece(rne)
            if not texte:
                checks.append(controle("Lecture de l'extrait RNE", "alerte", "Image : à contrôler visuellement (non envoyée à une IA externe)"))
            else:
                mots = _norm(str(d.get("raison_sociale", "")))
                trouve = mots and len(mots & _norm(texte)) / len(mots) >= 0.6
                checks.append(controle("Raison sociale présente sur l'extrait RNE", "ok" if trouve else "alerte",
                                       "Concordance trouvée" if trouve else "Non retrouvée dans le document"))
                mf_doc = mf.split("/")[0] in texte.replace(" ", "")
                checks.append(controle("Matricule présent sur l'extrait RNE", "ok" if mf_doc else "alerte",
                                       "Concordance trouvée" if mf_doc else "Non retrouvé dans le document"))
        checks.append(controle("Adresse e-mail professionnelle", "alerte" if domaine in WEBMAILS else "ok",
                               f"Messagerie grand public ({domaine})" if domaine in WEBMAILS else domaine))
    else:
        officiel = any(domaine == od or domaine.endswith("." + od) for od in OFFICIAL_EMAIL_DOMAINS)
        checks.append(controle("Adresse e-mail officielle de l'administration", "ok" if officiel else "alerte",
                               domaine if officiel else f"{domaine} n'est pas un domaine officiel ({', '.join(sorted(OFFICIAL_EMAIL_DOMAINS))})"))
        if role in {"contentieux", "chef_centre"}:
            checks.append(controle("Centre de rattachement", "ok" if centre_de(user) else "echec", centre_de(user) or "absent"))
        if role == "contentieux":
            mat = str(d.get("matricule_agent", ""))
            checks.append(controle("Matricule d'agent", "ok" if re.fullmatch(r"\d{4,10}", mat) else "alerte", mat or "absent"))
        if role == "ministre":
            deja = any(u["id"] != user["id"] and u["role"] == "ministre" and u.get("statut", "actif") == "actif" for u in repo().list_users())
            checks.append(controle("Un seul compte ministre actif", "alerte" if deja else "ok",
                                   "Un compte ministre est déjà actif" if deja else "Aucun autre compte"))

    ok = sum(c["statut"] == "ok" for c in checks)
    return {"controles": checks, "score": round(100 * ok / len(checks)) if checks else 0,
            "bloquant": any(c["statut"] == "echec" for c in checks), "date": _now().isoformat()}


# ---- notifications (n8n generic webhook) -----------------------------------------------------

def notifier(email: str, sujet: str, titre: str, message: str, lien: str | None = None) -> bool:
    if not N8N_NOTIF_WEBHOOK_URL:
        log.info("N8N_NOTIF_WEBHOOK_URL not set: e-mail « %s » to %s not sent", sujet, email)
        return False
    from .auth import _post_n8n
    return _post_n8n(N8N_NOTIF_WEBHOOK_URL, {"email": email, "sujet": sujet, "titre": titre, "message": message,
                                             "lien": lien or APP_URL})


# ---- workflow ----------------------------------------------------------------------------------

def soumettre(user: dict) -> dict:
    """Called when the sign-up form is complete: run the checks, notify the applicant."""
    verif = {**(user.get("verification") or {}), "pre_verification": preverifier(user), "soumis_le": _now().isoformat(),
             "validateur": validateur_de(user["role"])}
    user = repo().update_user(user["id"], statut="en_attente", verification=verif) or {**user, "statut": "en_attente", "verification": verif}
    notifier(user["email"], "Votre demande d'accès JISER est bien reçue", f"Bonjour {user['prenom']},",
             f"Votre demande d'accès en tant que {ROLE_LABELS.get(user['role'], user['role'])} a bien été reçue. "
             f"Nos équipes vérifient vos informations et vos justificatifs sous {DELAI_VERIFICATION_H} heures. "
             "Vous recevrez un e-mail dès que votre espace sera activé.")
    repo().journal_add({"action": "demande_acces", "cible": f"{user['prenom']} {user['nom']} ({user['role']})",
                        "recommandation": f"Pré-vérification automatique : {verif['pre_verification']['score']} %", "mode": "regles",
                        "utilisateur": user["email"]})
    return user


def peut_decider(validateur: dict, role_validateur: str, demandeur: dict) -> bool:
    if role_validateur == "admin":
        return True
    if role_validateur == "chef_centre" and demandeur["role"] == "contentieux":
        return bool(centre_de(validateur)) and centre_de(validateur) == centre_de(demandeur)
    return False


def demandes(validateur: dict | None, role_validateur: str) -> list[dict]:
    out = []
    for u in repo().list_users():
        if u.get("statut") != "en_attente":
            continue
        full = repo().get_user(u["email"]) or u
        if not peut_decider(validateur or {}, role_validateur, full):
            continue
        soumis = (full.get("verification") or {}).get("soumis_le") or full.get("cree_le")
        heures = (_now() - datetime.fromisoformat(str(soumis).replace("Z", "+00:00"))).total_seconds() / 3600 if soumis else 0
        out.append({"id": full["id"], "email": full["email"], "nom": full["nom"], "prenom": full["prenom"], "role": full["role"],
                    "role_label": ROLE_LABELS.get(full["role"], full["role"]), "details": full.get("details") or {},
                    "verification": full.get("verification") or {}, "attente_heures": round(heures, 1),
                    "pieces": repo().pieces_for(full["id"]), "cree_le": full.get("cree_le")})
    return sorted(out, key=lambda x: -x["attente_heures"])


def decider(validateur_email: str, validateur: dict | None, role_validateur: str, user_id: str, decision: str, motif: str) -> dict:
    demandeur = repo().get_user_by_id(user_id)
    if not demandeur or demandeur.get("statut") != "en_attente":
        raise ValueError("Demande introuvable ou déjà traitée.")
    if not peut_decider(validateur or {}, role_validateur, demandeur):
        raise PermissionError("Vous n'êtes pas habilité à valider ce compte.")
    if decision == "refuse" and not motif.strip():
        raise ValueError("Indiquez le motif du refus : il est communiqué au demandeur.")
    verif = {**(demandeur.get("verification") or {}), "decision": decision, "motif": motif.strip(), "decide_par": validateur_email,
             "decide_le": _now().isoformat()}
    statut = "actif" if decision == "valide" else "refuse"
    repo().update_user(user_id, statut=statut, verification=verif)
    repo().journal_add({"action": "decision_acces", "cible": f"{demandeur['prenom']} {demandeur['nom']} ({demandeur['role']})",
                        "recommandation": f"Pré-vérification {verif.get('pre_verification', {}).get('score', '?')} %", "mode": "humain",
                        "decision_humaine": "validée" if statut == "actif" else f"refusée : {motif.strip()}", "utilisateur": validateur_email})
    if statut == "actif":
        from .auth import send_welcome
        send_welcome({**demandeur, "statut": "actif"})
        notifier(demandeur["email"], "Votre espace JISER est activé", f"Bonjour {demandeur['prenom']},",
                 "Vos informations ont été vérifiées : votre espace est maintenant accessible. Connectez-vous avec votre adresse e-mail.")
    else:
        notifier(demandeur["email"], "Votre demande d'accès JISER", f"Bonjour {demandeur['prenom']},",
                 f"Après vérification, votre demande d'accès n'a pas pu être acceptée. Motif : {motif.strip()}. "
                 "Vous pouvez répondre à cet e-mail pour compléter votre dossier.")
    return {"ok": True, "statut": statut}


def est_administration(role: str | None) -> bool:
    return role in ADMINISTRATION
