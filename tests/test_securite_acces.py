"""Security tests: account verification, role and centre isolation, messaging, confidentiality.

Run: .venv/Scripts/python -m pytest tests -q
"""
import base64
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import auth, securite, veille
from app.services.db import repo

SAMPLE = Path(__file__).resolve().parents[1] / "data" / "synthetic" / "samples" / "notification_sami.pdf"
CONSENTS = {"cgu": True, "donnees_personnelles": True, "analyse_ia": True}
_codes: dict[str, str] = {}


@pytest.fixture(scope="module")
def client():
    auth._deliver_otp = lambda email, code, intention: _codes.__setitem__(email, code) or "test"
    with TestClient(app) as c:
        yield c


def _login(c, email, intention):
    r = c.post("/api/auth/otp/demander", json={"email": email, "intention": intention})
    assert r.status_code == 200, r.text
    r = c.post("/api/auth/otp/verifier", json={"email": email, "code": _codes[email]})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def _inscrire(c, email, role, details, pieces=()):
    h = _login(c, email, "inscription")
    r = c.post("/api/auth/profil", headers=h, json={"role": role, "nom": "Test", "prenom": email.split("@")[0], "details": details,
                                                    "consentements": CONSENTS})
    assert r.status_code == 200, r.text
    for t in pieces:
        r = c.post("/api/comptes/pieces", headers=h, json={"type": t, "nom": f"{t}.pdf", "mime": "application/pdf",
                                                            "contenu": base64.b64encode(b"%PDF-1.4 test").decode()})
        assert r.status_code == 200, r.text
    assert c.post("/api/comptes/soumettre", headers=h).json()["statut"] == "en_attente"
    return h, r


def _valider(c, h_validateur, email):
    demande = next(d for d in c.get("/api/comptes/demandes", headers=h_validateur).json() if d["email"] == email)
    r = c.post(f"/api/comptes/demandes/{demande['id']}/decision", headers=h_validateur, json={"decision": "valide"})
    assert r.status_code == 200, r.text


@pytest.fixture(scope="module")
def comptes_(client):
    c = client
    admin = _login(c, "admin@test.tn", "admin")
    ent, _ = _inscrire(c, "sami@elamen.tn", "entreprise", {"raison_sociale": "Société Distribution El Amen SARL",
                       "matricule_fiscal": "1478523K/A/M/000", "forme_juridique": "SARL", "secteur": "Commerce de gros",
                       "gouvernorat": "Sfax", "effectif": "10 à 49", "regime": "Réel", "telephone": "22 123 456"}, ["rne", "cin"])
    # a pending account sees nothing
    assert c.get("/api/contribuable/analyses", headers=ent).status_code == 403
    _valider(c, admin, "sami@elamen.tn")
    chef, _ = _inscrire(c, "chef.sfax@finances.gov.tn", "chef_centre", {"centre": "Sfax 1", "matricule_agent": "10001"}, ["nomination"])
    _valider(c, admin, "chef.sfax@finances.gov.tn")
    agent, _ = _inscrire(c, "agent.sfax@finances.gov.tn", "contentieux", {"centre": "Sfax 1", "matricule_agent": "20002", "grade": "Inspecteur"}, ["carte_pro"])
    # a case officer is validated by the head of their own centre (hierarchy)
    _valider(c, chef, "agent.sfax@finances.gov.tn")
    agent_tunis, _ = _inscrire(c, "agent.tunis@finances.gov.tn", "contentieux", {"centre": "Tunis 1", "matricule_agent": "30003", "grade": "Inspecteur"}, ["carte_pro"])
    assert all(d["email"] != "agent.tunis@finances.gov.tn" for d in c.get("/api/comptes/demandes", headers=chef).json())
    _valider(c, admin, "agent.tunis@finances.gov.tn")
    ministre, _ = _inscrire(c, "ministre@finances.gov.tn", "ministre", {"cabinet": "Cabinet du ministre"}, ["nomination"])
    _valider(c, admin, "ministre@finances.gov.tn")
    return {"admin": admin, "ent": ent, "chef": chef, "agent": agent, "agent_tunis": agent_tunis, "ministre": ministre}


def test_isolation_des_espaces(client, comptes_):
    c, h = client, comptes_
    assert c.get("/api/admin/dossiers", headers=h["ent"]).status_code == 403
    assert c.get("/api/plateforme/utilisateurs", headers=h["ent"]).status_code == 403
    assert c.get("/api/plateforme/utilisateurs", headers=h["agent"]).status_code == 403
    assert c.get("/api/contribuable/analyses", headers=h["agent"]).status_code == 403
    assert c.get("/api/pilotage/national", headers=h["agent"]).status_code == 403
    # the minister sees aggregates, never a named file
    assert c.get("/api/admin/dossiers", headers=h["ministre"]).status_code == 403
    assert c.get("/api/admin/dossiers/D-SAMI", headers=h["ministre"]).status_code == 403
    nat = c.get("/api/pilotage/national", headers=h["ministre"]).json()
    assert "entreprise" not in str(nat["par_gouvernorat"])
    assert any(r.get("masque") for r in nat["par_gouvernorat"])   # k-anonymity


def test_perimetre_du_centre(client, comptes_):
    c, h = client, comptes_
    stock = c.get("/api/admin/dossiers?limit=500", headers=h["agent"]).json()
    assert stock["perimetre"] == "Sfax" and {d["gouvernorat"] for d in stock["dossiers"]} == {"Sfax"}
    assert c.get("/api/admin/dossiers/D-SAMI", headers=h["agent"]).status_code == 200
    assert c.get("/api/admin/dossiers/D-SAMI", headers=h["agent_tunis"]).status_code == 404


def test_affectation_et_validation_conciliation(client, comptes_):
    c, h = client, comptes_
    equipe = c.get("/api/pilotage/equipe", headers=h["chef"]).json()
    assert [a["nom"] for a in equipe] == ["agent.sfax Test"]
    assert c.post("/api/pilotage/affectations", headers=h["agent"], json={"dossier_id": "D-SAMI", "agent_id": equipe[0]["id"]}).status_code == 403
    assert c.post("/api/pilotage/affectations", headers=h["chef"], json={"dossier_id": "D-SAMI", "agent_id": equipe[0]["id"]}).status_code == 200
    mes = c.get("/api/admin/dossiers?mes=true", headers=h["agent"]).json()
    assert [d["id"] for d in mes["dossiers"]] == ["D-SAMI"]
    r = c.post("/api/admin/dossiers/D-SAMI/decision", headers=h["agent"], json={"decision": "validee"}).json()
    assert r["statut"] == "en_attente_validation"
    attente = c.get("/api/pilotage/conciliations-a-valider", headers=h["chef"]).json()
    assert len(attente) == 1
    assert c.post(f"/api/pilotage/conciliations/{attente[0]['id']}/decision", headers=h["chef"], json={"decision": "validee"}).json()["statut"] == "validee"


def test_messagerie_et_confidentialite(client, comptes_):
    c, h = client, comptes_
    r = c.post("/api/contribuable/analyser", headers=h["ent"], files={"fichier": ("notification_sami.pdf", SAMPLE.read_bytes(), "application/pdf")})
    assert r.status_code == 200, r.text
    analyse_id = r.json()["analyse_id"]
    # encrypted at rest
    stored = repo().analyses[analyse_id]
    assert "_chiffre" in stored["resultat"] and "El Amen" not in str(stored["resultat"])

    conv = c.post("/api/messagerie/conversations", headers=h["ent"], json={"analyse_id": analyse_id}).json()
    assert conv["dossier_id"] == "D-SAMI"
    assert c.post(f"/api/messagerie/conversations/{conv['id']}/messages", headers=h["ent"], json={"contenu": "Bonjour, voici nos factures."}).status_code == 200
    assert repo().messages[-1]["contenu"].startswith("enc:v1:")
    fil = c.get(f"/api/messagerie/conversations/{conv['id']}", headers=h["agent"])
    assert fil.status_code == 200 and fil.json()["messages"][0]["contenu"] == "Bonjour, voici nos factures."
    assert c.get(f"/api/messagerie/conversations/{conv['id']}", headers=h["agent_tunis"]).status_code == 404
    assert c.get(f"/api/messagerie/conversations/{conv['id']}", headers=h["ministre"]).status_code == 403
    assert c.post(f"/api/messagerie/conversations/{conv['id']}/messages", headers=h["agent"], json={"contenu": "Bien reçu."}).status_code == 200

    # the company sees who consulted its file (role and centre, not the person)
    acces = c.get("/api/confidentialite/acces", headers=h["ent"]).json()
    assert any(a["role"] == "contentieux" and a["centre"] == "Sfax 1" for a in acces)
    export = c.get("/api/confidentialite/export", headers=h["ent"])
    assert export.status_code == 200 and "Bien reçu." in export.text


def test_pseudonymisation():
    ids = {"Société Distribution El Amen SARL": "ENTREPRISE", "1478523K/A/M/000": "MATRICULE", "Sami Ben Salah": "PERSONNE"}
    with securite.contexte(ids):
        table: dict[str, str] = {}
        masque = securite.masquer("Sami Ben Salah, gérant de Société Distribution El Amen SARL (1478523K/A/M/000), "
                                  "tél. 22 123 456, sami@elamen.tn, doit 180 000 DT.", table)
    assert "El Amen" not in masque and "1478523K" not in masque and "22 123 456" not in masque and "sami@" not in masque
    assert "180 000 DT" in masque   # amounts are kept
    assert securite.restaurer(masque, table).startswith("Sami Ben Salah")


def test_consentement_ia_retire(client, comptes_):
    c, h = client, comptes_
    assert c.put("/api/confidentialite/consentements", headers=h["ent"], json={"analyse_ia": False}).status_code == 200
    from app.services import llm
    with securite.contexte({}, ia_autorisee=False):
        with pytest.raises(llm.LLMUnavailable):
            llm._parse("x", "test", securite.BaseModel, 10, False)


def test_veille_simulation_ne_modifie_pas_la_base(client, comptes_):
    avant = veille.base("cdpf")
    c = veille.simuler()
    out = client.post(f"/api/plateforme/veille/changements/{c['id']}/decision", headers=comptes_["admin"], json={"decision": "valide"}).json()
    assert out["publie"] is False and veille.base("cdpf") == avant
    assert client.post("/api/plateforme/veille/simuler", headers=comptes_["ent"]).status_code == 403


def test_droit_a_l_effacement(client, comptes_):
    c, h = client, comptes_
    assert c.post("/api/confidentialite/suppression", headers=h["ent"], json={"confirmation": "non"}).status_code == 422
    assert c.post("/api/confidentialite/suppression", headers=h["ent"], json={"confirmation": "SUPPRIMER"}).status_code == 200
    assert repo().get_user("sami@elamen.tn") is None
    assert not repo().conversations
