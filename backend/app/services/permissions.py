"""Roles, rights and data scope, following the hierarchy of the Tunisian tax administration.

Ministère des Finances -> Direction générale des impôts -> 27 centres régionaux de contrôle des impôts
(CRCI, categories A and B) -> case officers. JISER keeps three administration levels:

* ministre       national, strategic: aggregated statistics only, never a named taxpayer (tax secrecy)
* chef_centre    one CRCI: its stock, assigns files, approves large settlements and its officers' accounts
* contentieux    case officer in one CRCI: works on files, talks with taxpayers, proposes settlements

Every protected route declares the permission it needs; the role always comes from the database,
never from the browser.
"""
from __future__ import annotations

ROLE_LABELS = {
    "entreprise": "Chef d'entreprise",
    "ministre": "Ministre des Finances",
    "chef_centre": "Chef de centre régional (CRCI)",
    "contentieux": "Chargé(e) du contentieux",
    "admin": "Administrateur plateforme",
    # legacy profiles, kept readable for old accounts
    "conseil": "Conseil fiscal", "verificateur": "Vérificateur",
}

ADMINISTRATION = {"ministre", "chef_centre", "contentieux"}
SELF_SERVICE_ROLES = {"entreprise", *ADMINISTRATION}     # "admin" is never self-service

_AGENT = {"stats:centre", "dossiers:lire", "dossier:avis", "conciliation:proposer", "controle_qualite", "copilote",
          "messagerie:administration", "favoris"}
PERMISSIONS: dict[str, set[str]] = {
    "entreprise": {"analyses:propres", "messagerie:entreprise", "donnees:propres", "copilote", "favoris"},
    "contentieux": _AGENT,
    "chef_centre": _AGENT | {"dossiers:affecter", "conciliation:valider", "comptes:valider_agents", "equipe:lire"},
    "ministre": {"stats:national", "copilote", "favoris"},
    "admin": {"plateforme", "comptes:valider", "veille:gerer", "journal:lire"},
}

# 27 CRCI (ministère des Finances): category A (16) and B (11)
CENTRES_A = ["Tunis 1", "Tunis 2", "Tunis 3", "Ariana", "Ben Arous", "Manouba", "Bizerte", "Nabeul", "Sousse",
             "Monastir", "Sfax 1", "Sfax 2", "Kairouan", "Médenine", "Mahdia", "Gabès"]
CENTRES_B = ["Gafsa", "Le Kef", "Béja", "Jendouba", "Kasserine", "Sidi Bouzid", "Zaghouan", "Siliana", "Kébili",
             "Tozeur", "Tataouine"]
CENTRES = CENTRES_A + CENTRES_B


def gouvernorat_du_centre(centre: str | None) -> str | None:
    """Files are located by governorate; Tunis 1-3 and Sfax 1-2 share their governorate."""
    if not centre:
        return None
    return centre.rsplit(" ", 1)[0] if centre.split(" ")[-1].isdigit() else centre


def a_permission(role: str | None, permission: str) -> bool:
    return permission in PERMISSIONS.get(role or "", set())


def centre_de(user: dict | None) -> str | None:
    return (user or {}).get("details", {}).get("centre") or None


def perimetre(user: dict | None) -> str | None:
    """Governorate a user is limited to (None = national, for legacy accounts without a centre)."""
    return gouvernorat_du_centre(centre_de(user))


def peut_voir_dossier(user: dict | None, role: str | None, gouvernorat_dossier: str) -> bool:
    if role not in {"contentieux", "chef_centre"}:
        return False
    zone = perimetre(user)
    return zone is None or zone == gouvernorat_dossier


def validateur_de(role: str) -> str:
    """Who approves a new account: the hierarchy for case officers, the platform admin otherwise."""
    return "chef_centre" if role == "contentieux" else "admin"
