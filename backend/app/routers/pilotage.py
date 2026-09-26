"""Administration hierarchy: national steering (minister), team and approvals (head of centre)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..deps import permission
from ..services import pilotage

router = APIRouter(prefix="/api/pilotage", tags=["pilotage"])


def _liste(v: str | None) -> list[str]:
    return [x for x in (v or "").split(",") if x]


@router.get("/national")
def national(gouvernorats: str | None = None, motifs: str | None = None, etape: str | None = None, tranche: str | None = None,
             periode_mois: int | None = None, _: dict = Depends(permission("stats:national"))):
    """Minister's dashboard: aggregates only (k-anonymity), filtered live."""
    return pilotage.national({"gouvernorats": _liste(gouvernorats), "motifs": _liste(motifs), "etape": etape,
                              "tranche": tranche, "periode_mois": periode_mois})


@router.get("/equipe")
def equipe(session: dict = Depends(permission("equipe:lire"))):
    return pilotage.equipe(session["user"])


class AffectationRequest(BaseModel):
    dossier_id: str
    agent_id: str


@router.post("/affectations")
def affecter(req: AffectationRequest, session: dict = Depends(permission("dossiers:affecter"))):
    try:
        return pilotage.affecter(session["user"], req.dossier_id, req.agent_id, session["email"])
    except LookupError as e:
        raise HTTPException(404, str(e)) from e
    except PermissionError as e:
        raise HTTPException(403, str(e)) from e


@router.get("/conciliations-a-valider")
def a_valider(session: dict = Depends(permission("conciliation:valider"))):
    return pilotage.conciliations_a_valider(session["user"])


class DecisionConciliation(BaseModel):
    decision: str   # validee | refusee
    motif: str = ""


@router.post("/conciliations/{cid}/decision")
def decider(cid: str, req: DecisionConciliation, session: dict = Depends(permission("conciliation:valider"))):
    if req.decision not in {"validee", "refusee"}:
        raise HTTPException(422, "Décision invalide.")
    try:
        return pilotage.decider_conciliation(session["user"], session["email"], cid, req.decision, req.motif)
    except LookupError as e:
        raise HTTPException(404, str(e)) from e
    except PermissionError as e:
        raise HTTPException(403, str(e)) from e
