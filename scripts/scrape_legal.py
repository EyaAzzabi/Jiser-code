"""Scrape public Tunisian tax codes from Jurisite Tunisie into article-level JSON.

Source: https://www.jurisitetunisie.com (robots.txt allows /tunisie/codes/).
The texts are official laws; the site is cited as the source in the app and the
synthesis note. Requests are rate-limited to stay polite.

Usage:
    python scripts/scrape_legal.py            # all configured codes
    python scripts/scrape_legal.py cdpf       # a single code
"""
from __future__ import annotations

import codecs
import json
import re
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE = "https://www.jurisitetunisie.com/tunisie/codes"
OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "legal"
def _cp1252_fallback(err: UnicodeDecodeError) -> tuple[str, int]:
    bad = err.object[err.start:err.end]
    return bad.decode("cp1252", errors="replace"), err.end


codecs.register_error("cp1252fallback", _cp1252_fallback)

HEADERS = {"User-Agent": "Mozilla/5.0 (JISER hackathon prototype; contact: equipe JISER)"}
DELAY_S = 0.4

# code id -> (folder, page prefix, human name, first page number, last page number)
CODES = {
    "cdpf": ("cdpf", "cdpf", "Code des droits et procédures fiscaux", 1000, 1200),
    "ctva": ("tva", "tva", "Code de la taxe sur la valeur ajoutée", 1000, 1200),
    "cirppis": ("cirppis", "cirppis", "Code de l'IRPP et de l'IS", 1000, 1300),
}

HEADING_RE = re.compile(r"^(Titre|Chapitre|Section|Sous-section|Paragraphe)\b", re.IGNORECASE)
FOOTER_RE = re.compile(r"\s*/\s*Codes et lois en texte int.*$")
_SUFFIX = "bis|ter|quater|quinquies|sexies|septies|octies|nonies|decies"
ARTICLE_RE = re.compile(
    # "Art. 44" at line start (separator optional), or "Article 44 -" (separator required).
    # Lower-case "article 44 du présent code" references inside sentences are not matched.
    r"(?:^|\n)[ \t]*(?:Art\.[ \t]*(?P<a>\d+(?:[ \t]*(?:" + _SUFFIX + r"))?)(?:[ \t]*\(nouveau\))?(?:[ \t]*[-–—.:])?"
    r"|(?i:article)\s+(?P<b>\d+(?:[ \t]*(?:" + _SUFFIX + r"))?)[ \t]*[-–—:.])[ \t]*"
)


def fetch(url: str) -> str | None:
    resp = requests.get(url, headers=HEADERS, timeout=20)
    if resp.status_code != 200:
        return None
    # Pages mix UTF-8 with stray Latin-1 bytes: decode UTF-8, fall back to cp1252 per bad byte.
    return resp.content.decode("utf-8", errors="cp1252fallback")


def page_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "head"]):
        tag.decompose()
    text = soup.get_text("\n")
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def split_articles(text: str, code_id: str, code_name: str, url: str, heading: str) -> tuple[list[dict], str]:
    """Split one page into articles. Returns (articles, last heading seen)."""
    matches = list(ARTICLE_RE.finditer(text))
    articles = []
    # headings that appear before the first article belong to it
    preamble = text[: matches[0].start()] if matches else text
    for line in preamble.splitlines():
        if HEADING_RE.match(line):
            heading = line
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[m.end():end].strip()
        # a heading inside the body starts the next section: cut it off and remember it
        next_heading = None
        kept = []
        for line in body.splitlines():
            if HEADING_RE.match(line) and len(line) < 200:
                next_heading = line if next_heading is None else f"{next_heading} / {line}"
                continue
            if line.startswith("Copyright") or "Jurisite Tunisie" in line:
                continue
            kept.append(line)
        body = " ".join(kept).strip()
        body = FOOTER_RE.sub("", body).strip()
        num = re.sub(r"\s+", " ", m.group("a") or m.group("b")).strip().lower()
        if body:
            articles.append({
                "id": f"{code_id}-art-{num.replace(' ', '-')}",
                "code": code_id,
                "code_name": code_name,
                "article": num,
                "heading": heading,
                "text": body,
                "source_url": url,
            })
        if next_heading:
            heading = next_heading
    return articles, heading


def scrape_code(code_id: str) -> list[dict]:
    folder, prefix, name, first, last = CODES[code_id]
    articles: list[dict] = []
    seen: set[str] = set()
    heading = ""
    misses = 0
    for n in range(first, last + 1, 5):
        url = f"{BASE}/{folder}/{prefix}{n}.htm"
        html = fetch(url)
        time.sleep(DELAY_S)
        if html is None:
            misses += 1
            if misses >= 6 and articles:  # past the end of the code
                break
            continue
        misses = 0
        page_articles, heading = split_articles(page_text(html), code_id, name, url, heading)
        for art in page_articles:
            # The first pages may hold the promulgating law, whose article numbers collide with
            # the code's own articles: the later (code) version wins.
            if art["id"] in seen:
                articles = [a for a in articles if a["id"] != art["id"]]
            seen.add(art["id"])
            articles.append(art)
        print(f"  {url}: {len(page_articles)} articles")
    return articles


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    targets = sys.argv[1:] or list(CODES)
    for code_id in targets:
        print(f"Scraping {code_id}...")
        arts = scrape_code(code_id)
        out = OUT_DIR / f"{code_id}.json"
        out.write_text(json.dumps(arts, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"-> {len(arts)} articles written to {out}")


if __name__ == "__main__":
    main()
