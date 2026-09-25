"""AI features of the administration space.

* synthese_stock   — plain-language briefing of the whole stock + 3 recommended actions
* avis_dossier     — legal opinion on one file + draft settlement letter
* ameliorer_notification — rewrites weak reassessment motivations before the notice is sent

Each function returns the LLM's answer when available and a rule-based version otherwise,
with a `mode` field ("ia" | "hors_ligne") so the UI can show which one it displays.
"""
from __future__ import annotations

from pydantic import BaseModel

from ..schemas import AnalyseNotification
from . import llm


def fmt_dt(amount: float) -> str:
    """Rounded dinars for narrative text: 117296590.989 -> "117 296 591 DT"."""
    return f"{round(amount):,}".replace(",", " ") + " DT"


class Action(BaseModel):
    titre: str
    detail: str


class Synthese(BaseModel):
    synthese: str
    actions: list[Action]
    mode: str = "ia"


class _SyntheseLLM(BaseModel):
    synthese: str
    actions: list[Action]


def synthese_stock(dash: dict) -> Synthese:
    k = dash["kpi"]
    top_gouv = [{"gouvernorat": g["gouvernorat"], "montant": fmt_dt(g["montant"])} for g in dash["par_gouvernorat"][:3]]
    causes = dash["causes_annulation"][:3]
    facts = {
        "montant_bloque": fmt_dt(k["montant_bloque"]), "dossiers_en_cours": k["dossiers_en_cours"],
        "recouvrable_estime": fmt_dt(k["montant_recouvrable_estime"]), "dossiers_avec_vice": k["dossiers_avec_vice"],
        "taux_recouvrement_historique": k["taux_recouvrement_historique"], "taux_conciliation": k["taux_conciliation"],
        "duree_moyenne_mois": k["duree_moyenne_mois"], "gouvernorats_principaux": top_gouv,
        "causes_annulation": causes, "gain_tri_vs_fifo_pct_arrondi": round((dash.get("modele") or {}).get("triage", {}).get("gain_vs_fifo_pct") or 0),
    }
    if llm.available():
        try:
            out = llm.parse("synthese-stock",
                            "Tu es l'analyste IA de l'unité du contentieux fiscal. À partir de ces indicateurs (JSON), écris une "
                            "synthèse de 4 phrases maximum pour la cheffe du contentieux, puis 3 actions prioritaires concrètes "
                            "(titre court + détail d'une phrase). N'invente aucun chiffre.\n\n" + str(facts), _SyntheseLLM, max_tokens=1500)
            return Synthese(synthese=out.synthese, actions=out.actions[:3])
        except llm.LLMUnavailable:
            pass
    g = top_gouv[0] if top_gouv else {"gouvernorat": "—"}
    c = causes[0] if causes else {"cause": "—", "nb": 0}
    return Synthese(mode="hors_ligne", synthese=(
        f"{k['dossiers_en_cours']} dossiers sont en cours pour {fmt_dt(k['montant_bloque'])} bloqués, dont environ "
        f"{fmt_dt(k['montant_recouvrable_estime'])} recouvrables selon le modèle. {g['gouvernorat']} concentre le plus gros montant. "
        f"{k['dossiers_avec_vice']} dossiers présentent un vice de procédure et risquent l'annulation. "
        f"Historiquement, la première cause d'annulation est : {c['cause'].lower()}."),
        actions=[
            Action(titre="Traiter les 20 dossiers prioritaires", detail="Le tri par montant recouvrable concentre l'effort là où il rapporte le plus."),
            Action(titre="Concilier les dossiers à vice de procédure", detail=f"{k['dossiers_avec_vice']} dossiers ont peu de chances devant le juge : une conciliation encaisse plus vite."),
            Action(titre="Contrôle qualité systématique avant envoi", detail="Vérifier chaque notification évite les annulations pour vice de procédure ou défaut de motivation."),
        ])


class AvisDossier(BaseModel):
    avis: str
    points_forts: list[str]
    points_faibles: list[str]
    lettre_conciliation: str
    mode: str = "ia"


class _AvisLLM(BaseModel):
    avis: str
    points_forts: list[str]
    points_faibles: list[str]
    lettre_conciliation: str


def avis_dossier(detail: dict) -> AvisDossier:
    n = detail["dossier"]["notification"]
    score = detail["score"]
    conc = detail["conciliation"]
    # each defect carries its exact article so the model never has to guess a number
    vices = [f"{p['detail']} (article {p['article'].split('-art-')[1].replace('-', ' ')} du CDPF)"
             for p in detail["procedure"] if p["statut"] == "vice"]
    facts = {"entreprise": n["entreprise"]["nom"], "reference": n["reference"], "score_solidite": score["score_solidite"],
             "facteurs": score["explications"], "vices": vices,
             "chefs": [{"libelle": i["libelle"], "montant": i["montant"], "p_maintenu": i["p_maintenu"], "action": i["action"],
                        "montant_propose": i["montant_propose"]} for i in conc["items"]],
             "montant_notifie": conc["montant_notifie"], "montant_propose": conc["montant_propose"]}
    if llm.available():
        try:
            out = llm.parse("avis-dossier",
                            "Tu es le juriste IA de l'unité du contentieux fiscal tunisien. À partir de ce dossier (JSON), rédige : "
                            "(1) un avis de 4 phrases sur la solidité du redressement devant le juge ; (2) 2 à 4 points forts et points "
                            "faibles ; (3) un projet de lettre proposant une conciliation au contribuable avec les montants proposés, "
                            "Ne cite QUE les articles qui figurent dans les données (champ vices) ; n'invente aucun article, "
                            "fait ni montant.\n\n" + str(facts),
                            _AvisLLM, max_tokens=3000)
            return AvisDossier(**out.model_dump())
        except llm.LLMUnavailable:
            pass
    weak = [e["facteur"] for e in score["explications"] if e["impact"] < 0]
    strong = [e["facteur"] for e in score["explications"] if e["impact"] > 0]
    lignes = "\n".join(f"- {i['libelle']} : {fmt_dt(i['montant_propose'])}" for i in conc["items"] if i["montant_propose"] > 0)
    lettre = (f"Objet : proposition de règlement amiable — notification {n['reference']}\n\n"
              f"Madame, Monsieur,\n\nÀ la suite de l'examen de votre dossier, l'administration vous propose un règlement amiable "
              f"pour un montant total de {fmt_dt(conc['montant_propose'])}, réparti comme suit :\n{lignes or '- aucun montant maintenu'}\n\n"
              f"Cette proposition met fin au litige sans procédure contentieuse. Nous vous invitons à nous faire part de votre accord "
              f"dans un délai de quinze jours.\n\nLe Chef du contentieux")
    return AvisDossier(mode="hors_ligne",
                       avis=(f"Score de solidité : {score['score_solidite']}/100. "
                             + (f"La procédure présente {len(vices)} vice(s), ce qui expose le redressement à une annulation. " if vices else "La procédure est régulière. ")
                             + f"Le contentieux rapporterait en moyenne {fmt_dt(conc['montant_attendu_contentieux'])}, "
                               f"contre {fmt_dt(conc['montant_propose'])} encaissables tout de suite par une conciliation."),
                       points_forts=strong or ["Aucun facteur favorable marquant"], points_faibles=weak or vices or ["Aucune faiblesse marquante"],
                       lettre_conciliation=lettre)


class MotivationAmelioree(BaseModel):
    chef_id: str
    probleme: str
    motivation_proposee: str


class Ameliorations(BaseModel):
    ameliorations: list[MotivationAmelioree]
    mode: str = "ia"


class _AmeliorationsLLM(BaseModel):
    ameliorations: list[MotivationAmelioree]


def ameliorer_notification(a: AnalyseNotification) -> Ameliorations:
    weak = [c for c in a.chefs if c.chef.motivation_qualite != "detaillee" or not c.chef.article_invoque]
    if not weak:
        return Ameliorations(ameliorations=[], mode="hors_ligne")
    if llm.available():
        payload = [{"chef_id": c.chef.id, "libelle": c.chef.libelle, "impot": c.chef.impot, "exercice": c.chef.exercice,
                    "montant": c.chef.montant_principal, "methode": c.chef.methode, "motivation_actuelle": c.chef.motivation,
                    "article_invoque": c.chef.article_invoque, "articles_pertinents": [r.id for r in c.articles]} for c in weak]
        try:
            out = llm.parse("ameliorer-notif",
                            "Tu aides un vérificateur fiscal tunisien à renforcer sa notification AVANT envoi (article 43 du CDPF : "
                            "chefs et méthode doivent être indiqués). Pour chaque chef (JSON), explique le problème en une phrase et "
                            "propose une motivation complète et précise : faits, méthode de calcul, base légale. Utilise des "
                            "placeholders [À COMPLÉTER : …] pour les faits que tu ne connais pas ; n'invente aucun chiffre.\n\n" + str(payload),
                            _AmeliorationsLLM, max_tokens=3000)
            return Ameliorations(ameliorations=out.ameliorations)
        except llm.LLMUnavailable:
            pass
    return Ameliorations(mode="hors_ligne", ameliorations=[MotivationAmelioree(
        chef_id=c.chef.id,
        probleme=("Chef non motivé" if c.chef.motivation_qualite == "absente" else "Motivation trop sommaire")
                 + ("" if c.chef.article_invoque else " et base légale absente"),
        motivation_proposee=(f"Au titre de l'exercice {c.chef.exercice}, [À COMPLÉTER : faits constatés, pièces examinées]. "
                             f"Méthode retenue : {c.chef.methode or '[À COMPLÉTER]'}. Base légale : "
                             f"{c.chef.article_invoque or (c.articles[0].id.replace('-art-', ' art. ').upper() if c.articles else '[À COMPLÉTER]')}. "
                             f"Montant redressé en principal : {fmt_dt(c.chef.montant_principal)}."),
    ) for c in weak])
