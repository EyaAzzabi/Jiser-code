"""Confidentiality of taxpayer data (loi organique 2004-63).

Three mechanisms:

* Encryption at rest: free text entered by users (messages, attachments, analyses, reply drafts,
  identity documents) is stored encrypted with Fernet (AES-128-CBC + HMAC-SHA256). The key never
  leaves the server.
* Pseudonymisation before any generative AI call: company names, tax IDs, people, e-mails, phone
  numbers and bank accounts are replaced by neutral tokens ([ENTREPRISE_1], [MATRICULE_1]...) before
  the text is sent to an external LLM, then put back in the answer. The disk cache only ever holds
  pseudonymised text.
* Consent: a user who withdraws consent to generative AI is served by the rules and the ML model only.

Per-request settings (identifiers to mask, AI consent) travel in context variables, set once by
the request's access-control dependency.
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import re
from contextlib import contextmanager
from contextvars import ContextVar

from cryptography.fernet import Fernet, InvalidToken
from pydantic import BaseModel

from ..config import DATA_KEY, N8N_SHARED_SECRET, SUPABASE_SERVICE_KEY

log = logging.getLogger("jiser.securite")

# ---- Encryption at rest ----------------------------------------------------------------------

PREFIX = "enc:v1:"


def _key() -> bytes:
    if DATA_KEY:
        return DATA_KEY.encode()
    secret = SUPABASE_SERVICE_KEY or N8N_SHARED_SECRET
    if secret:   # stable key derived from a server-only secret
        return base64.urlsafe_b64encode(hashlib.sha256(("jiser-data-key:" + secret).encode()).digest())
    log.warning("No JISER_DATA_KEY: using a temporary key (encrypted data will not survive a restart)")
    return Fernet.generate_key()


_fernet = Fernet(_key())


def chiffrer(texte: str | None) -> str | None:
    if texte is None or texte.startswith(PREFIX):
        return texte
    return PREFIX + _fernet.encrypt(texte.encode()).decode()


def dechiffrer(valeur: str | None) -> str | None:
    if not valeur or not valeur.startswith(PREFIX):
        return valeur   # data written before encryption was enabled
    try:
        return _fernet.decrypt(valeur[len(PREFIX):].encode()).decode()
    except InvalidToken:
        log.error("Undecryptable value (wrong JISER_DATA_KEY?)")
        return "[donnée chiffrée illisible]"


def chiffrer_json(obj) -> dict:
    return {"_chiffre": chiffrer(json.dumps(obj, ensure_ascii=False))}


def dechiffrer_json(obj):
    if isinstance(obj, dict) and "_chiffre" in obj:
        return json.loads(dechiffrer(obj["_chiffre"]) or "null")
    return obj


# ---- Pseudonymisation before the LLM ---------------------------------------------------------

_identifiants: ContextVar[dict[str, str]] = ContextVar("identifiants", default={})
_ia_autorisee: ContextVar[bool] = ContextVar("ia_autorisee", default=True)
_table: ContextVar[dict[str, str] | None] = ContextVar("table", default=None)

# patterns masked even when the identity is unknown
MOTIFS = [
    ("MATRICULE", re.compile(r"\b\d{7}[A-Z]/[A-Z]/[A-Z]/\d{3}\b")),
    ("EMAIL", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
    ("RIB", re.compile(r"\b\d{2}\s?\d{3}\s?\d{13}\s?\d{2}\b")),
    # 8-digit Tunisian numbers, but never amounts ("12 345 678 DT") or the tail of a longer number
    ("TELEPHONE", re.compile(r"(?<!\d)(?<!\d\s)(?:\+216\s?)?[2-9]\d(?:[\s.]?\d{3}){2}(?!\d)(?!\s?(?:DT|TND|MDT|dinars|%))")),
    ("CIN", re.compile(r"\bCIN\s*(?:n°|:)?\s*\d{8}\b", re.IGNORECASE)),
]


def identifiants_de(user: dict | None, extra: dict[str, str] | None = None) -> dict[str, str]:
    """Known identifiers of a user (and optionally of a case), as {category: value}."""
    ids: dict[str, str] = {}
    if user:
        d = user.get("details") or {}
        for cat, val in (("ENTREPRISE", d.get("raison_sociale")), ("MATRICULE", d.get("matricule_fiscal")),
                         ("PERSONNE", f"{user.get('prenom', '')} {user.get('nom', '')}".strip()),
                         ("PERSONNE", user.get("nom")), ("EMAIL", user.get("email")), ("TELEPHONE", d.get("telephone"))):
            if val and len(str(val)) >= 3:
                ids.setdefault(f"{cat}:{val}", cat)
    for val, cat in (extra or {}).items():
        if val and len(val) >= 3:
            ids.setdefault(f"{cat}:{val}", cat)
    return {k.split(":", 1)[1]: v for k, v in ids.items()}


@contextmanager
def contexte(identifiants: dict[str, str] | None = None, ia_autorisee: bool = True):
    """Mask these identifiers in every LLM call made inside the block."""
    t1 = _identifiants.set(identifiants or {})
    t2 = _ia_autorisee.set(ia_autorisee)
    try:
        yield
    finally:
        _identifiants.reset(t1)
        _ia_autorisee.reset(t2)


def definir(identifiants: dict[str, str], ia_autorisee: bool) -> None:
    """Set the context for the rest of the current request (called by the access dependency)."""
    _identifiants.set(identifiants)
    _ia_autorisee.set(ia_autorisee)


def ajouter_identifiants(extra: dict[str, str]) -> None:
    """Add case identifiers (e.g. the company of an administration file) to the current request."""
    _identifiants.set({**_identifiants.get(), **{k: v for k, v in extra.items() if k and len(k) >= 3}})


def ia_autorisee() -> bool:
    return _ia_autorisee.get()


def masquer(texte: str, table: dict[str, str]) -> str:
    """Replace identifiers by tokens; `table` (token -> original) is filled in place."""
    inverse = {v: k for k, v in table.items()}
    compteurs: dict[str, int] = {}
    for tok in table:
        cat = tok.strip("[]").rsplit("_", 1)[0]
        compteurs[cat] = max(compteurs.get(cat, 0), int(tok.strip("[]").rsplit("_", 1)[1]))

    def jeton(cat: str, original: str) -> str:
        if original in inverse:
            return inverse[original]
        compteurs[cat] = compteurs.get(cat, 0) + 1
        tok = f"[{cat}_{compteurs[cat]}]"
        table[tok] = original
        inverse[original] = tok
        return tok

    # longest known values first, case-insensitive
    for val, cat in sorted(_identifiants.get().items(), key=lambda kv: -len(kv[0])):
        texte = re.sub(re.escape(val), lambda m, c=cat: jeton(c, m.group(0)), texte, flags=re.IGNORECASE)
    for cat, rx in MOTIFS:
        texte = rx.sub(lambda m, c=cat: jeton(c, m.group(0)), texte)
    return texte


def restaurer(texte: str, table: dict[str, str]) -> str:
    for tok, original in table.items():
        texte = texte.replace(tok, original)
    return texte


def restaurer_modele(model: BaseModel, table: dict[str, str]) -> BaseModel:
    if not table:
        return model
    return type(model).model_validate_json(restaurer(model.model_dump_json(), {k: json.dumps(v)[1:-1] for k, v in table.items()}))


class RestaurateurFlux:
    """Puts identifiers back into a streamed answer, even when a token is split across chunks."""

    def __init__(self, table: dict[str, str]):
        self.table = table
        self.tampon = ""

    def pousser(self, morceau: str) -> str:
        self.tampon += morceau
        coupe = self.tampon.rfind("[")
        if coupe != -1 and "]" not in self.tampon[coupe:] and len(self.tampon) - coupe < 24:
            sortie, self.tampon = self.tampon[:coupe], self.tampon[coupe:]
        else:
            sortie, self.tampon = self.tampon, ""
        return restaurer(sortie, self.table)

    def vider(self) -> str:
        sortie, self.tampon = self.tampon, ""
        return restaurer(sortie, self.table)


def apercu(texte: str, identifiants: dict[str, str]) -> dict:
    """What the external AI would receive for this text (shown to the user on the privacy page)."""
    with contexte(identifiants):
        table: dict[str, str] = {}
        masque = masquer(texte, table)
    return {"original": texte, "envoye_a_l_ia": masque, "remplacements": [{"jeton": k, "categorie": k.strip("[]").rsplit("_", 1)[0]} for k in table]}


NEUTRE = {"ENTREPRISE": "votre entreprise", "MATRICULE": "votre matricule fiscal", "PERSONNE": "", "EMAIL": "votre adresse e-mail",
          "TELEPHONE": "votre numéro", "RIB": "votre compte bancaire", "CIN": "votre carte d'identité"}


def neutraliser(texte: str) -> str:
    """For outputs that cannot carry tokens (speech): identifiers become neutral words."""
    table: dict[str, str] = {}
    masque = masquer(texte, table)
    for tok in table:
        masque = masque.replace(tok, NEUTRE.get(tok.strip("[]").rsplit("_", 1)[0], ""))
    return re.sub(r"\s{2,}", " ", masque)
