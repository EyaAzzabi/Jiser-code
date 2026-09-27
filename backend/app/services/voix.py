"""Read explanations aloud (text-to-speech) in French, English or Modern Standard Arabic.

1. The text is adapted for listening in the target language by the LLM (translation). A text
   already in the target language (French to French, Arabic to Arabic) is read as it is.
2. OpenAI's TTS model turns it into MP3, with a spoken-style instruction per language.
Results are cached on disk: the same explanation is only synthesised once.
"""
from __future__ import annotations

import hashlib
import logging

from pydantic import BaseModel

from ..config import CACHE_DIR, OPENAI_API_KEY
from . import llm, securite

log = logging.getLogger("jiser.voix")

TTS_MODEL = "gpt-4o-mini-tts"
MAX_CHARS = 3500
VOICES = {
    "fr": ("coral", "Parle en français, d'une voix calme, claire et bienveillante, comme un conseiller fiscal qui explique simplement."),
    "en": ("coral", "Speak in clear, calm and friendly English, like an advisor explaining simply."),
    "ar": ("coral", "تحدّث باللغة العربية الفصحى، بصوت هادئ وواضح ومطمئن، كمستشار جبائي يشرح ببساطة. "
                    "Speak Modern Standard Arabic with clear, correct pronunciation."),
}


class VoixIndisponible(RuntimeError):
    pass


class _Script(BaseModel):
    texte: str


def _prepare(texte: str, source: str, cible: str) -> str:
    texte = texte.strip()[:MAX_CHARS]
    if cible == source:
        return texte
    consigne = {
        "fr": "Réécris ce texte en français clair, prêt à être lu à voix haute. Garde tous les faits, montants, dates et articles.",
        "en": "Translate this text into clear, natural English, ready to be read aloud. Keep every fact, amount, date and "
              "article number (e.g. « article 44 du CDPF » becomes « article 44 of the CDPF »).",
        "ar": "Traduis ce texte en arabe standard moderne (الفصحى), clair, prêt à être lu à voix haute, avec la terminologie "
              "fiscale officielle tunisienne (« الفصل 44 من مجلة الحقوق والإجراءات الجبائية »). Garde tous les faits, montants, "
              "dates et numéros d'articles. Écris les nombres en chiffres.",
    }[cible]
    try:
        return llm.parse("voix-" + cible, f"{consigne}\n\nTEXTE :\n{texte}", _Script, max_tokens=2500).texte[:MAX_CHARS]
    except llm.LLMUnavailable as e:
        raise VoixIndisponible(f"préparation du texte impossible : {e}") from e


def synthese(texte: str, source: str = "fr", cible: str = "fr") -> bytes:
    if not OPENAI_API_KEY:
        raise VoixIndisponible("La lecture vocale nécessite une clé OpenAI.")
    if cible not in VOICES:
        raise VoixIndisponible("Langue non prise en charge.")
    if not securite.ia_autorisee():
        raise VoixIndisponible("Lecture vocale désactivée : vous avez retiré votre consentement à l'IA générative.")
    texte = securite.neutraliser(texte)   # the speech service never receives names or tax IDs
    key = hashlib.sha256(f"{source}|{cible}|{texte}".encode()).hexdigest()[:24]
    path = CACHE_DIR / f"tts-{key}.mp3"
    if path.exists():
        return path.read_bytes()
    script = _prepare(texte, source, cible)
    voice, instructions = VOICES[cible]
    import openai
    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY, max_retries=2, timeout=90)
        audio = client.audio.speech.create(model=TTS_MODEL, voice=voice, input=script,
                                           instructions=instructions, response_format="mp3").content
    except openai.APIError as e:
        raise VoixIndisponible(f"synthèse vocale indisponible : {e}") from e
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_bytes(audio)
    return audio
