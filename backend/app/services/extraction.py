"""Turn an uploaded notification (PDF, image or pasted text) into a structured Notification.

Order of attempts:
  1. PDF/text in the JISER letter format -> deterministic parser (works offline)
  2. Any other text -> LLM (structured output)
  3. Photos (one per page, HEIC included) and scanned PDFs -> vision model, all pages read together.
     Phone photos are straightened (EXIF) and resized before sending; an unreadable photo is refused
     with advice instead of producing an empty analysis.
Note: an image cannot be pseudonymised like text; the interface tells the user so (PDF = maximum privacy).
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
    "explicitement ; `mention_delai_30j` (nom historique) = vrai si la notification invite à répondre dans le délai "
    "légal, quel que soit le nombre de jours écrit (45 jours depuis 2015, 30 jours dans les anciennes versions) ; "
    "si une information n'apparaît pas, laisse le champ vide plutôt que de l'inventer."
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


IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp", ".heic", ".heif")
MAX_PAGES = 8
MAX_COTE = 2048   # longest side sent to the vision model: enough to read, much faster than a 12 MP photo


def _est_image(name: str, content_type: str | None) -> bool:
    # some phones upload "image" or "blob" without an extension: trust the content type too
    return name.endswith(IMAGE_EXT) or (content_type or "").startswith("image/")


def preparer_image(data: bytes) -> bytes:
    """Phone photo -> upright JPEG of reasonable size (EXIF rotation applied, HEIC converted)."""
    from PIL import Image, ImageOps
    try:
        import pillow_heif
        pillow_heif.register_heif_opener()
    except ImportError:
        pass
    try:
        im = Image.open(io.BytesIO(data))
        im = ImageOps.exif_transpose(im).convert("RGB")
    except Exception as e:
        raise ExtractionError("Image illisible : reprenez la photo (formats acceptés : JPG, PNG, WEBP, HEIC).") from e
    im.thumbnail((MAX_COTE, MAX_COTE))
    out = io.BytesIO()
    im.save(out, "JPEG", quality=88)
    return out.getvalue()


def pages_pdf_scanne(data: bytes) -> list[bytes]:
    """Scanned PDF (no text layer): render each page to an image for the vision model."""
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(data)
    pages = []
    try:
        for i in range(min(len(doc), MAX_PAGES)):
            out = io.BytesIO()
            doc[i].render(scale=2.0).to_pil().convert("RGB").save(out, "JPEG", quality=85)
            pages.append(out.getvalue())
    finally:
        doc.close()
    return pages


def from_images(images: list[bytes]) -> tuple[Notification, str]:
    """One notification photographed page by page: all pages are read together."""
    if not llm.available():
        raise ExtractionError("La lecture d'une photo nécessite l'IA (mode hors ligne actif).")
    if len(images) > MAX_PAGES:
        raise ExtractionError(f"{MAX_PAGES} pages au maximum par notification.")
    content = [{"type": "image", "media_type": "image/jpeg", "data": base64.b64encode(img).decode()} for img in images]
    consigne = EXTRACTION_PROMPT + (f" Les {len(images)} images sont les pages successives d'une même notification : "
                                    "combine-les." if len(images) > 1 else "")
    content.append({"type": "text", "text": consigne})
    try:
        notif = llm.parse("extract-img", content, Notification)
    except llm.LLMUnavailable as e:
        raise ExtractionError(f"Extraction IA indisponible : {e}") from e
    if not notif.chefs:
        raise ExtractionError("Aucun chef de redressement n'a pu être lu. Reprenez la photo à plat, bien éclairée, "
                              "avec toute la page visible (ajoutez chaque page de la notification).")
    return notif, "ia"


def from_uploads(fichiers: list[tuple[bytes, str, str | None]]) -> tuple[Notification, str]:
    """Several files = several pages of one notification (photos, or scanned PDFs)."""
    if len(fichiers) == 1:
        return from_upload(*fichiers[0])
    images: list[bytes] = []
    for data, name, ctype in fichiers:
        name = name.lower()
        if _est_image(name, ctype):
            images.append(preparer_image(data))
        elif name.endswith(".pdf") or ctype == "application/pdf":
            images += pages_pdf_scanne(data)
        else:
            raise ExtractionError("Pour plusieurs pages, envoyez des photos ou des PDF.")
    return from_images(images)


def from_upload(data: bytes, filename: str, content_type: str | None) -> tuple[Notification, str]:
    name = filename.lower()
    if name.endswith(".pdf") or content_type == "application/pdf":
        text = pdf_text(data)
        if text.strip():
            return from_text(text)
        return from_images(pages_pdf_scanne(data))   # scanned PDF: read the page images
    if name.endswith((".txt", ".md")) or content_type == "text/plain":
        return from_text(data.decode("utf-8", errors="replace"))
    if _est_image(name, content_type):
        return from_images([preparer_image(data)])
    raise ExtractionError("Format de fichier non pris en charge (PDF, photo ou texte).")
