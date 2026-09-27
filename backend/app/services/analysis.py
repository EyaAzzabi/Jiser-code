"""Taxpayer-side analysis of a notification: procedure checks, item-by-item contestability,
applicable articles, plain-language explanations and the reply deadline.

Scores come from the ML model and the CDPF rules (always available). Claude, when available,
only rewrites the explanations and arguments in plain language, grounded on the retrieved
articles; if it is unavailable the rule-based texts are used as they are.
"""
from __future__ import annotations

from datetime import date, timedelta

from pydantic import BaseModel

from ..domain import CHEF_TYPES, DELAI_REPONSE_JOURS, DROIT_REPRISE_ANS, PIECES_AR
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


# Modern Standard Arabic, with the official Tunisian tax vocabulary (المجلة، الفصل، التوظيف الإجباري...)
EXPLICATIONS_AR = {
    "TVA_FACTURES_NON_CONFORMES": "ترفض الإدارة الأداء على القيمة المضافة الذي طرحتموه على بعض فواتير الشراء، إذ تعتبر أن "
                                  "هذه الفواتير غير مطابقة للشروط القانونية أو لا تقابلها عمليات حقيقية. وبالتالي يتعيّن عليكم "
                                  "إرجاع هذا الأداء مع الخطايا.",
    "CHARGES_NON_DEDUCTIBLES": "تعتبر الإدارة أن بعض المصاريف لا يمكن طرحها من ربحكم، لغياب ما يثبتها أو لانعدام صلتها "
                               "بنشاطكم، فأضافتها إلى الربح الخاضع للضريبة.",
    "MINORATION_CA": "ترى الإدارة، بعد مقارنة تصاريحكم بكشوفاتكم البنكية، أنكم صرّحتم برقم معاملات أقل مما قبضتموه فعلًا.",
    "RECONSTITUTION_CA": "لم تُقبل محاسبتكم، فأعادت الإدارة احتساب رقم معاملاتكم بطريقة تقديرية (مثل ضارب الهامش الربحي).",
    "RETENUE_SOURCE_NON_EFFECTUEE": "كان عليكم اقتطاع نسبة من بعض المبالغ المدفوعة (أتعاب، عمولات...) وتحويلها إلى خزينة "
                                    "الدولة، وتعتبر الإدارة أن ذلك لم يتم.",
    "AVANTAGES_ENTREPRISES_LIEES": "تعتبر الإدارة أنكم بعتم أو اشتريتم من مؤسسة مرتبطة بكم بسعر غير عادي، مما أدى إلى تحويل "
                                   "جزء من ربحكم، فأعادت إدماج الفارق.",
}

LANGUE_AR = ("Écris tout en arabe standard moderne (الفصحى), clair et accessible à un chef d'entreprise, sans aucun dialecte. "
             "Utilise la terminologie fiscale officielle tunisienne : « الفصل 44 من مجلة الحقوق والإجراءات الجبائية » pour "
             "« article 44 du CDPF », « مجلة الأداء على القيمة المضافة », « مجلة الضريبة على دخل الأشخاص الطبيعيين والضريبة على "
             "الشركات », « التوظيف الإجباري », « الخطايا », « المراجعة الجبائية المعمقة ». Les montants restent en dinars.")


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
    "MENTION_DELAI_30J": "la notification n'indique pas le délai de réponse de 45 jours",
    "PENALITES_INDIQUEES": "les pénalités ne sont pas chiffrées",
    "DROIT_REPRISE": "un exercice est hors du délai de reprise",
}


VICE_TEXT_AR = {
    "AVIS_PREALABLE": "لم يثبت تبليغ الإعلام المسبق بالمراجعة",
    "DELAI_AVIS_15J": "انطلقت المراجعة قبل مرور 15 يومًا على الإعلام",
    "MENTION_ASSISTANCE": "لم يتضمن الإعلام حق الاستعانة بشخص",
    "DUREE_MAX": "تجاوزت المراجعة المدة القصوى القانونية",
    "MENTION_DELAI_30J": "لم يتضمن الإعلام أجل الرد المحدد بـ 45 يومًا",
    "PENALITES_INDIQUEES": "لم يتم بيان مبلغ الخطايا",
    "DROIT_REPRISE": "إحدى السنوات خارج أجل التقادم",
}


def _arguments_ar(chef: ChefRedressement, notif: Notification, vices: list) -> list[str]:
    """Rule-based arguments in Modern Standard Arabic (used when the generative AI is off)."""
    args = [f"إخلال إجرائي: {VICE_TEXT_AR.get(v.code, v.label)}. {v.detail} "
            f"(الفصل {v.article.replace('cdpf-art-', '').replace('-', ' ')} من مجلة الحقوق والإجراءات الجبائية)" for v in vices]
    if chef.motivation_qualite == "absente":
        args.append("هذا العنصر غير معلّل: يوجب الفصل 43 من مجلة الحقوق والإجراءات الجبائية بيان عناصر التعديل وطريقة احتسابها.")
    elif chef.motivation_qualite == "sommaire":
        args.append("التعليل مقتضب جدًا: اطلبوا تفاصيل الاحتساب والوثائق التي اعتمدتها الإدارة.")
    if not chef.article_invoque:
        args.append("لم يتم ذكر أي سند قانوني لهذا العنصر.")
    if notif.date_notification.year > chef.exercice + DROIT_REPRISE_ANS:
        args.append(f"سنة {chef.exercice} خارج أجل التقادم المحدد بأربع سنوات (الفصل 19 من مجلة الحقوق والإجراءات الجبائية).")
    if not args:
        args.append("تبدو الإجراءات سليمة: يجب أن ينصبّ الاعتراض على الأصل، مع تقديم الوثائق المثبتة.")
    return args


def _arguments(chef: ChefRedressement, notif: Notification, vices: list, langue: str = "fr") -> list[str]:
    if langue == "ar":
        return _arguments_ar(chef, notif, vices)
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


def _llm_rewrite(analyse: AnalyseNotification, langue: str = "fr") -> _LLMAnalyse | None:
    if not llm.available():
        return None
    langue_txt = LANGUE_AR if langue == "ar" else "Écris en français simple."
    parts = [langue_txt,
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


def analyse(notif: Notification, pieces_ratio: float = DEFAULT_PIECES_RATIO, today: date | None = None,
            langue: str = "fr") -> AnalyseNotification:
    today = today or date.today()
    procedure = check_procedure(notif, langue)
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
            explication=(EXPLICATIONS_AR if langue == "ar" else EXPLICATIONS).get(
                chef.type, "قامت الإدارة بتعديل هذا العنصر: اطّلعوا على التعليل أدناه." if langue == "ar"
                else "L'administration a redressé ce point : lisez la motivation ci-dessous."),
            contestabilite=_contestabilite(float(p[0]), chef, notif),
            arguments=_arguments(chef, notif, vices_dossier, langue),
            pieces_a_fournir=[PIECES_AR.get(x, x) if langue == "ar" else x
                              for x in meta.get("pieces", ["Toute pièce justifiant l'opération redressée"])],
            articles=_articles(chef),
        ))

    deadline = notif.date_notification + timedelta(days=DELAI_REPONSE_JOURS)
    n_contest = sum(c.contestabilite != "solide" for c in chefs)
    resume = (f"Vous devez répondre par écrit avant le {deadline:%d/%m/%Y} (article 44 du CDPF), sinon la taxation "
              f"sera établie d'office (article 47). {n_contest} chef(s) sur {len(chefs)} peuvent être contestés"
              + (f", et {len(vices_dossier)} vice(s) de procédure ont été détectés." if vices_dossier else ".")
              + " Faites relire votre réponse par un conseiller fiscal.")
    if langue == "ar":
        resume = (f"يتعيّن عليكم الرد كتابيًا قبل {deadline:%d/%m/%Y} (الفصل 44 من مجلة الحقوق والإجراءات الجبائية)، "
                  f"وإلا تقوم الإدارة بالتوظيف الإجباري (الفصل 47). يمكن الاعتراض على {n_contest} من أصل {len(chefs)} "
                  "من عناصر التعديل"
                  + (f"، وقد رُصدت {len(vices_dossier)} من الإخلالات الإجرائية." if vices_dossier else ".")
                  + " يُنصح بعرض ردكم على مستشار جبائي قبل إرساله.")
    result = AnalyseNotification(
        notification=notif, montant_total=notif.montant_total, date_limite_reponse=deadline,
        jours_restants=(deadline - today).days, procedure=procedure, chefs=chefs, resume=resume,
        montant_contestable=round(contestable_amount, 3), mode="hors_ligne")

    result.langue = langue
    rewrite = _llm_rewrite(result, langue)
    if rewrite:
        by_id = {c.chef_id: c for c in rewrite.chefs}
        for ca in result.chefs:
            if ca.chef.id in by_id:
                ca.explication = by_id[ca.chef.id].explication
                ca.arguments = by_id[ca.chef.id].arguments or ca.arguments
        result.resume = rewrite.resume
        result.mode = "ia"
    return result
