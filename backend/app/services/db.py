"""Persistence layer: Supabase (PostgreSQL) when configured, in-memory otherwise.

Both backends expose the same methods, so the rest of the app never checks which one runs.
The Supabase client uses the service_role key and must only run server-side.

Encryption at rest happens here, so no code path can store taxpayer text in clear: analysis
results, reply drafts, messages, attachments and identity documents are encrypted on write and
decrypted on read (see securite.py).
"""
from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache

from ..config import SUPABASE_SERVICE_KEY, SUPABASE_URL
from .securite import chiffrer, chiffrer_json, dechiffrer, dechiffrer_json

log = logging.getLogger("jiser.db")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(d: datetime | date) -> str:
    return d.isoformat()


# ---- encryption of sensitive columns --------------------------------------------------------

def _enc_analysis(row: dict) -> dict:
    return {**row, "resultat": chiffrer_json(row["resultat"])} if "resultat" in row else row


def _dec_analysis(row: dict | None) -> dict | None:
    return {**row, "resultat": dechiffrer_json(row["resultat"])} if row and "resultat" in row else row


def _enc_fields(row: dict, *fields: str) -> dict:
    return {**row, **{f: chiffrer(row[f]) for f in fields if row.get(f) is not None}}


def _dec_fields(row: dict | None, *fields: str) -> dict | None:
    return {**row, **{f: dechiffrer(row[f]) for f in fields if row.get(f) is not None}} if row else row


def _sans(row: dict, *fields: str) -> dict:
    return {k: v for k, v in row.items() if k not in fields}


class MemoryRepo:
    kind = "memoire"

    def __init__(self) -> None:
        self.users: dict[str, dict] = {}
        self.otps: dict[str, dict] = {}
        self.sessions: dict[str, dict] = {}
        self.analyses: dict[str, dict] = {}
        self.reponses: list[dict] = []
        self.journal: list[dict] = []
        self.favoris: dict[str, dict] = {}
        self.pieces: dict[str, dict] = {}
        self.affectations: dict[str, dict] = {}
        self.conciliations: dict[str, dict] = {}
        self.conversations: dict[str, dict] = {}
        self.messages: list[dict] = []
        self.acces: list[dict] = []

    # users
    def get_user(self, email: str) -> dict | None:
        return self.users.get(email)

    def get_user_by_id(self, user_id: str) -> dict | None:
        return next((u for u in self.users.values() if u["id"] == user_id), None)

    def create_user(self, row: dict) -> dict:
        row = {"id": str(uuid.uuid4()), "cree_le": _iso(_now()), "actif": True, "statut": "actif", "verification": {}, **row}
        self.users[row["email"]] = row
        return row

    def update_user(self, user_id: str, **fields) -> dict | None:
        u = self.get_user_by_id(user_id)
        if u:
            u.update(fields)
        return u

    def delete_user(self, user_id: str) -> None:
        u = self.get_user_by_id(user_id)
        if not u:
            return
        del self.users[u["email"]]
        self.analyses = {k: a for k, a in self.analyses.items() if a["utilisateur_id"] != user_id}
        self.reponses = [r for r in self.reponses if r["utilisateur_id"] != user_id]
        self.favoris = {k: f for k, f in self.favoris.items() if f["utilisateur_id"] != user_id}
        self.pieces = {k: p for k, p in self.pieces.items() if p["utilisateur_id"] != user_id}
        convs = {k for k, c in self.conversations.items() if c["entreprise_id"] == user_id}
        self.conversations = {k: c for k, c in self.conversations.items() if k not in convs}
        self.messages = [m for m in self.messages if m["conversation_id"] not in convs]
        self.sessions = {k: s for k, s in self.sessions.items() if s.get("utilisateur_id") != user_id}

    def touch_login(self, email: str) -> None:
        if email in self.users:
            self.users[email]["derniere_connexion"] = _iso(_now())

    def list_users(self) -> list[dict]:
        return sorted(self.users.values(), key=lambda u: u["cree_le"], reverse=True)

    # otp
    def otp_get(self, email: str) -> dict | None:
        return self.otps.get(email)

    def otp_set(self, email: str, row: dict) -> None:
        self.otps[email] = {"email": email, **row}

    def otp_update(self, email: str, **fields) -> None:
        if email in self.otps:
            self.otps[email].update(fields)

    def otp_delete(self, email: str) -> None:
        self.otps.pop(email, None)

    # sessions
    def session_create(self, row: dict) -> None:
        self.sessions[row["token_hash"]] = row

    def session_get(self, token_hash: str) -> dict | None:
        return self.sessions.get(token_hash)

    def session_update(self, token_hash: str, **fields) -> None:
        if token_hash in self.sessions:
            self.sessions[token_hash].update(fields)

    def session_delete(self, token_hash: str) -> None:
        self.sessions.pop(token_hash, None)

    # analyses & replies (encrypted)
    def analysis_add(self, row: dict) -> dict:
        row = {"id": str(uuid.uuid4()), "cree_le": _iso(_now()), **row}
        self.analyses[row["id"]] = _enc_analysis(row)
        return row

    def analyses_for(self, user_id: str) -> list[dict]:
        rows = sorted((a for a in self.analyses.values() if a["utilisateur_id"] == user_id), key=lambda a: a["cree_le"], reverse=True)
        return [_dec_analysis(a) for a in rows]

    def analysis_get(self, analysis_id: str, user_id: str) -> dict | None:
        a = self.analyses.get(analysis_id)
        return _dec_analysis(a) if a and a["utilisateur_id"] == user_id else None

    def reponse_add(self, row: dict) -> dict:
        row = {"id": str(uuid.uuid4()), "cree_le": _iso(_now()), **row}
        self.reponses.append(_enc_fields(row, "lettre"))
        return row

    def reponses_for(self, user_id: str) -> list[dict]:
        rows = sorted((r for r in self.reponses if r["utilisateur_id"] == user_id), key=lambda r: r["cree_le"], reverse=True)
        return [_dec_fields(r, "lettre") for r in rows]

    def upcoming_deadlines(self, days: int) -> list[dict]:
        today, limit = date.today(), date.today() + timedelta(days=days)
        by_id = {u["id"]: u for u in self.users.values()}
        out = []
        for a in self.analyses.values():
            d = date.fromisoformat(str(a["date_limite"]))
            if today <= d <= limit and a["utilisateur_id"] in by_id:
                u = by_id[a["utilisateur_id"]]
                out.append({**{k: a[k] for k in ("id", "reference", "entreprise", "montant_total", "date_limite")},
                            "email": u["email"], "prenom": u["prenom"], "jours_restants": (d - today).days})
        return out

    # journal
    def journal_add(self, row: dict) -> None:
        self.journal.insert(0, {"horodatage": _iso(_now()), "decision_humaine": "en attente", **row})
        del self.journal[1000:]

    def journal_list(self, limit: int) -> list[dict]:
        return self.journal[:limit]

    def journal_has(self, action: str, cible: str) -> bool:
        return any(j["action"] == action and j["cible"] == cible for j in self.journal)

    # favourites
    def favoris_list(self, user_id: str) -> list[dict]:
        return sorted((f for f in self.favoris.values() if f["utilisateur_id"] == user_id), key=lambda f: f["cree_le"], reverse=True)

    def favoris_add(self, row: dict) -> dict:
        for f in self.favoris.values():
            if (f["utilisateur_id"], f["type"], f["ref"]) == (row["utilisateur_id"], row["type"], row["ref"]):
                return f
        row = {"id": str(uuid.uuid4()), "cree_le": _iso(_now()), **row}
        self.favoris[row["id"]] = row
        return row

    def favoris_delete(self, fav_id: str, user_id: str) -> None:
        if self.favoris.get(fav_id, {}).get("utilisateur_id") == user_id:
            del self.favoris[fav_id]

    # dossiers
    def dossiers_all(self) -> list[dict] | None:
        return None   # None = use the local synthetic file

    # identity documents (encrypted)
    def piece_add(self, row: dict) -> dict:
        row = {"id": str(uuid.uuid4()), "cree_le": _iso(_now()), **row}
        self.pieces[row["id"]] = _enc_fields(row, "contenu")
        return _sans(row, "contenu")

    def pieces_for(self, user_id: str) -> list[dict]:
        return [_sans(p, "contenu") for p in self.pieces.values() if p["utilisateur_id"] == user_id]

    def piece_get(self, piece_id: str) -> dict | None:
        return _dec_fields(self.pieces.get(piece_id), "contenu")

    # file assignments and settlement approvals
    def affectation_set(self, row: dict) -> None:
        self.affectations[row["dossier_id"]] = {"cree_le": _iso(_now()), **row}

    def affectations_all(self) -> dict[str, dict]:
        return dict(self.affectations)

    def conciliation_add(self, row: dict) -> dict:
        row = {"id": str(uuid.uuid4()), "cree_le": _iso(_now()), "statut": "en_attente", **row}
        self.conciliations[row["id"]] = row
        return row

    def conciliations_list(self) -> list[dict]:
        return sorted(self.conciliations.values(), key=lambda c: c["cree_le"], reverse=True)

    def conciliation_update(self, cid: str, **fields) -> dict | None:
        c = self.conciliations.get(cid)
        if c:
            c.update(fields)
        return c

    # messaging (contents encrypted)
    def conversation_add(self, row: dict) -> dict:
        row = {"id": str(uuid.uuid4()), "cree_le": _iso(_now()), "dernier_message_le": _iso(_now()), **row}
        self.conversations[row["id"]] = row
        return row

    def conversation_get(self, cid: str) -> dict | None:
        return self.conversations.get(cid)

    def conversation_par_reference(self, reference: str, entreprise_id: str) -> dict | None:
        return next((c for c in self.conversations.values() if c["reference"] == reference and c["entreprise_id"] == entreprise_id), None)

    def conversations_all(self) -> list[dict]:
        return sorted(self.conversations.values(), key=lambda c: c["dernier_message_le"], reverse=True)

    def conversation_update(self, cid: str, **fields) -> None:
        if cid in self.conversations:
            self.conversations[cid].update(fields)

    def message_add(self, row: dict) -> dict:
        row = {"id": str(uuid.uuid4()), "cree_le": _iso(_now()), "lu_par": [row.get("auteur_id")], **row}
        self.messages.append(_enc_fields(row, "contenu", "piece_contenu"))
        return _sans(row, "piece_contenu") | {"a_piece": bool(row.get("piece_nom"))}

    def messages_for(self, cid: str) -> list[dict]:
        return [_sans(_dec_fields(m, "contenu"), "piece_contenu") | {"a_piece": bool(m.get("piece_nom"))}
                for m in self.messages if m["conversation_id"] == cid]

    def message_piece(self, mid: str) -> dict | None:
        return _dec_fields(next((m for m in self.messages if m["id"] == mid), None), "piece_contenu")

    def messages_marquer_lus(self, cid: str, user_id: str) -> None:
        for m in self.messages:
            if m["conversation_id"] == cid and user_id not in m["lu_par"]:
                m["lu_par"] = [*m["lu_par"], user_id]

    # access log shown to the taxpayer ("who consulted my file")
    def acces_add(self, row: dict) -> None:
        self.acces.insert(0, {"horodatage": _iso(_now()), **row})
        del self.acces[5000:]

    def acces_pour(self, references: list[str]) -> list[dict]:
        return [a for a in self.acces if a["reference"] in references][:200]


class SupabaseRepo:
    kind = "supabase"

    def __init__(self) -> None:
        from supabase import create_client
        self.sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    def _t(self, name: str):
        return self.sb.table(name)

    @staticmethod
    def _one(res) -> dict | None:
        return res.data[0] if res.data else None

    # users
    def get_user(self, email: str) -> dict | None:
        return self._one(self._t("utilisateurs").select("*").eq("email", email).limit(1).execute())

    def get_user_by_id(self, user_id: str) -> dict | None:
        return self._one(self._t("utilisateurs").select("*").eq("id", user_id).limit(1).execute())

    def create_user(self, row: dict) -> dict:
        return self._t("utilisateurs").insert(row).execute().data[0]

    def update_user(self, user_id: str, **fields) -> dict | None:
        return self._one(self._t("utilisateurs").update(fields).eq("id", user_id).execute())

    def delete_user(self, user_id: str) -> None:
        # analyses, replies, favourites, sessions, documents and conversations cascade (see schema)
        self._t("utilisateurs").delete().eq("id", user_id).execute()

    def touch_login(self, email: str) -> None:
        self._t("utilisateurs").update({"derniere_connexion": _iso(_now())}).eq("email", email).execute()

    def list_users(self) -> list[dict]:
        return self._t("utilisateurs").select("id,email,role,nom,prenom,fonction,details,cree_le,derniere_connexion,actif,statut,verification") \
            .order("cree_le", desc=True).limit(500).execute().data

    # otp
    def otp_get(self, email: str) -> dict | None:
        return self._one(self._t("otp_codes").select("*").eq("email", email).limit(1).execute())

    def otp_set(self, email: str, row: dict) -> None:
        self._t("otp_codes").upsert({"email": email, **row}, on_conflict="email").execute()

    def otp_update(self, email: str, **fields) -> None:
        self._t("otp_codes").update(fields).eq("email", email).execute()

    def otp_delete(self, email: str) -> None:
        self._t("otp_codes").delete().eq("email", email).execute()

    # sessions
    def session_create(self, row: dict) -> None:
        self._t("sessions").insert(row).execute()

    def session_get(self, token_hash: str) -> dict | None:
        return self._one(self._t("sessions").select("*").eq("token_hash", token_hash).limit(1).execute())

    def session_update(self, token_hash: str, **fields) -> None:
        self._t("sessions").update(fields).eq("token_hash", token_hash).execute()

    def session_delete(self, token_hash: str) -> None:
        self._t("sessions").delete().eq("token_hash", token_hash).execute()

    # analyses & replies (encrypted)
    def analysis_add(self, row: dict) -> dict:
        return _dec_analysis(self._t("analyses").insert(_enc_analysis(row)).execute().data[0])

    def analyses_for(self, user_id: str) -> list[dict]:
        rows = self._t("analyses").select("*").eq("utilisateur_id", user_id).order("cree_le", desc=True).limit(100).execute().data
        return [_dec_analysis(r) for r in rows]

    def analysis_get(self, analysis_id: str, user_id: str) -> dict | None:
        row = self._one(self._t("analyses").select("*").eq("id", analysis_id).eq("utilisateur_id", user_id).limit(1).execute())
        return _dec_analysis(row)

    def reponse_add(self, row: dict) -> dict:
        return _dec_fields(self._t("reponses").insert(_enc_fields(row, "lettre")).execute().data[0], "lettre")

    def reponses_for(self, user_id: str) -> list[dict]:
        rows = self._t("reponses").select("*").eq("utilisateur_id", user_id).order("cree_le", desc=True).limit(100).execute().data
        return [_dec_fields(r, "lettre") for r in rows]

    def upcoming_deadlines(self, days: int) -> list[dict]:
        today, limit = date.today(), date.today() + timedelta(days=days)
        rows = self._t("analyses").select("id,reference,entreprise,montant_total,date_limite,utilisateurs(email,prenom)") \
            .gte("date_limite", today.isoformat()).lte("date_limite", limit.isoformat()).execute().data
        return [{"id": r["id"], "reference": r["reference"], "entreprise": r["entreprise"], "montant_total": r["montant_total"],
                 "date_limite": r["date_limite"], "email": r["utilisateurs"]["email"], "prenom": r["utilisateurs"]["prenom"],
                 "jours_restants": (date.fromisoformat(r["date_limite"]) - today).days}
                for r in rows if r.get("utilisateurs")]

    # journal
    def journal_add(self, row: dict) -> None:
        try:
            self._t("journal").insert(row).execute()
        except Exception as e:  # never block a user action because the audit insert failed
            log.error("journal insert failed: %s", e)

    def journal_list(self, limit: int) -> list[dict]:
        return self._t("journal").select("*").order("horodatage", desc=True).limit(limit).execute().data

    def journal_has(self, action: str, cible: str) -> bool:
        return bool(self._t("journal").select("id").eq("action", action).eq("cible", cible).limit(1).execute().data)

    # favourites
    def favoris_list(self, user_id: str) -> list[dict]:
        return self._t("favoris").select("*").eq("utilisateur_id", user_id).order("cree_le", desc=True).limit(200).execute().data

    def favoris_add(self, row: dict) -> dict:
        return self._t("favoris").upsert(row, on_conflict="utilisateur_id,type,ref").execute().data[0]

    def favoris_delete(self, fav_id: str, user_id: str) -> None:
        self._t("favoris").delete().eq("id", fav_id).eq("utilisateur_id", user_id).execute()

    # dossiers
    def dossiers_all(self) -> list[dict] | None:
        out, start, page = [], 0, 1000
        while True:
            rows = self._t("dossiers").select("data").range(start, start + page - 1).execute().data
            out += [r["data"] for r in rows]
            if len(rows) < page:
                break
            start += page
        return out or None

    # identity documents (encrypted)
    def piece_add(self, row: dict) -> dict:
        return _sans(self._t("pieces_justificatives").insert(_enc_fields(row, "contenu")).execute().data[0], "contenu")

    def pieces_for(self, user_id: str) -> list[dict]:
        return self._t("pieces_justificatives").select("id,utilisateur_id,type,nom,mime,taille,cree_le") \
            .eq("utilisateur_id", user_id).execute().data

    def piece_get(self, piece_id: str) -> dict | None:
        return _dec_fields(self._one(self._t("pieces_justificatives").select("*").eq("id", piece_id).limit(1).execute()), "contenu")

    # file assignments and settlement approvals
    def affectation_set(self, row: dict) -> None:
        self._t("affectations").upsert(row, on_conflict="dossier_id").execute()

    def affectations_all(self) -> dict[str, dict]:
        return {r["dossier_id"]: r for r in self._t("affectations").select("*").limit(5000).execute().data}

    def conciliation_add(self, row: dict) -> dict:
        return self._t("conciliations").insert(row).execute().data[0]

    def conciliations_list(self) -> list[dict]:
        return self._t("conciliations").select("*").order("cree_le", desc=True).limit(500).execute().data

    def conciliation_update(self, cid: str, **fields) -> dict | None:
        return self._one(self._t("conciliations").update(fields).eq("id", cid).execute())

    # messaging (contents encrypted)
    def conversation_add(self, row: dict) -> dict:
        return self._t("conversations").insert(row).execute().data[0]

    def conversation_get(self, cid: str) -> dict | None:
        return self._one(self._t("conversations").select("*").eq("id", cid).limit(1).execute())

    def conversation_par_reference(self, reference: str, entreprise_id: str) -> dict | None:
        return self._one(self._t("conversations").select("*").eq("reference", reference).eq("entreprise_id", entreprise_id).limit(1).execute())

    def conversations_all(self) -> list[dict]:
        return self._t("conversations").select("*").order("dernier_message_le", desc=True).limit(500).execute().data

    def conversation_update(self, cid: str, **fields) -> None:
        self._t("conversations").update(fields).eq("id", cid).execute()

    def message_add(self, row: dict) -> dict:
        row = {"lu_par": [row.get("auteur_id")], **row}
        out = self._t("messages").insert(_enc_fields(row, "contenu", "piece_contenu")).execute().data[0]
        return _sans(_dec_fields(out, "contenu"), "piece_contenu") | {"a_piece": bool(out.get("piece_nom"))}

    def messages_for(self, cid: str) -> list[dict]:
        rows = self._t("messages").select("id,conversation_id,auteur_id,auteur_role,auteur_nom,contenu,piece_nom,piece_mime,lu_par,cree_le") \
            .eq("conversation_id", cid).order("cree_le").limit(1000).execute().data
        return [_dec_fields(r, "contenu") | {"a_piece": bool(r.get("piece_nom"))} for r in rows]

    def message_piece(self, mid: str) -> dict | None:
        return _dec_fields(self._one(self._t("messages").select("*").eq("id", mid).limit(1).execute()), "piece_contenu")

    def messages_marquer_lus(self, cid: str, user_id: str) -> None:
        for m in self._t("messages").select("id,lu_par").eq("conversation_id", cid).execute().data:
            if user_id not in (m["lu_par"] or []):
                self._t("messages").update({"lu_par": [*(m["lu_par"] or []), user_id]}).eq("id", m["id"]).execute()

    # access log shown to the taxpayer ("who consulted my file")
    def acces_add(self, row: dict) -> None:
        try:
            self._t("acces").insert(row).execute()
        except Exception as e:   # the access log must never block the consultation itself
            log.error("access log insert failed: %s", e)

    def acces_pour(self, references: list[str]) -> list[dict]:
        if not references:
            return []
        return self._t("acces").select("*").in_("reference", references).order("horodatage", desc=True).limit(200).execute().data


@lru_cache(maxsize=1)
def repo() -> MemoryRepo | SupabaseRepo:
    if SUPABASE_URL and SUPABASE_SERVICE_KEY:
        try:
            r = SupabaseRepo()
            r._t("journal").select("id").limit(1).execute()   # fail fast if the schema is missing
            log.info("Database: Supabase")
            return r
        except Exception as e:
            log.error("Supabase unavailable (%s): falling back to in-memory storage", e)
    log.info("Database: in-memory")
    return MemoryRepo()
