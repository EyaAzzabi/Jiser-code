"""Retrieval over the scraped tax codes (BM25, fully offline).

BM25 keeps the prototype light (no embedding model download) and every hit is an exact
article, so citations stay verifiable. A multilingual embedding index (e.g. bge-m3) can be
added later for Arabic queries.
"""
from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache

from rank_bm25 import BM25Okapi

from ..config import LEGAL_DIR
from ..schemas import ArticleRef

CODE_FILES = ["cdpf", "ctva", "cirppis"]
STOPWORDS = set("""au aux avec ce ces dans de des du elle en et eux il ils je la le les leur lui ma mais me même mes
moi mon ne nos notre nous on ou par pas pour qu que qui sa se ses son sur ta te tes toi ton tu un une vos votre
vous est sont été être a ont cette cet celle celui dont lorsque selon présent code article articles ainsi loi
note modifié ajouté portant finances année n°""".split())


def _norm(text: str) -> list[str]:
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    tokens = re.findall(r"[a-z]{3,}", text)
    return [t.rstrip("s") for t in tokens if t not in STOPWORDS]


class LegalIndex:
    def __init__(self) -> None:
        self.articles: list[dict] = []
        for code in CODE_FILES:
            path = LEGAL_DIR / f"{code}.json"
            if path.exists():
                self.articles += json.loads(path.read_text(encoding="utf-8"))
        self.by_id = {a["id"]: a for a in self.articles}
        self.bm25 = BM25Okapi([_norm(a["text"] + " " + a.get("heading", "")) for a in self.articles])

    @staticmethod
    def to_ref(a: dict, max_chars: int = 600) -> ArticleRef:
        text = a["text"]
        return ArticleRef(id=a["id"], code=a["code"], article=a["article"],
                          extrait=text if len(text) <= max_chars else text[:max_chars].rsplit(" ", 1)[0] + " …",
                          source_url=a["source_url"])

    def get(self, article_id: str) -> ArticleRef | None:
        a = self.by_id.get(article_id)
        return self.to_ref(a) if a else None

    def search(self, query: str, k: int = 3, codes: list[str] | None = None) -> list[ArticleRef]:
        scores = self.bm25.get_scores(_norm(query))
        ranked = sorted(range(len(self.articles)), key=lambda i: scores[i], reverse=True)
        out = []
        for i in ranked:
            if scores[i] <= 0:
                break
            if codes and self.articles[i]["code"] not in codes:
                continue
            out.append(self.to_ref(self.articles[i]))
            if len(out) == k:
                break
        return out


@lru_cache(maxsize=1)
def get_index() -> LegalIndex:
    return LegalIndex()
