"""Turn an uploaded notification (PDF, image or pasted text) into a structured Notification.

Order of attempts:
  1. PDF/text in the JISER letter format -> deterministic parser (works offline)
  2. Any other text, or an image -> Claude (structured output, vision for images)
"""
from __future__ import annotations

import base64
import io
import re

from pypdf import PdfReader

from ..schemas import Notification
from . import letter, llm

# Lines that start a new field in a letter; any other line is a wrapped continuation.
_LINE_STARTS = re.compile(
    r"^(RÉPUBLIQUE|MINISTÈRE|Direction|Centre|NOTIFICATION|Référence|Date de|Destinataire|Matricule|Activité|"
    r"Gouvernorat|Taille|Nature de|Avis de|Comptabilité|Exercices|Madame|À l'issue|Vous |CHEF N°|Impôt :|"
    r"Base légale|Méthode|Motivation|Montant en|Pénalités|RÉCAPITULATIF|Total|TOTAL|Nous vous|Le Chef|\()"
)


class ExtractionError(ValueError):
    pass


def pdf_text(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def unwrap(text: str) -> str:
    """Re-join lines that the PDF layout wrapped, so each field sits on one line."""
    out: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if out and not _LINE_STARTS.match(line):
            out[-1] = f"{out[-1]} {line}"
        else:
            out.append(line)
    return "\n".join(out)


EXTRACTION_PROMPT = (
    "Voici une notification des résultats d'une vérification fiscale tunisienne. Extrais-la dans le "
    "schéma demandé. Règles : un chef de redressement par élément redressé ; montants en dinars (nombres) ; "
    "dates au format AAAA-MM-JJ ; `type` parmi TVA_FACTURES_NON_CONFORMES, CHARGES_NON_DEDUCTIBLES, "
    "MINORATION_CA, RECONSTITUTION_CA, RETENUE_SOURCE_NON_EFFECTUEE, AVANTAGES_ENTREPRISES_LIEES ou AUTRE ; "
    "`motivation_qualite` = 'absente' si aucune justification, 'sommaire' si une phrase vague, sinon 'detaillee' ; "
    "`mention_assistance`, `mention_delai_30j` et `penalites_indiquees` sont vrais seulement si le texte le dit "
    "explicitement ; si une information n'apparaît pas, laisse le champ vide plutôt que de l'inventer."
)


def from_text(text: str) -> tuple[Notification, str]:
    text = unwrap(text)
    parsed = letter.parse(text)
    if parsed and parsed.chefs:
        return parsed, "lecture_structuree"
    if not llm.available():
        raise ExtractionError("Format non reconnu en mode hors ligne : l'extraction IA est nécessaire pour ce document.")
    try:
        return llm.parse("extract", f"{EXTRACTION_PROMPT}\n\n---\n{text[:60000]}", Notification), "ia"
    except llm.LLMUnavailable as e:
        raise ExtractionError(f"Extraction IA indisponible : {e}") from e


def from_upload(data: bytes, filename: str, content_type: str | None) -> tuple[Notification, str]:
    name = filename.lower()
    if name.endswith(".pdf") or content_type == "application/pdf":
        text = pdf_text(data)
        if text.strip():
            return from_text(text)
        raise ExtractionError("PDF sans texte (scan) : l'extraction IA par image est nécessaire.")
    if name.endswith((".txt", ".md")):
        return from_text(data.decode("utf-8", errors="replace"))
    if name.endswith((".png", ".jpg", ".jpeg", ".webp")):
        if not llm.available():
            raise ExtractionError("La lecture d'une photo nécessite l'IA (mode hors ligne actif).")
        media = "image/png" if name.endswith(".png") else "image/webp" if name.endswith(".webp") else "image/jpeg"
        content = [
            {"type": "image", "source": {"type": "base64", "media_type": media, "data": base64.b64encode(data).decode()}},
            {"type": "text", "text": EXTRACTION_PROMPT},
        ]
        try:
            return llm.parse("extract-img", content, Notification), "ia"
        except llm.LLMUnavailable as e:
            raise ExtractionError(f"Extraction IA indisponible : {e}") from e
    raise ExtractionError("Format de fichier non pris en charge (PDF, image ou texte).")
