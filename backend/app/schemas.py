"""Data contract shared by the synthetic data, the ML model, the API and the frontend."""
from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field

MotivationQualite = Literal["detaillee", "sommaire", "absente"]
Issue = Literal["maintenu", "reduit", "annule"]
Contestabilite = Literal["solide", "discutable", "contestable"]


class Entreprise(BaseModel):
    nom: str
    matricule_fiscal: str
    secteur: str
    taille: Literal["TPE", "PME", "GE"]
    gouvernorat: str
    regime: str = "Réel"


class ChefRedressement(BaseModel):
    id: str
    type: str = Field(description="Clé de domain.CHEF_TYPES")
    libelle: str
    impot: str
    exercice: int
    montant_principal: float
    penalites: float
    article_invoque: Optional[str] = None
    motivation: str = ""
    motivation_qualite: MotivationQualite = "detaillee"
    methode: str = ""


class Notification(BaseModel):
    reference: str
    centre: str
    type_verification: Literal["approfondie", "preliminaire"]
    comptabilite_conforme: bool = True
    date_avis: Optional[date] = None
    date_debut_verification: Optional[date] = None
    date_notification: date
    exercices_verifies: list[int]
    mention_assistance: bool = True
    mention_delai_30j: bool = True
    penalites_indiquees: bool = True
    entreprise: Entreprise
    chefs: list[ChefRedressement]

    @property
    def montant_total(self) -> float:
        return round(sum(c.montant_principal + c.penalites for c in self.chefs), 3)


class ChefIssue(BaseModel):
    chef_id: str
    issue: Issue
    montant_final: float


class Dossier(BaseModel):
    """A contentious file: a notification plus its history and (for closed files) its outcome."""
    id: str
    notification: Notification
    etape: str
    date_etape: date
    pieces_fournies_ratio: float = Field(ge=0, le=1, description="Part des justificatifs produits")
    reponse_contribuable: bool
    statut: Literal["en_cours", "cloture"]
    issues: list[ChefIssue] = []
    montant_recouvre: Optional[float] = None


# ---- API responses ------------------------------------------------------------------------

class ArticleRef(BaseModel):
    id: str
    code: str
    article: str
    extrait: str
    source_url: str


class ProcedureCheck(BaseModel):
    code: str
    label: str
    article: str
    statut: Literal["ok", "vice", "a_verifier"]
    detail: str


class ChefAnalyse(BaseModel):
    chef: ChefRedressement
    explication: str
    contestabilite: Contestabilite
    arguments: list[str]
    pieces_a_fournir: list[str]
    articles: list[ArticleRef]


class AnalyseNotification(BaseModel):
    notification: Notification
    montant_total: float
    date_limite_reponse: date
    jours_restants: int
    procedure: list[ProcedureCheck]
    chefs: list[ChefAnalyse]
    resume: str
    montant_contestable: float
    mode: Literal["ia", "hors_ligne"]
    langue: Literal["fr", "derja"] = "fr"
    analyse_id: Optional[str] = None


class ScoreExplication(BaseModel):
    facteur: str
    impact: float


class ScoreDossier(BaseModel):
    dossier_id: str
    score_solidite: int = Field(ge=0, le=100)
    proba_maintien: float
    montant_recouvrable_estime: float
    explications: list[ScoreExplication]
