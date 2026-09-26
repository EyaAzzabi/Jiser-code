"""Legal watch: keep the legal base (and its embeddings) up to date, automatically and under control.

Pipeline, run every week (internal scheduler, or n8n calling POST /api/n8n/veille), or on demand:

  1. collect     download each official source (CDPF PDF on jibaya.tn, codes on Jurisite)
  2. detect      fingerprint (SHA-256) of the source; unchanged -> stop there
  3. parse       split the new text article by article (same parsers as the initial import)
  4. compare     article by article with the published base: added / modified / repealed
  5. queue       every change waits for a legal expert in the platform admin ("À valider")
  6. publish     on approval: the base is updated, the previous text is archived as a version
                 (with its validity dates) and the embeddings of the changed articles are recomputed
  7. report      an e-mail summary is sent to the administrators (n8n)

Nothing reaches the AI before a human has approved it. A "simulation" change can be injected to
demonstrate the flow; approving it never modifies the base.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import logging
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests

from ..config import ADMIN_EMAILS, LEGAL_DIR, OPENAI_API_KEY, ROOT

log = logging.getLogger("jiser.veille")

VEILLE_DIR = LEGAL_DIR / "veille"
VERSIONS_DIR = LEGAL_DIR / "versions"
ETAT = VEILLE_DIR / "etat.json"
EN_ATTENTE = VEILLE_DIR / "en_attente.json"
EMB_FILE = LEGAL_DIR / "embeddings.npz"
EMB_META = LEGAL_DIR / "embeddings.json"
EMB_MODEL = "text-embedding-3-small"
PERIODE_S = 7 * 24 * 3600

SOURCES = [
    {"id": "cdpf", "code": "cdpf", "type": "pdf", "nom": "Code des droits et procédures fiscaux (édition officielle, jibaya.tn)",
     "url": "https://jibaya.tn/wp-content/uploads/2024/07/Code-des-droits-et-procedures-fiscaux-2024.pdf"},
    {"id": "ctva", "code": "ctva", "type": "jurisite", "nom": "Code de la TVA (Jurisite Tunisie)",
     "url": "https://www.jurisitetunisie.com/tunisie/codes/tva/"},
    {"id": "cirppis", "code": "cirppis", "type": "jurisite", "nom": "Code de l'IRPP et de l'IS (Jurisite Tunisie)",
     "url": "https://www.jurisitetunisie.com/tunisie/codes/cirppis/"},
]

_verrou = threading.Lock()
_en_cours: dict = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _lire(path: Path, defaut):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return defaut


def _ecrire(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(path)


def _empreinte(texte: str) -> str:
    return hashlib.sha256(texte.encode()).hexdigest()


def _script(nom: str):
    spec = importlib.util.spec_from_file_location(nom, ROOT / "scripts" / f"{nom}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def base(code: str) -> list[dict]:
    return _lire(LEGAL_DIR / f"{code}.json", [])


# ---- 1-3. collect, detect, parse ---------------------------------------------------------------

def _collecter(source: dict) -> tuple[str, list[dict]]:
    """Returns (fingerprint of the source, parsed articles)."""
    if source["type"] == "pdf":
        data = requests.get(source["url"], headers={"User-Agent": "Mozilla/5.0 (JISER veille juridique)"}, timeout=90).content
        empreinte = hashlib.sha256(data).hexdigest()
        return empreinte, _script("import_cdpf_officiel").parse_pdf(data)
    articles = _script("scrape_legal").scrape_code(source["code"])
    return _empreinte(json.dumps([a["text"] for a in articles], ensure_ascii=False)), articles


# ---- 4. compare ----------------------------------------------------------------------------------

def comparer(code: str, nouveaux: list[dict], source_id: str) -> list[dict]:
    actuels = {a["id"]: a for a in base(code)}
    # articles kept from a secondary source (marked "à vérifier") are not considered repealed
    officiels = {k: a for k, a in actuels.items() if "à vérifier" not in a.get("code_name", "")}
    neufs = {a["id"]: a for a in nouveaux}
    changements = []
    for aid, a in neufs.items():
        if aid not in actuels:
            changements.append({"type": "ajout", "article_id": aid, "article": a["article"], "ancien": None, "nouveau": a})
        elif " ".join(actuels[aid]["text"].split()) != " ".join(a["text"].split()):
            changements.append({"type": "modification", "article_id": aid, "article": a["article"], "ancien": actuels[aid], "nouveau": a})
    for aid, a in officiels.items():
        if aid not in neufs and nouveaux:
            changements.append({"type": "abrogation", "article_id": aid, "article": a["article"], "ancien": a, "nouveau": None})
    return [{"id": str(uuid.uuid4()), "source": source_id, "code": code, "detecte_le": _now(), "simulation": False, **c} for c in changements]


# ---- pipeline run --------------------------------------------------------------------------------

def etat() -> dict:
    e = _lire(ETAT, {"sources": {}, "executions": []})
    attente = _lire(EN_ATTENTE, [])
    meta = _lire(EMB_META, {})
    return {**e, "en_cours": dict(_en_cours), "en_attente": attente, "sources_config": SOURCES,
            "base": [{"code": s["code"], "nom": s["nom"], "articles": len(base(s["code"]))} for s in SOURCES],
            "embeddings": {"modele": meta.get("modele"), "articles": meta.get("n", 0), "calcule_le": meta.get("date"),
                           "disponible": EMB_FILE.exists()},
            "prochaine_execution": _prochaine(e)}


def _prochaine(e: dict) -> str | None:
    fin = next((x.get("fin") for x in e.get("executions", []) if x.get("fin")), None)
    if not fin:
        return None
    return datetime.fromtimestamp(datetime.fromisoformat(fin).timestamp() + PERIODE_S, timezone.utc).isoformat()


def lancer(declencheur: str, sources: list[str] | None = None, attendre: bool = False) -> dict:
    """Start a run in the background (a weekly run downloads and parses several hundred pages)."""
    if _en_cours:
        return {"ok": False, "message": "Une exécution est déjà en cours.", "en_cours": dict(_en_cours)}
    cibles = [s for s in SOURCES if not sources or s["id"] in sources]
    t = threading.Thread(target=_executer, args=(declencheur, cibles), daemon=True)
    t.start()
    if attendre:
        t.join()
    return {"ok": True, "message": f"Veille lancée sur {len(cibles)} source(s)."}


def _executer(declencheur: str, cibles: list[dict]) -> None:
    with _verrou:
        _en_cours.update({"debut": _now(), "declencheur": declencheur, "etape": "collecte", "source": None})
        e = _lire(ETAT, {"sources": {}, "executions": []})
        execution = {"debut": _now(), "declencheur": declencheur, "resultats": []}
        nouveaux_changements = []
        try:
            for s in cibles:
                _en_cours.update({"source": s["nom"], "etape": "collecte et analyse"})
                precedent = e["sources"].get(s["id"], {})
                try:
                    empreinte, articles = _collecter(s)
                except Exception as ex:   # one unreachable source must not stop the others
                    log.warning("veille %s: %s", s["id"], ex)
                    execution["resultats"].append({"source": s["id"], "statut": "erreur", "detail": str(ex)[:200]})
                    e["sources"][s["id"]] = {**precedent, "verifie_le": _now(), "statut": "erreur"}
                    continue
                if precedent.get("empreinte") == empreinte:
                    execution["resultats"].append({"source": s["id"], "statut": "inchange", "articles": len(articles)})
                    e["sources"][s["id"]] = {**precedent, "verifie_le": _now(), "statut": "inchange"}
                    continue
                _en_cours["etape"] = "comparaison article par article"
                changements = comparer(s["code"], articles, s["id"]) if articles else []
                nouveaux_changements += changements
                execution["resultats"].append({"source": s["id"], "statut": "modifie" if changements else "identique",
                                               "articles": len(articles), "changements": len(changements)})
                e["sources"][s["id"]] = {"empreinte": empreinte, "verifie_le": _now(), "modifie_le": _now() if changements else precedent.get("modifie_le"),
                                         "statut": "changements_a_valider" if changements else "a_jour", "articles": len(articles)}
            if nouveaux_changements:
                attente = _lire(EN_ATTENTE, [])
                deja = {(c["code"], c["article_id"], c["type"]) for c in attente}
                attente += [c for c in nouveaux_changements if (c["code"], c["article_id"], c["type"]) not in deja]
                _ecrire(EN_ATTENTE, attente)
        finally:
            execution.update({"fin": _now(), "changements": len(nouveaux_changements)})
            e["executions"] = [execution, *e.get("executions", [])][:20]
            _ecrire(ETAT, e)
            _en_cours.clear()
        _rapport(execution)


def _rapport(execution: dict) -> None:
    from .comptes import notifier
    lignes = "; ".join(f"{r['source']} : {r['statut']}" + (f" ({r.get('changements')} changement(s))" if r.get("changements") else "")
                       for r in execution["resultats"])
    for email in ADMIN_EMAILS:
        notifier(email, f"Veille juridique JISER : {execution['changements']} changement(s) détecté(s)", "Rapport de veille juridique",
                 f"Exécution {execution['declencheur']} terminée. {lignes}. "
                 + ("Des changements attendent votre validation dans l'espace administrateur." if execution["changements"] else
                    "La base juridique est à jour."))


# ---- 5-6. human validation, publication, versions --------------------------------------------------

def simuler() -> dict:
    """Inject a clearly labelled demo change (approving it never touches the base)."""
    a = next((x for x in base("cdpf") if x["id"] == "cdpf-art-44"), None) or base("cdpf")[0]
    nouveau = {**a, "text": a["text"].replace("quarante-cinq", "soixante").replace("45", "60")
               + " [SIMULATION : texte fictif utilisé pour démontrer le circuit de validation]"}
    c = {"id": str(uuid.uuid4()), "source": "cdpf", "code": "cdpf", "detecte_le": _now(), "simulation": True,
         "type": "modification", "article_id": a["id"], "article": a["article"], "ancien": a, "nouveau": nouveau}
    _ecrire(EN_ATTENTE, [c, *_lire(EN_ATTENTE, [])])
    return c


def decider(cid: str, decision: str, par: str, motif: str = "") -> dict:
    attente = _lire(EN_ATTENTE, [])
    c = next((x for x in attente if x["id"] == cid), None)
    if c is None:
        raise LookupError("Changement introuvable ou déjà traité.")
    _ecrire(EN_ATTENTE, [x for x in attente if x["id"] != cid])
    from .db import repo
    repo().journal_add({"action": "veille_juridique", "cible": f"{c['code'].upper()} art. {c['article']} ({c['type']})",
                        "recommandation": "Changement détecté par la veille" + (" (simulation)" if c["simulation"] else ""),
                        "mode": "humain", "decision_humaine": "validée" if decision == "valide" else f"rejetée {motif}".strip(), "utilisateur": par})
    if decision != "valide":
        return {"ok": True, "publie": False, "message": "Changement rejeté : la base reste inchangée."}
    if c["simulation"]:
        return {"ok": True, "publie": False, "message": "Simulation validée : circuit démontré, aucune modification publiée."}
    _publier(c, par)
    return {"ok": True, "publie": True, "message": f"Article {c['article']} publié ; version précédente archivée, embeddings mis à jour."}


def _publier(c: dict, par: str) -> None:
    path = LEGAL_DIR / f"{c['code']}.json"
    articles = base(c["code"])
    maintenant = _now()
    if c["ancien"]:
        versions = _lire(VERSIONS_DIR / f"{c['code']}.json", {})
        hist = versions.setdefault(c["article_id"], [])
        hist.append({"version": len(hist) + 1, "texte": c["ancien"]["text"], "source_url": c["ancien"].get("source_url"),
                     "en_vigueur_du": c["ancien"].get("en_vigueur_depuis"), "jusqu_au": maintenant, "empreinte": _empreinte(c["ancien"]["text"])})
        _ecrire(VERSIONS_DIR / f"{c['code']}.json", versions)
    articles = [a for a in articles if a["id"] != c["article_id"]]
    if c["nouveau"]:
        articles.append({**c["nouveau"], "en_vigueur_depuis": maintenant[:10], "valide_par": par,
                         "version": len(_lire(VERSIONS_DIR / f"{c['code']}.json", {}).get(c["article_id"], [])) + 1})
    _ecrire(path, sorted(articles, key=lambda a: (_num(a["article"]), a["article"])))
    calculer_embeddings([c["article_id"]] if c["nouveau"] else [])
    from .legal_rag import get_index
    get_index.cache_clear()


def _num(article: str) -> int:
    try:
        return int(article.split()[0])
    except ValueError:
        return 10_000


def historique(article_id: str) -> dict:
    code = article_id.split("-art-")[0]
    actuel = next((a for a in base(code) if a["id"] == article_id), None)
    return {"actuel": actuel, "versions": _lire(VERSIONS_DIR / f"{code}.json", {}).get(article_id, [])}


# ---- embeddings (vector search) ----------------------------------------------------------------

def _texte_embedding(a: dict) -> str:
    return f"{a.get('code_name', a['code'])} — article {a['article']}. {a.get('heading', '')} {a['text']}"[:8000]


def calculer_embeddings(seulement: list[str] | None = None) -> dict:
    """(Re)compute article embeddings; `seulement` = only these article ids (after a publication)."""
    import numpy as np
    if not OPENAI_API_KEY:
        return {"ok": False, "message": "Embeddings indisponibles : clé OpenAI absente."}
    import openai
    client = openai.OpenAI(api_key=OPENAI_API_KEY, max_retries=2, timeout=120)
    tous = [a for s in SOURCES for a in base(s["code"])]
    ids, vecteurs = [], None
    if EMB_FILE.exists() and seulement is not None:
        z = np.load(EMB_FILE, allow_pickle=False)
        anciens = dict(zip(z["ids"].tolist(), z["vecteurs"]))
    else:
        anciens = {}
    a_calculer = [a for a in tous if a["id"] not in anciens or (seulement and a["id"] in seulement)]
    nouveaux = {}
    for i in range(0, len(a_calculer), 64):
        lot = a_calculer[i:i + 64]
        rep = client.embeddings.create(model=EMB_MODEL, input=[_texte_embedding(a) for a in lot])
        nouveaux.update({a["id"]: d.embedding for a, d in zip(lot, rep.data)})
    for a in tous:
        v = nouveaux.get(a["id"], anciens.get(a["id"]))
        if v is not None:
            ids.append(a["id"])
            vecteurs = [*(vecteurs or []), v]
    mat = np.asarray(vecteurs, dtype=np.float32)
    mat /= np.linalg.norm(mat, axis=1, keepdims=True) + 1e-9
    np.savez_compressed(EMB_FILE, ids=np.asarray(ids), vecteurs=mat)
    _ecrire(EMB_META, {"modele": EMB_MODEL, "n": len(ids), "date": _now(), "dimension": int(mat.shape[1])})
    from .legal_rag import get_index
    get_index.cache_clear()
    return {"ok": True, "message": f"{len(nouveaux)} embedding(s) calculé(s), {len(ids)} articles indexés."}


# ---- scheduler ---------------------------------------------------------------------------------

def demarrer_planificateur() -> None:
    """Weekly run inside the API (n8n can trigger the same pipeline through /api/n8n/veille)."""
    def boucle():
        time.sleep(120)
        while True:
            e = _lire(ETAT, {"executions": []})
            derniere = next((x.get("fin") for x in e.get("executions", []) if x.get("fin")), None)
            if derniere is None or time.time() - datetime.fromisoformat(derniere).timestamp() > PERIODE_S:
                lancer("planifiee")
            time.sleep(6 * 3600)
    threading.Thread(target=boucle, daemon=True).start()
