"""Retrieval over the tax codes: BM25 (offline, exact words) + vector search (meaning), fused.

BM25 always runs and every hit is an exact article, so citations stay verifiable. When the legal
watch pipeline has computed article embeddings (veille.py), questions are also embedded and the two
rankings are merged by reciprocal rank fusion: a question in Arabic or with other words than the law
still finds the right article. The question is pseudonymised before being embedded.
"""
from __future__ import annotations

import json
import logging
import re
import threading
import unicodedata
from functools import lru_cache

from rank_bm25 import BM25Okapi

from ..config import LEGAL_DIR, OPENAI_API_KEY
from ..schemas import ArticleRef

log = logging.getLogger("jiser.rag")

CODE_FILES = ["cdpf", "ctva", "cirppis"]
STOPWORDS = set("""au aux avec ce ces dans de des du elle en et eux il ils je la le les leur lui ma mais me même mes
moi mon ne nos notre nous on ou par pas pour qu que qui sa se ses son sur ta te tes toi ton tu un une vos votre
vous est sont été être a ont cette cet celle celui dont lorsque selon présent code article articles ainsi loi
note modifié ajouté portant finances année n°""".split())
RRF_K = 60


def _norm(text: str) -> list[str]:
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    tokens = re.findall(r"[a-z]{3,}", text)
    return [t.rstrip("s") for t in tokens if t not in STOPWORDS]


@lru_cache(maxsize=512)
def _embed_query(query: str):
    import numpy as np
    import openai

    from . import securite
    table: dict[str, str] = {}
    client = openai.OpenAI(api_key=OPENAI_API_KEY, max_retries=1, timeout=15)
    v = np.asarray(client.embeddings.create(model="text-embedding-3-small", input=securite.masquer(query, table)).data[0].embedding,
                   dtype=np.float32)
    return v / (np.linalg.norm(v) + 1e-9)


class LegalIndex:
    def __init__(self) -> None:
        self.articles: list[dict] = []
        for code in CODE_FILES:
            path = LEGAL_DIR / f"{code}.json"
            if path.exists():
                self.articles += json.loads(path.read_text(encoding="utf-8"))
        self.by_id = {a["id"]: a for a in self.articles}
        self.bm25 = BM25Okapi([_norm(a["text"] + " " + a.get("heading", "")) for a in self.articles])
        self.vecteurs = None
        self.vec_ids: list[str] = []
        emb = LEGAL_DIR / "embeddings.npz"
        if emb.exists():
            try:
                import numpy as np
                z = np.load(emb, allow_pickle=False)
                self.vec_ids, self.vecteurs = z["ids"].tolist(), z["vecteurs"]
            except Exception as e:
                log.warning("embeddings unreadable: %s", e)

    @property
    def hybride(self) -> bool:
        return self.vecteurs is not None and bool(OPENAI_API_KEY)

    @staticmethod
    def to_ref(a: dict, max_chars: int = 600) -> ArticleRef:
        text = a["text"]
        return ArticleRef(id=a["id"], code=a["code"], article=a["article"],
                          extrait=text if len(text) <= max_chars else text[:max_chars].rsplit(" ", 1)[0] + " …",
                          source_url=a["source_url"])

    def get(self, article_id: str) -> ArticleRef | None:
        a = self.by_id.get(article_id)
        return self.to_ref(a) if a else None

    def search(self, query: str, k: int = 3, codes: list[str] | None = None, hybride: bool = False) -> list[ArticleRef]:
        scores = self.bm25.get_scores(_norm(query))
        bm25_rank = [i for i in sorted(range(len(self.articles)), key=lambda i: scores[i], reverse=True) if scores[i] > 0]
        fusion: dict[str, float] = {}
        for r, i in enumerate(bm25_rank[:50]):
            fusion[self.articles[i]["id"]] = 1 / (RRF_K + r)
        if hybride and self.hybride:
            try:
                sims = self.vecteurs @ _embed_query(query)
                for r, j in enumerate(sims.argsort()[::-1][:50]):
                    aid = self.vec_ids[j]
                    fusion[aid] = fusion.get(aid, 0) + 1 / (RRF_K + r)
            except Exception as e:   # vector search is a bonus: BM25 alone still answers
                log.warning("vector search unavailable: %s", e)
        out = []
        for aid in sorted(fusion, key=fusion.get, reverse=True):
            a = self.by_id.get(aid)
            if a is None or (codes and a["code"] not in codes):
                continue
            out.append(self.to_ref(a))
            if len(out) == k:
                break
        return out


_verrou = threading.Lock()


def get_index() -> LegalIndex:
    with _verrou:   # one load only, even if the startup thread and a request ask at the same time
        return _charger_index()


@lru_cache(maxsize=1)
def _charger_index() -> LegalIndex:
    return LegalIndex()


get_index.cache_clear = _charger_index.cache_clear   # used by the legal watch after a publication
