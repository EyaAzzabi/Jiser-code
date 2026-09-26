"""Replace the CDPF legal base with the official 2024 text published by the Ministry of Finance.

Source: « Code des droits et procédures fiscaux », édition 2024, ministère des Finances,
Direction Générale des Études et de la Législation Fiscales (PDF distributed on jibaya.tn).

Usage:
    python scripts/import_cdpf_officiel.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import requests
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
URL = "https://jibaya.tn/wp-content/uploads/2024/07/Code-des-droits-et-procedures-fiscaux-2024.pdf"
PDF = ROOT / "data" / "sources" / "CDPF_2024.pdf"
OUT = ROOT / "data" / "legal" / "cdpf.json"
NAME = "Code des droits et procédures fiscaux (édition officielle 2024)"

SUFFIX = r"(?:bis|ter|quater|quinquies|sexies|septies|octies|nonies|decies)"
# "Article 44 " or "Article 44 bis " at the start of an article: followed by an upper-case letter,
# a parenthesis (a footnote mark) or a dash; references in sentences are lower-case "l'article 44".
ART = re.compile(rf"(?<![’'])\bArticle (\d{{1,3}}(?: {SUFFIX})?)\s+(?=[A-ZÀ-Ý(«\-–])")
HEADING = re.compile(r"\b(TITRE|CHAPITRE|SECTION|Titre|Chapitre|Section|Sous-section)\s+[IVXLC\d]+[^.]{0,120}?(?= [A-Z][a-zé])")


def clean(text: str) -> str:
    t = re.sub(r"\s*\n\s*", " ", text)
    t = re.sub(r"(\w) - (\w)", r"\1-\2", t)
    return re.sub(r"\s{2,}", " ", t)


def parse_pdf(data: bytes) -> list[dict]:
    """Official CDPF PDF -> list of articles (also used by the legal watch pipeline, veille.py)."""
    import io
    text = clean("\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(data)).pages))
    matches = list(ART.finditer(text))
    # The code's articles appear once, in increasing order. Annexed laws reuse the same numbers
    # (their "Article 43" is not the code's): accept an article only if it keeps the order going.
    best: dict[str, str] = {}
    last = 0
    for i, m in enumerate(matches):
        num = m.group(1).lower()
        n = int(num.split()[0])
        body = text[m.end(): matches[i + 1].start() if i + 1 < len(matches) else len(text)].strip()
        body = re.sub(r"\s\d{1,3}\s*$", "", body)          # trailing page number
        if len(body) < 40 or num in best or not (last <= n <= last + 3):
            continue
        best[num] = body
        last = n
    order = lambda n: (int(n.split()[0]), n)
    return [{"id": f"cdpf-art-{n.replace(' ', '-')}", "code": "cdpf", "code_name": NAME, "article": n,
             "heading": "", "text": best[n][:6000], "source_url": URL} for n in sorted(best, key=order)]


def main() -> None:
    PDF.parent.mkdir(parents=True, exist_ok=True)
    if not PDF.exists():
        PDF.write_bytes(requests.get(URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=60).content)
    articles = parse_pdf(PDF.read_bytes())
    OUT.write_text(json.dumps(articles, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(articles)} articles written to {OUT}")


if __name__ == "__main__":
    main()
