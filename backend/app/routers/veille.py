"""Legal watch pipeline: status, manual run, human validation of changes, embeddings."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..deps import n8n_auth, permission
from ..services import veille

router = APIRouter(tags=["veille juridique"])
GERER = permission("veille:gerer")


@router.get("/api/plateforme/veille")
def etat(_: dict = Depends(GERER)):
    return veille.etat()


class LancerRequest(BaseModel):
    sources: list[str] | None = None


@router.post("/api/plateforme/veille/lancer")
def lancer(req: LancerRequest, session: dict = Depends(GERER)):
    return veille.lancer(f"manuelle ({session['email'].split('@')[0][:2]}***)", req.sources)


@router.post("/api/plateforme/veille/simuler")
def simuler(_: dict = Depends(GERER)):
    return veille.simuler()


class DecisionVeille(BaseModel):
    decision: str   # valide | rejete
    motif: str = ""


@router.post("/api/plateforme/veille/changements/{cid}/decision")
def decider(cid: str, req: DecisionVeille, session: dict = Depends(GERER)):
    if req.decision not in {"valide", "rejete"}:
        raise HTTPException(422, "Décision invalide.")
    try:
        return veille.decider(cid, req.decision, session["email"], req.motif)
    except LookupError as e:
        raise HTTPException(404, str(e)) from e


@router.post("/api/plateforme/veille/embeddings")
def embeddings(_: dict = Depends(GERER)):
    return veille.calculer_embeddings()


@router.get("/api/plateforme/veille/historique/{article_id}")
def historique(article_id: str, _: dict = Depends(GERER)):
    return veille.historique(article_id)


@router.post("/api/n8n/veille", tags=["n8n"])
def veille_n8n(_: None = Depends(n8n_auth)):
    """Called weekly by the n8n legal watch workflow (same pipeline as the internal scheduler)."""
    return veille.lancer("n8n")
