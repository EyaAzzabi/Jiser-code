"""Read explanations aloud (text-to-speech) in French, English or Tunisian derja.

1. The text is adapted for listening in the target language by the LLM (translation to English;
   for derja, rewriting in Arabic script so the voice pronounces it like a Tunisian speaker would).
   French text going to French is read as it is.
2. OpenAI's TTS model turns it into MP3, with a spoken-style instruction per language.
Results are cached on disk: the same explanation is only synthesised once.
"""
from __future__ import annotations

import hashlib
import logging

from pydantic import BaseModel

from ..config import CACHE_DIR, OPENAI_API_KEY
from . import llm

log = logging.getLogger("jiser.voix")

TTS_MODEL = "gpt-4o-mini-tts"
MAX_CHARS = 3500
VOICES = {
    "fr": ("coral", "Parle en français, d'une voix calme, claire et bienveillante, comme un conseiller fiscal qui explique simplement."),
    "en": ("coral", "Speak in clear, calm and friendly English, like an advisor explaining simply."),
    "derja": ("coral", "Parle en dialecte tunisien (derja), avec un accent tunisien naturel, d'une voix chaleureuse et claire. "
                       "Prononce les termes juridiques français à la française."),
}


class VoixIndisponible(RuntimeError):
    pass


class _Script(BaseModel):
    texte: str


def _prepare(texte: str, source: str, cible: str) -> str:
    texte = texte.strip()[:MAX_CHARS]
    if cible == "fr" and source == "fr":
        return texte
    consigne = {
        "fr": "Réécris ce texte en français clair, prêt à être lu à voix haute. Garde tous les faits, montants, dates et articles.",
        "en": "Translate this text into clear, natural English, ready to be read aloud. Keep every fact, amount, date and "
              "article number (e.g. « article 44 du CDPF » becomes « article 44 of the CDPF »).",
        "derja": "EXCEPTION À LA RÈGLE DES CARACTÈRES LATINS : ce texte sert uniquement à une synthèse vocale, il doit donc être "
                 "écrit en caractères arabes. Réécris ce texte en derja tunisienne parlée, EN CARACTÈRES ARABES, prêt à être lu à voix haute par une voix "
                 "tunisienne. Garde tous les faits, montants, dates et numéros d'articles ; les termes juridiques peuvent rester "
                 "en français (caractères latins). Écris les nombres en chiffres.",
    }[cible]
    try:
        script = llm.parse("voix-" + cible, f"{consigne}\n\nTEXTE :\n{texte}", _Script, max_tokens=2500).texte
        if cible == "derja" and not llm.ARABIC_SCRIPT.search(script):
            # still in Latin script: the voice would mispronounce arabizi digits (3, 7, 9), so ask once more
            script = llm.parse("voix-derja-ar", "Écris ce texte tunisien en caractères arabes (et non latins), sans rien "
                                                "changer au sens, pour une synthèse vocale :\n\n" + script, _Script, max_tokens=2500).texte
        return script[:MAX_CHARS]
    except llm.LLMUnavailable as e:
        raise VoixIndisponible(f"préparation du texte impossible : {e}") from e


def synthese(texte: str, source: str = "fr", cible: str = "fr") -> bytes:
    if not OPENAI_API_KEY:
        raise VoixIndisponible("La lecture vocale nécessite une clé OpenAI.")
    if cible not in VOICES:
        raise VoixIndisponible("Langue non prise en charge.")
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
