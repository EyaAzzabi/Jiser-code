"""Persistence layer: Supabase (PostgreSQL) when configured, in-memory otherwise.

Both backends expose the same methods, so the rest of the app never checks which one runs.
The Supabase client uses the service_role key and must only run server-side.
"""
from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache

from ..config import SUPABASE_SERVICE_KEY, SUPABASE_URL

log = logging.getLogger("jiser.db")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(d: datetime | date) -> str:
    return d.isoformat()


class MemoryRepo:
    kind = "memoire"

    def __init__(self) -> None:
        self.users: dict[str, dict] = {}
        self.otps: dict[str, dict] = {}
        self.sessions: dict[str, dict] = {}
        self.analyses: dict[str, dict] = {}
        self.reponses: list[dict] = []
        self.journal: list[dict] = []

    # users
    def get_user(self, email: str) -> dict | None:
        return self.users.get(email)

    def create_user(self, row: dict) -> dict:
        row = {"id": str(uuid.uuid4()), "cree_le": _iso(_now()), "actif": True, **row}
        self.users[row["email"]] = row
        return row

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

    # analyses & replies
    def analysis_add(self, row: dict) -> dict:
        row = {"id": str(uuid.uuid4()), "cree_le": _iso(_now()), **row}
        self.analyses[row["id"]] = row
        return row

    def analyses_for(self, user_id: str) -> list[dict]:
        return sorted((a for a in self.analyses.values() if a["utilisateur_id"] == user_id),
                      key=lambda a: a["cree_le"], reverse=True)

    def analysis_get(self, analysis_id: str, user_id: str) -> dict | None:
        a = self.analyses.get(analysis_id)
        return a if a and a["utilisateur_id"] == user_id else None

    def reponse_add(self, row: dict) -> dict:
        row = {"id": str(uuid.uuid4()), "cree_le": _iso(_now()), **row}
        self.reponses.append(row)
        return row

    def reponses_for(self, user_id: str) -> list[dict]:
        return sorted((r for r in self.reponses if r["utilisateur_id"] == user_id), key=lambda r: r["cree_le"], reverse=True)

    def upcoming_deadlines(self, days: int) -> list[dict]:
        today, limit = date.today(), date.today() + timedelta(days=days)
        by_id = {u["id"]: u for u in self.users.values()}
        out = []
        for a in self.analyses.values():
            d = date.fromisoformat(str(a["date_limite"]))
            if today <= d <= limit and a["utilisateur_id"] in by_id:
                u = by_id[a["utilisateur_id"]]
                out.append({**{k: a[k] for k in ("reference", "entreprise", "montant_total", "date_limite")},
                            "email": u["email"], "prenom": u["prenom"], "jours_restants": (d - today).days})
        return out

    # journal
    def journal_add(self, row: dict) -> None:
        self.journal.insert(0, {"horodatage": _iso(_now()), "decision_humaine": "en attente", **row})
        del self.journal[1000:]

    def journal_list(self, limit: int) -> list[dict]:
        return self.journal[:limit]

    # dossiers
    def dossiers_all(self) -> list[dict] | None:
        return None   # None = use the local synthetic file


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

    def get_user(self, email: str) -> dict | None:
        return self._one(self._t("utilisateurs").select("*").eq("email", email).limit(1).execute())

    def create_user(self, row: dict) -> dict:
        return self._t("utilisateurs").insert(row).execute().data[0]

    def touch_login(self, email: str) -> None:
        self._t("utilisateurs").update({"derniere_connexion": _iso(_now())}).eq("email", email).execute()

    def list_users(self) -> list[dict]:
        return self._t("utilisateurs").select("id,email,role,nom,prenom,fonction,details,cree_le,derniere_connexion,actif") \
            .order("cree_le", desc=True).limit(200).execute().data

    def otp_get(self, email: str) -> dict | None:
        return self._one(self._t("otp_codes").select("*").eq("email", email).limit(1).execute())

    def otp_set(self, email: str, row: dict) -> None:
        self._t("otp_codes").upsert({"email": email, **row}, on_conflict="email").execute()

    def otp_update(self, email: str, **fields) -> None:
        self._t("otp_codes").update(fields).eq("email", email).execute()

    def otp_delete(self, email: str) -> None:
        self._t("otp_codes").delete().eq("email", email).execute()

    def session_create(self, row: dict) -> None:
        self._t("sessions").insert(row).execute()

    def session_get(self, token_hash: str) -> dict | None:
        return self._one(self._t("sessions").select("*").eq("token_hash", token_hash).limit(1).execute())

    def session_update(self, token_hash: str, **fields) -> None:
        self._t("sessions").update(fields).eq("token_hash", token_hash).execute()

    def session_delete(self, token_hash: str) -> None:
        self._t("sessions").delete().eq("token_hash", token_hash).execute()

    def analysis_add(self, row: dict) -> dict:
        return self._t("analyses").insert(row).execute().data[0]

    def analyses_for(self, user_id: str) -> list[dict]:
        return self._t("analyses").select("*").eq("utilisateur_id", user_id).order("cree_le", desc=True).limit(100).execute().data

    def analysis_get(self, analysis_id: str, user_id: str) -> dict | None:
        return self._one(self._t("analyses").select("*").eq("id", analysis_id).eq("utilisateur_id", user_id).limit(1).execute())

    def reponse_add(self, row: dict) -> dict:
        return self._t("reponses").insert(row).execute().data[0]

    def reponses_for(self, user_id: str) -> list[dict]:
        return self._t("reponses").select("*").eq("utilisateur_id", user_id).order("cree_le", desc=True).limit(100).execute().data

    def upcoming_deadlines(self, days: int) -> list[dict]:
        today, limit = date.today(), date.today() + timedelta(days=days)
        rows = self._t("analyses").select("reference,entreprise,montant_total,date_limite,utilisateurs(email,prenom)") \
            .gte("date_limite", today.isoformat()).lte("date_limite", limit.isoformat()).execute().data
        return [{"reference": r["reference"], "entreprise": r["entreprise"], "montant_total": r["montant_total"],
                 "date_limite": r["date_limite"], "email": r["utilisateurs"]["email"], "prenom": r["utilisateurs"]["prenom"],
                 "jours_restants": (date.fromisoformat(r["date_limite"]) - today).days}
                for r in rows if r.get("utilisateurs")]

    def journal_add(self, row: dict) -> None:
        try:
            self._t("journal").insert(row).execute()
        except Exception as e:  # never block a user action because the audit insert failed
            log.error("journal insert failed: %s", e)

    def journal_list(self, limit: int) -> list[dict]:
        return self._t("journal").select("*").order("horodatage", desc=True).limit(limit).execute().data

    def dossiers_all(self) -> list[dict] | None:
        out, start, page = [], 0, 1000
        while True:
            rows = self._t("dossiers").select("data").range(start, start + page - 1).execute().data
            out += [r["data"] for r in rows]
            if len(rows) < page:
                break
            start += page
        return out or None


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
