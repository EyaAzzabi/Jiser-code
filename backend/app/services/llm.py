"""LLM access for JISER, with two interchangeable providers.

* Gemini (Google AI Studio) — default, permanent free tier (Flash models), vision, JSON schema output.
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
                      LLM_PROVIDER, OFFLINE)

log = logging.getLogger("jiser.llm")
T = TypeVar("T", bound=BaseModel)

SYSTEM_PROMPT = (
    "Tu es l'assistant fiscal de JISER, une plateforme tunisienne qui aide les entreprises et "
    "l'administration fiscale à traiter les notifications de redressement. Tu t'appuies uniquement "
    "sur les articles de loi et les faits fournis dans la demande et tu cites les numéros d'articles. "
    "Si une information manque, dis-le au lieu de l'inventer. Tu écris clairement, sans jargon inutile, "
    "pour un chef d'entreprise qui n'est pas juriste. Quand on te demande le tunisien (derja), écris en "
    "derja tunisienne en caractères latins (ex. « lazmek tjeweb 9bal 30 jour »), en gardant les termes "
    "juridiques en français. Tu rappelles qu'un professionnel doit relire avant toute décision."
)


class LLMUnavailable(RuntimeError):
    pass


_disabled_reason: str | None = None
_gemini_client = None
_gemini_model: str | None = GEMINI_MODEL or None
_anthropic_client = None
GEMINI_FALLBACKS = ["gemini-3.5-flash", "gemini-flash-latest", "gemini-2.5-flash"]


def available() -> bool:
    return not OFFLINE and _disabled_reason is None


def status() -> dict:
    if OFFLINE:
        return {"ia": False, "raison": "Aucune clé d'IA configurée : mode hors ligne (règles + modèle ML)"}
    if _disabled_reason:
        return {"ia": False, "raison": _disabled_reason}
    model = _gemini_model if LLM_PROVIDER == "gemini" else ANTHROPIC_MODEL
    return {"ia": True, "fournisseur": LLM_PROVIDER, "modele": model}


def _disable(reason: str) -> None:
    global _disabled_reason
    _disabled_reason = reason
    log.warning("LLM disabled: %s", reason)


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
                _disable("Clé Gemini refusée")
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
        _disable("Clé Claude refusée")
        raise LLMUnavailable("clé refusée") from e
    except anthropic.BadRequestError as e:
        if "credit balance" in str(e):
            _disable("Crédit Claude épuisé")
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


def parse(kind: str, prompt: list[dict] | str, schema: type[T], max_tokens: int = 8000, cache: bool = True) -> T:
    """Ask the configured LLM for a structured answer validated against `schema`."""
    if not available():
        raise LLMUnavailable(status()["raison"])
    content = prompt if isinstance(prompt, list) else [{"type": "text", "text": prompt}]
    cacheable = cache and all(b["type"] == "text" for b in content)
    path = _cache_path(kind, {"p": LLM_PROVIDER, "c": content, "s": schema.__name__}) if cacheable else None
    if path and path.exists():
        try:
            return schema.model_validate_json(path.read_text(encoding="utf-8"))
        except ValidationError:
            pass
    result = _gemini_parse(content, schema, max_tokens) if LLM_PROVIDER == "gemini" else _anthropic_parse(content, schema, max_tokens)
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
