"""LLM access for JISER, with interchangeable providers.

* OpenAI — main provider when OPENAI_API_KEY is set (structured outputs via `chat.completions.parse`).
* Gemini (Google AI Studio) — free tier (Flash models); main provider otherwise, and automatic backup.
* Claude (Anthropic) — optional, via structured outputs (`messages.parse`).

Callers use one function, `parse(kind, content, schema)`, and always get a validated Pydantic
object. Content blocks use one neutral shape: {"type": "text", "text": ...} or
{"type": "image", "media_type": ..., "data": <base64>}.

Also: a disk cache for identical text requests, and a circuit breaker that switches the app to
offline mode (rules + ML only) after a non-retryable account error.
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import re
import time
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from ..config import (ANTHROPIC_API_KEY, ANTHROPIC_MODEL, CACHE_DIR, GEMINI_API_KEY, GEMINI_MODEL,
                      LLM_PROVIDER, OFFLINE, OPENAI_API_KEY, OPENAI_MODEL)

log = logging.getLogger("jiser.llm")
T = TypeVar("T", bound=BaseModel)

SYSTEM_PROMPT = (
    "Tu es l'assistant fiscal de JISER, une plateforme tunisienne qui aide les entreprises et "
    "l'administration fiscale à traiter les notifications de redressement. Tu t'appuies uniquement "
    "sur les articles de loi et les faits fournis dans la demande et tu cites les numéros d'articles. "
    "Si une information manque, dis-le au lieu de l'inventer. Tu écris clairement, sans jargon inutile, "
    "pour un chef d'entreprise qui n'est pas juriste. Quand on te demande le tunisien (derja), écris en "
    "derja tunisienne UNIQUEMENT en caractères latins (arabizi : 3, 7, 9, 5 pour ع ح ق خ ; ex. « lazmek tjeweb "
    "9bal 30 jour ») — aucun caractère arabe — en gardant les termes juridiques en français. "
    "Tu rappelles qu'un professionnel doit relire avant toute décision."
)


class LLMUnavailable(RuntimeError):
    pass


# provider -> reason, for providers switched off after a non-retryable account error
_disabled: dict[str, str] = {}
_openai_client = None
_gemini_client = None
_gemini_model: str | None = GEMINI_MODEL or None
_anthropic_client = None
GEMINI_FALLBACKS = ["gemini-3.5-flash", "gemini-flash-latest", "gemini-2.5-flash"]


def _providers() -> list[str]:
    """Main provider first, then Gemini as backup when its key is set."""
    chain = [LLM_PROVIDER]
    if LLM_PROVIDER != "gemini" and GEMINI_API_KEY:
        chain.append("gemini")
    return [p for p in chain if p not in _disabled]


def available() -> bool:
    return not OFFLINE and bool(_providers())


def _model_of(provider: str) -> str | None:
    return {"openai": OPENAI_MODEL, "gemini": _gemini_model, "anthropic": ANTHROPIC_MODEL}.get(provider)


def status() -> dict:
    if OFFLINE:
        return {"ia": False, "raison": "Aucune clé d'IA configurée : mode hors ligne (règles + modèle ML)"}
    chain = _providers()
    if not chain:
        return {"ia": False, "raison": " ; ".join(_disabled.values())}
    return {"ia": True, "fournisseur": chain[0], "modele": _model_of(chain[0]),
            "secours": chain[1] if len(chain) > 1 else None}


def _disable(reason: str, provider: str = LLM_PROVIDER) -> None:
    _disabled[provider] = reason
    log.warning("LLM provider %s disabled: %s", provider, reason)


# ---- OpenAI ---------------------------------------------------------------------------------

def _openai_parse(content: list[dict], schema: type[T], max_tokens: int) -> T:
    import openai
    global _openai_client
    if _openai_client is None:
        _openai_client = openai.OpenAI(api_key=OPENAI_API_KEY, max_retries=2, timeout=120)
    parts = [{"type": "image_url", "image_url": {"url": f"data:{b['media_type']};base64,{b['data']}"}}
             if b["type"] == "image" else {"type": "text", "text": b["text"]} for b in content]
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": parts}]
    # reasoning models spend part of the completion budget thinking: leave headroom, keep effort low for speed
    kwargs = {"model": OPENAI_MODEL, "messages": messages, "max_completion_tokens": max_tokens + 6000}
    if OPENAI_MODEL.startswith(("gpt-5", "o")):
        kwargs["reasoning_effort"] = "low"
    try:
        try:
            resp = _openai_client.chat.completions.parse(response_format=schema, **kwargs)
            msg = resp.choices[0].message
            if msg.refusal:
                raise LLMUnavailable("requête refusée par le modèle")
            if msg.parsed is not None:
                return msg.parsed
            raise LLMUnavailable("réponse vide")
        except openai.BadRequestError as e:
            if "schema" not in str(e).lower() and "response_format" not in str(e).lower():
                raise
            # schema outside OpenAI's strict subset: plain JSON mode with the schema as instructions
            hint = "Réponds uniquement en JSON valide conforme à ce schéma :\n" + json.dumps(schema.model_json_schema(), ensure_ascii=False)
            messages[0] = {"role": "system", "content": SYSTEM_PROMPT + "\n" + hint}
            resp = _openai_client.chat.completions.create(response_format={"type": "json_object"}, **kwargs)
            return schema.model_validate_json(resp.choices[0].message.content or "")
    except (openai.AuthenticationError, openai.PermissionDeniedError) as e:
        _disable("Clé OpenAI refusée", "openai")
        raise LLMUnavailable("clé OpenAI refusée") from e
    except openai.RateLimitError as e:
        if "quota" in str(e).lower():
            _disable("Crédit OpenAI épuisé", "openai")
        raise LLMUnavailable("limite OpenAI atteinte") from e
    except openai.APIError as e:
        raise LLMUnavailable(f"erreur OpenAI : {e}") from e
    except ValidationError as e:
        raise LLMUnavailable("réponse OpenAI non conforme au schéma") from e


# ---- Gemini ---------------------------------------------------------------------------------

def _gemini():
    global _gemini_client
    if _gemini_client is None:
        from google import genai
        _gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    return _gemini_client


def _pick_gemini_model() -> str:
    """Choose the newest general-purpose Flash model this key can use (free tier)."""
    names = []
    for m in _gemini().models.list():
        name = m.name.removeprefix("models/")
        actions = getattr(m, "supported_actions", None) or []
        if "generateContent" in actions and "flash" in name and not re.search(r"lite|image|tts|live|audio|embed|exp", name):
            names.append(name)
    if not names:
        raise LLMUnavailable("aucun modèle Gemini Flash disponible pour cette clé")

    def version(n: str) -> tuple:
        nums = re.findall(r"\d+(?:\.\d+)?", n)
        return (float(nums[0]) if nums else 0, "preview" not in n, -len(n))
    return sorted(names, key=version, reverse=True)[0]


def _gemini_parse(content: list[dict], schema: type[T], max_tokens: int) -> T:
    from google.genai import errors, types
    global _gemini_model
    parts = []
    for block in content:
        if block["type"] == "image":
            parts.append(types.Part.from_bytes(data=base64.b64decode(block["data"]), mime_type=block["media_type"]))
        else:
            parts.append(types.Part.from_text(text=block["text"]))
    # Flash models "think" before answering and those tokens count against max_output_tokens: add headroom
    budget = max_tokens + 6000
    no_afc = types.AutomaticFunctionCallingConfig(disable=True)

    def call(model: str):
        try:
            config = types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT, temperature=0.3,
                                                 max_output_tokens=budget, response_mime_type="application/json",
                                                 response_schema=schema, automatic_function_calling=no_afc)
            return _gemini().models.generate_content(model=model, contents=parts, config=config)
        except (ValueError, TypeError):
            # schema feature outside Gemini's schema subset: ask for JSON matching the schema instead
            hint = "Réponds uniquement en JSON valide conforme à ce schéma :\n" + json.dumps(schema.model_json_schema(), ensure_ascii=False)
            config = types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT + "\n" + hint, temperature=0.3,
                                                 max_output_tokens=budget, response_mime_type="application/json",
                                                 automatic_function_calling=no_afc)
            return _gemini().models.generate_content(model=model, contents=parts, config=config)

    try:
        if not _gemini_model:
            _gemini_model = _pick_gemini_model()
            log.info("Gemini model: %s", _gemini_model)
    except Exception as e:
        raise LLMUnavailable(f"Gemini injoignable : {e}") from e

    # Overloaded (503/500) or rate-limited (429, per-model quota): retry on fallback Flash models
    resp, last = None, None
    attempts = [_gemini_model, _gemini_model, *GEMINI_FALLBACKS]   # the main model gets one retry
    for i, model in enumerate(attempts):
        if i == 1:
            time.sleep(2)   # short back-off: 503 "overloaded" is usually transient
        try:
            resp = call(model)
            break
        except errors.APIError as e:
            last = e
            if e.code in (401, 403) or (e.code == 400 and "API key" in str(e)):
                _disable("Clé Gemini refusée", "gemini")
                raise LLMUnavailable("clé Gemini refusée") from e
            if e.code not in (429, 500, 503, 404):
                raise LLMUnavailable(f"erreur Gemini {e.code}") from e
            log.warning("Gemini %s on %s, trying next model", e.code, model)
        except Exception as e:  # network errors, etc.
            raise LLMUnavailable(f"Gemini injoignable : {e}") from e
    if resp is None:
        raise LLMUnavailable("quota gratuit Gemini atteint, réessayez dans une minute"
                             if last is not None and last.code == 429 else "Gemini surchargé, réessayez dans un instant")
    if isinstance(getattr(resp, "parsed", None), schema):
        return resp.parsed
    try:
        return schema.model_validate_json(resp.text or "")
    except ValidationError as e:
        raise LLMUnavailable("réponse Gemini non conforme au schéma") from e


# ---- Claude ---------------------------------------------------------------------------------

def _anthropic_parse(content: list[dict], schema: type[T], max_tokens: int) -> T:
    import anthropic
    global _anthropic_client
    if _anthropic_client is None:
        _anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY, max_retries=2, timeout=90)
    blocks = [{"type": "image", "source": {"type": "base64", "media_type": b["media_type"], "data": b["data"]}}
              if b["type"] == "image" else b for b in content]
    try:
        response = _anthropic_client.messages.parse(model=ANTHROPIC_MODEL, max_tokens=max_tokens, system=SYSTEM_PROMPT,
                                                    messages=[{"role": "user", "content": blocks}], output_format=schema)
    except (anthropic.AuthenticationError, anthropic.PermissionDeniedError) as e:
        _disable("Clé Claude refusée", "anthropic")
        raise LLMUnavailable("clé refusée") from e
    except anthropic.BadRequestError as e:
        if "credit balance" in str(e):
            _disable("Crédit Claude épuisé", "anthropic")
        raise LLMUnavailable(f"requête refusée : {e.message}") from e
    except anthropic.APIError as e:
        raise LLMUnavailable(f"erreur Claude : {e}") from e
    if response.stop_reason == "refusal" or response.parsed_output is None:
        raise LLMUnavailable("réponse inexploitable")
    return response.parsed_output


# ---- Public API -----------------------------------------------------------------------------

def _cache_path(kind: str, payload: dict):
    key = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()[:24]
    return CACHE_DIR / f"{kind}-{key}.json"


ARABIC_SCRIPT = re.compile(r"[؀-ۿ]")
# last-resort transliteration to arabizi, used only if a rewrite request still leaves Arabic script
_ARABIZI = str.maketrans({
    "ا": "a", "أ": "a", "إ": "i", "آ": "a", "ب": "b", "ت": "t", "ث": "th", "ج": "j", "ح": "7", "خ": "5",
    "د": "d", "ذ": "dh", "ر": "r", "ز": "z", "س": "s", "ش": "ch", "ص": "s", "ض": "dh", "ط": "t", "ظ": "dh",
    "ع": "3", "غ": "gh", "ف": "f", "ق": "9", "ك": "k", "ل": "l", "م": "m", "ن": "n", "ه": "h", "و": "ou",
    "ي": "i", "ى": "a", "ة": "a", "ء": "2", "ؤ": "2", "ئ": "2", "،": ",", "؟": "?", "ً": "", "ٌ": "",
    "ٍ": "", "َ": "a", "ُ": "ou", "ِ": "i", "ّ": "", "ْ": "",
})


def _arabizi(model: T) -> T:
    return type(model).model_validate_json(model.model_dump_json().translate(_ARABIZI))


def parse(kind: str, prompt: list[dict] | str, schema: type[T], max_tokens: int = 8000, cache: bool = True,
          latin_only: bool = False) -> T:
    """Ask the configured LLM for a structured answer validated against `schema`.

    latin_only: for derja answers, which must be written in Latin script (arabizi). Models sometimes
    slip into Arabic script; the answer is then sent back once to be rewritten.
    """
    result = _parse(kind, prompt, schema, max_tokens, cache)
    if latin_only and ARABIC_SCRIPT.search(result.model_dump_json()):
        fix = ("Réécris exactement ce JSON en remplaçant chaque mot écrit en caractères arabes par son équivalent en "
               "derja tunisienne en caractères latins (arabizi, chiffres 3/7/9/5). Ne change rien d'autre.\n\n"
               + result.model_dump_json())
        try:
            result = _parse(kind + "-latin", fix, schema, max_tokens, cache=False)
        except LLMUnavailable:
            pass
        if ARABIC_SCRIPT.search(result.model_dump_json()):
            result = _arabizi(result)
    return result


def _parse(kind: str, prompt: list[dict] | str, schema: type[T], max_tokens: int, cache: bool) -> T:
    if not available():
        raise LLMUnavailable(status()["raison"])
    content = prompt if isinstance(prompt, list) else [{"type": "text", "text": prompt}]
    cacheable = cache and all(b["type"] == "text" for b in content)
    path = _cache_path(kind, {"c": content, "s": schema.__name__}) if cacheable else None
    if path and path.exists():
        try:
            return schema.model_validate_json(path.read_text(encoding="utf-8"))
        except ValidationError:
            pass
    handlers = {"openai": _openai_parse, "gemini": _gemini_parse, "anthropic": _anthropic_parse}
    result, errors = None, []
    for provider in _providers():   # main provider, then Gemini backup
        try:
            result = handlers[provider](content, schema, max_tokens)
            break
        except LLMUnavailable as e:
            errors.append(f"{provider} : {e}")
            log.warning("LLM %s failed (%s)", provider, e)
    if result is None:
        raise LLMUnavailable(" ; ".join(errors) or "aucun fournisseur d'IA disponible")
    if path:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(result.model_dump_json(), encoding="utf-8")
    return result


def probe() -> None:
    """Startup check so the UI shows the real AI status from the first page."""
    if not available():
        return

    class _Ping(BaseModel):
        ok: bool

    try:
        parse("probe", "Réponds ok=true.", _Ping, max_tokens=50, cache=False)
    except LLMUnavailable as e:
        log.warning("LLM probe failed: %s", e)


def stream_text(prompt: str, max_tokens: int = 2500):
    """Yield the answer as it is generated (OpenAI streaming). Raises LLMUnavailable before the
    first chunk if streaming is not possible, so the caller can fall back to a normal answer."""
    if OFFLINE or LLM_PROVIDER != "openai" or "openai" in _disabled:
        raise LLMUnavailable("streaming indisponible")
    import openai
    global _openai_client
    if _openai_client is None:
        _openai_client = openai.OpenAI(api_key=OPENAI_API_KEY, max_retries=2, timeout=120)
    kwargs = {"model": OPENAI_MODEL, "max_completion_tokens": max_tokens + 4000, "stream": True,
              "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}]}
    if OPENAI_MODEL.startswith(("gpt-5", "o")):
        kwargs["reasoning_effort"] = "low"
    try:
        stream = _openai_client.chat.completions.create(**kwargs)
    except openai.APIError as e:
        raise LLMUnavailable(f"erreur OpenAI : {e}") from e

    def gen():
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    return gen()
