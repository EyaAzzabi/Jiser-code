"""Taxpayer-side analysis of a notification: procedure checks, item-by-item contestability,
applicable articles, plain-language explanations and the reply deadline.

Scores come from the ML model and the CDPF rules (always available). Claude, when available,
only rewrites the explanations and arguments in plain language, grounded on the retrieved
articles; if it is unavailable the rule-based texts are used as they are.
"""
from __future__ import annotations

from datetime import date, timedelta

from pydantic import BaseModel

from ..domain import CHEF_TYPES, DELAI_REPONSE_JOURS, DROIT_REPRISE_ANS
from ..schemas import AnalyseNotification, ArticleRef, ChefAnalyse, ChefRedressement, Dossier, Notification
from . import llm, scoring
from .legal_rag import get_index
from .procedure import check_procedure

DEFAULT_PIECES_RATIO = 0.3   # unknown for a fresh upload: assume few documents gathered yet

EXPLICATIONS = {
    "TVA_FACTURES_NON_CONFORMES": "L'administration refuse la TVA que vous avez déduite sur certaines factures d'achat. "
                                  "Elle estime que ces factures ne sont pas conformes ou ne correspondent pas à de vraies opérations. "
                                  "Vous devez donc reverser cette TVA, plus des pénalités.",
    "CHARGES_NON_DEDUCTIBLES": "L'administration considère que certaines dépenses ne peuvent pas être déduites de votre bénéfice "
                               "(pas de justificatif ou pas de lien avec votre activité). Elle les ajoute à votre bénéfice imposable.",
    "MINORATION_CA": "L'administration pense que vous avez déclaré moins de chiffre d'affaires que ce que vous avez réellement "
                     "encaissé, en comparant vos déclarations à vos relevés bancaires.",
    "RECONSTITUTION_CA": "Votre comptabilité n'a pas été acceptée : l'administration a recalculé elle-même votre chiffre "
                         "d'affaires avec une méthode d'estimation (par exemple un coefficient de marge).",
    "RETENUE_SOURCE_NON_EFFECTUEE": "Vous deviez retenir un pourcentage sur certains paiements (honoraires, commissions…) et le "
                                    "reverser à l'État. L'administration estime que cela n'a pas été fait.",
    "AVANTAGES_ENTREPRISES_LIEES": "L'administration estime que vous avez vendu ou acheté à une société liée à un prix anormal, "
                                   "ce qui a déplacé une partie de votre bénéfice. Elle réintègre la différence.",
}


def _contestabilite(p_maintenu: float, chef: ChefRedressement, notif: Notification) -> str:
    if notif.date_notification.year > chef.exercice + DROIT_REPRISE_ANS or chef.motivation_qualite == "absente":
        return "contestable"
    if p_maintenu >= 0.55:
        return "solide"
    if p_maintenu >= 0.30:
        return "discutable"
    return "contestable"


VICE_TEXT = {
    "AVIS_PREALABLE": "l'avis préalable de vérification n'est pas établi",
    "DELAI_AVIS_15J": "la vérification a commencé moins de 15 jours après l'avis",
    "MENTION_ASSISTANCE": "l'avis ne mentionne pas le droit de se faire assister",
    "DUREE_MAX": "la vérification a dépassé la durée maximale légale",
    "MENTION_DELAI_30J": "la notification n'indique pas le délai de réponse de 30 jours",
    "PENALITES_INDIQUEES": "les pénalités ne sont pas chiffrées",
    "DROIT_REPRISE": "un exercice est hors du délai de reprise",
}


def _arguments(chef: ChefRedressement, notif: Notification, vices: list) -> list[str]:
    args = [f"Vice de procédure : {VICE_TEXT.get(v.code, v.label.lower())}. {v.detail} "
            f"(article {v.article.replace('cdpf-art-', '')} du CDPF)" for v in vices]
    if chef.motivation_qualite == "absente":
        args.append("Ce chef n'est pas motivé : l'article 43 du CDPF impose d'indiquer les chefs de redressement et la méthode retenue.")
    elif chef.motivation_qualite == "sommaire":
        args.append("La motivation est très sommaire : demander le détail des calculs et des pièces sur lesquelles "
                    "l'administration s'appuie.")
    if not chef.article_invoque:
        args.append("Aucune base légale n'est citée pour ce chef.")
    if notif.date_notification.year > chef.exercice + DROIT_REPRISE_ANS:
        args.append(f"L'exercice {chef.exercice} est hors du délai de reprise de 4 ans (article 19 du CDPF).")
    if not args:
        args.append("La procédure semble régulière : la contestation doit porter sur le fond, pièces justificatives à l'appui.")
    return args


def _articles(chef: ChefRedressement) -> list[ArticleRef]:
    index = get_index()
    refs: list[ArticleRef] = []
    for aid in CHEF_TYPES.get(chef.type, {}).get("articles", []):
        ref = index.get(aid)
        if ref:
            refs.append(ref)
    for ref in index.search(f"{chef.libelle} {chef.motivation}", k=3):
        if all(r.id != ref.id for r in refs):
            refs.append(ref)
    return refs[:3]


class _LLMChef(BaseModel):
    chef_id: str
    explication: str
    arguments: list[str]


class _LLMAnalyse(BaseModel):
    resume: str
    chefs: list[_LLMChef]


def _llm_rewrite(analyse: AnalyseNotification) -> _LLMAnalyse | None:
    if not llm.available():
        return None
    parts = [
        "Voici l'analyse automatique d'une notification de redressement fiscal (JSON), avec les articles de loi "
        "retrouvés pour chaque chef. Réécris pour le chef d'entreprise : (1) un résumé de 3 phrases maximum de sa "
        "situation et de ce qu'il doit faire avant la date limite ; (2) pour chaque chef, une explication simple de ce "
        "qui lui est reproché et 2 à 4 arguments concrets de réponse. Garde les vices de procédure détectés et cite "
        "les articles fournis (numéro et code). N'invente aucun fait, montant ni article.",
        analyse.model_dump_json(exclude={"mode"}),
    ]
    try:
        return llm.parse("analyse", "\n\n".join(parts), _LLMAnalyse)
    except llm.LLMUnavailable:
        return None


def analyse(notif: Notification, pieces_ratio: float = DEFAULT_PIECES_RATIO, today: date | None = None) -> AnalyseNotification:
    today = today or date.today()
    procedure = check_procedure(notif)
    vices_dossier = [p for p in procedure if p.statut == "vice" and p.code != "CHEFS_MOTIVES"]
    dossier = Dossier(id="upload", notification=notif, etape="Notification", date_etape=notif.date_notification,
                      pieces_fournies_ratio=pieces_ratio, reponse_contribuable=True, statut="en_cours")
    probas = scoring.chef_probas(dossier)
    _, shares = scoring.expected_recovery(dossier, probas)

    chefs = []
    contestable_amount = 0.0
    for chef, p, share in zip(notif.chefs, probas, shares):
        total = chef.montant_principal + chef.penalites
        contestable_amount += total * (1 - share)
        meta = CHEF_TYPES.get(chef.type, {})
        chefs.append(ChefAnalyse(
            chef=chef,
            explication=EXPLICATIONS.get(chef.type, "L'administration a redressé ce point : lisez la motivation ci-dessous."),
            contestabilite=_contestabilite(float(p[0]), chef, notif),
            arguments=_arguments(chef, notif, vices_dossier),
            pieces_a_fournir=meta.get("pieces", ["Toute pièce justifiant l'opération redressée"]),
            articles=_articles(chef),
        ))

    deadline = notif.date_notification + timedelta(days=DELAI_REPONSE_JOURS)
    n_contest = sum(c.contestabilite != "solide" for c in chefs)
    resume = (f"Vous devez répondre par écrit avant le {deadline:%d/%m/%Y} (article 44 du CDPF), sinon la taxation "
              f"sera établie d'office (article 47). {n_contest} chef(s) sur {len(chefs)} peuvent être contestés"
              + (f", et {len(vices_dossier)} vice(s) de procédure ont été détectés." if vices_dossier else ".")
              + " Faites relire votre réponse par un conseiller fiscal.")
    result = AnalyseNotification(
        notification=notif, montant_total=notif.montant_total, date_limite_reponse=deadline,
        jours_restants=(deadline - today).days, procedure=procedure, chefs=chefs, resume=resume,
        montant_contestable=round(contestable_amount, 3), mode="hors_ligne")

    rewrite = _llm_rewrite(result)
    if rewrite:
        by_id = {c.chef_id: c for c in rewrite.chefs}
        for ca in result.chefs:
            if ca.chef.id in by_id:
                ca.explication = by_id[ca.chef.id].explication
                ca.arguments = by_id[ca.chef.id].arguments or ca.arguments
        result.resume = rewrite.resume
        result.mode = "ia"
    return result
