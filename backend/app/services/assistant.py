"""Tax assistant (espace entreprise): answers questions in French or Modern Standard Arabic, grounded on
the retrieved law articles and, when given, on the user's analysed notification (RAG)."""
from __future__ import annotations

from pydantic import BaseModel

from ..schemas import ArticleRef
from . import llm
from .legal_rag import get_index


class Echange(BaseModel):
    role: str        # "utilisateur" | "assistant"
    texte: str


class _Answer(BaseModel):
    reponse: str
    articles_cites: list[str]
    suggestions: list[str]


class AssistantAnswer(BaseModel):
    reponse: str
    articles: list[ArticleRef]
    suggestions: list[str]
    mode: str


CODE_NAMES = {"cdpf": "CDPF", "ctva": "Code de la TVA", "cirppis": "Code de l'IRPP et de l'IS"}

SUGGESTIONS = {
    "fr": ["Quel est mon délai pour répondre ?", "Que se passe-t-il si je ne réponds pas ?", "Qu'est-ce qu'un vice de procédure ?"],
    "ar": ["ما هو أجل الرد على الإعلام بنتائج المراجعة؟", "ماذا يحدث إذا لم أرد في الأجل؟", "ما المقصود بالإخلال الإجرائي؟"],
}

LANGUE_AR = ("Réponds en arabe standard moderne (الفصحى), clair et simple, sans dialecte, avec la terminologie fiscale "
             "officielle tunisienne (ex. « الفصل 44 من مجلة الحقوق والإجراءات الجبائية », « التوظيف الإجباري », « الخطايا »).")

# Arabic legal words -> French vocabulary of the codes, so BM25 also finds the right articles for Arabic questions
# (the vector search handles the meaning; this keeps exact-word retrieval useful)
TERMES_AR = {
    "أجل": "délai", "آجال": "délai", "الرد": "réponse répondre", "رد": "réponse", "إعلام": "notification",
    "نتائج المراجعة": "notification résultats vérification", "مراجعة": "vérification", "المراقبة": "vérification contrôle",
    "التوظيف الإجباري": "taxation office", "خطايا": "pénalités", "خطية": "pénalités", "المحكمة": "tribunal recours",
    "طعن": "recours", "اعتراض": "opposition", "مصالحة": "conciliation", "صلح": "conciliation", "فاتورة": "factures",
    "فواتير": "factures", "القيمة المضافة": "taxe valeur ajoutée déduction", "تقادم": "prescription reprise",
    "حق المراجعة": "droit reprise", "رقم المعاملات": "chiffre affaires", "أعباء": "charges déductibles",
    "الخصم من المورد": "retenue source", "محاسبة": "comptabilité", "وثائق": "pièces justificatives", "إخلال": "vice procédure",
}


def _expand(question: str) -> str:
    return question + " " + " ".join(v for k, v in TERMES_AR.items() if k in question)


def answer(question: str, langue: str = "fr", historique: list[Echange] | None = None, contexte: dict | None = None) -> AssistantAnswer:
    index = get_index()
    query = _expand(question + " " + " ".join(e.texte for e in (historique or [])[-2:] if e.role == "utilisateur"))
    articles = index.search(query, k=4, codes=["cdpf", "ctva", "cirppis"], hybride=True)
    if not articles:   # general procedure questions: notification and reply rules
        articles = [a for a in (index.get("cdpf-art-43"), index.get("cdpf-art-44")) if a]

    if not llm.available():
        intro = ("L'assistant IA n'est pas disponible pour le moment. Voici les articles de loi les plus proches de votre question :"
                 if langue == "fr" else "المساعد الذكي غير متاح حاليًا. إليكم الفصول القانونية الأقرب إلى سؤالكم:")
        return AssistantAnswer(reponse=intro, articles=articles, suggestions=SUGGESTIONS.get(langue, SUGGESTIONS["fr"]), mode="hors_ligne")

    lang = LANGUE_AR if langue == "ar" else "Réponds en français simple."
    parts = [
        lang,
        "Réponds à la question d'un contribuable tunisien en 3 à 8 phrases, en t'appuyant uniquement sur les articles "
        "ci-dessous et sur son dossier s'il est fourni. Dans le texte, cite les articles sous la forme « article 44 du CDPF » "
        "(jamais les identifiants techniques) ; mets leurs identifiants exacts dans `articles_cites`. "
        "Propose 3 questions de suivi courtes dans `suggestions`. Si la réponse dépend d'éléments absents, dis-le.",
        "ARTICLES :\n" + "\n".join(f"[{a.id}] (article {a.article} du {CODE_NAMES.get(a.code, a.code)}) {a.extrait}" for a in articles),
    ]
    if contexte:
        parts.append("DOSSIER DE L'UTILISATEUR (résumé) :\n" + str(contexte)[:6000])
    if historique:
        parts.append("CONVERSATION :\n" + "\n".join(f"{e.role} : {e.texte}" for e in historique[-6:]))
    parts.append(f"QUESTION : {question}")
    try:
        out = llm.parse("assistant", "\n\n".join(parts), _Answer, max_tokens=2000)
    except llm.LLMUnavailable as e:
        return AssistantAnswer(reponse=f"L'assistant IA n'a pas pu répondre ({e}). Articles les plus proches :",
                               articles=articles, suggestions=SUGGESTIONS.get(langue, SUGGESTIONS["fr"]), mode="hors_ligne")
    cited = [a for a in articles if a.id in out.articles_cites] or articles[:2]
    return AssistantAnswer(reponse=out.reponse, articles=cited, suggestions=out.suggestions[:3], mode="ia")


SEP = "§§"


def answer_stream(question: str, langue: str = "fr", historique: list[Echange] | None = None, contexte: dict | None = None):
    """Same answer as `answer`, streamed as events: articles first, then text deltas, then suggestions."""
    index = get_index()
    query = _expand(question + " " + " ".join(e.texte for e in (historique or [])[-2:] if e.role == "utilisateur"))
    articles = index.search(query, k=4, codes=["cdpf", "ctva", "cirppis"], hybride=True) or \
        [a for a in (index.get("cdpf-art-43"), index.get("cdpf-art-44")) if a]
    lang = LANGUE_AR if langue == "ar" else "Réponds en français simple."
    parts = [
        lang,
        "Réponds à la question en 3 à 8 phrases, en texte simple (pas de markdown), en t'appuyant uniquement sur les articles "
        "ci-dessous et sur le dossier s'il est fourni. Cite les articles sous la forme « article 44 du CDPF ». Si la réponse "
        f"dépend d'éléments absents, dis-le. Termine par une ligne contenant exactement {SEP}, puis 3 questions de suivi "
        "courtes, une par ligne, dans la même langue.",
        "ARTICLES :\n" + "\n".join(f"[{a.id}] (article {a.article} du {CODE_NAMES.get(a.code, a.code)}) {a.extrait}" for a in articles),
    ]
    if contexte:
        parts.append("DOSSIER DE L'UTILISATEUR (résumé) :\n" + str(contexte)[:6000])
    if historique:
        parts.append("CONVERSATION :\n" + "\n".join(f"{e.role} : {e.texte}" for e in historique[-6:]))
    parts.append(f"QUESTION : {question}")

    yield {"type": "articles", "articles": [a.model_dump() for a in articles]}
    try:
        chunks = llm.stream_text("\n\n".join(parts))
    except llm.LLMUnavailable:
        # no streaming (offline, Gemini backup…): send the regular answer in one piece
        full = answer(question, langue, historique, contexte)
        yield {"type": "delta", "text": full.reponse}
        yield {"type": "fin", "suggestions": full.suggestions, "mode": full.mode}
        return

    pending, tail, in_suggestions = "", "", False
    try:
        for chunk in chunks:
            if in_suggestions:
                tail += chunk
                continue
            pending += chunk
            if SEP in pending:
                before, _, after = pending.partition(SEP)
                if before:
                    yield {"type": "delta", "text": before}
                tail, in_suggestions, pending = after, True, ""
            elif len(pending) > 1:
                # keep the last character back: it may be the start of the separator
                yield {"type": "delta", "text": pending[:-1]}
                pending = pending[-1:]
    except Exception as e:  # stream cut mid-way: close cleanly with what was sent
        yield {"type": "delta", "text": f"\n[réponse interrompue : {e}]"}
    if pending and not in_suggestions:
        yield {"type": "delta", "text": pending}
    suggestions = [s.strip(" -•\t") for s in tail.splitlines() if s.strip(" -•\t")][:3]
    yield {"type": "fin", "suggestions": suggestions or SUGGESTIONS.get(langue, SUGGESTIONS["fr"]), "mode": "ia"}
