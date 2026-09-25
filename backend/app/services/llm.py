"""Thin wrapper around the Claude API (Anthropic Python SDK).

* Structured outputs: `client.messages.parse(..., output_format=PydanticModel)` returns a
  validated object, so the rest of the code never parses free text.
* Disk cache: identical requests are answered from data/cache/ (saves credits during demos).
* Offline mode: when there is no API key, JISER_OFFLINE=1, or the call fails, `available()`
  is False / calls raise LLMUnavailable and callers use their rule-based fallback.
"""
from __future__ import annotations

import hashlib
import json
import logging
from typing import TypeVar

import anthropic
from pydantic import BaseModel

from ..config import ANTHROPIC_API_KEY, CACHE_DIR, LLM_MODEL, OFFLINE

log = logging.getLogger("jiser.llm")
T = TypeVar("T", bound=BaseModel)

SYSTEM_PROMPT = (
    "Tu es l'assistant fiscal de JISER, une plateforme tunisienne qui aide les entreprises et "
    "l'administration fiscale à traiter les notifications de redressement. Tu t'appuies uniquement "
    "sur les articles de loi fournis dans la demande et tu cites leurs numéros. Si une information "
    "manque, dis-le au lieu de l'inventer. Tu écris en français clair, sans jargon inutile, pour un "
    "chef d'entreprise qui n'est pas juriste. Tu ne donnes pas de conseil définitif : tu rappelles "
    "qu'un professionnel doit relire."
)


class LLMUnavailable(RuntimeError):
    pass


_client: anthropic.Anthropic | None = None
# Set when the API answers with a non-retryable account error (e.g. no credit left), so the
# app switches to offline mode for the rest of the session instead of failing on every call.
_disabled_reason: str | None = None


def available() -> bool:
    return not OFFLINE and _disabled_reason is None


def status() -> dict:
    if OFFLINE:
        return {"ia": False, "raison": "Mode hors ligne (pas de clé API ou JISER_OFFLINE=1)"}
    if _disabled_reason:
        return {"ia": False, "raison": _disabled_reason}
    return {"ia": True, "modele": LLM_MODEL}


def probe() -> None:
    """Cheap startup check (a few tokens) so the UI shows the real AI status from the first page."""
    if not available():
        return
    try:
        _get_client().messages.create(model=LLM_MODEL, max_tokens=16, thinking={"type": "disabled"},
                                      messages=[{"role": "user", "content": "ok"}])
    except (anthropic.AuthenticationError, anthropic.PermissionDeniedError):
        _disable("Clé API refusée")
    except anthropic.BadRequestError as e:
        if "credit balance" in str(e):
            _disable("Crédit API épuisé : mode hors ligne")
    except anthropic.APIError as e:
        log.warning("LLM probe failed: %s", e)


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY, max_retries=2, timeout=90)
    return _client


def _disable(reason: str) -> None:
    global _disabled_reason
    _disabled_reason = reason
    log.warning("LLM disabled: %s", reason)


def _cache_path(kind: str, payload: dict):
    key = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()[:24]
    return CACHE_DIR / f"{kind}-{key}.json"


def parse(kind: str, prompt: list[dict] | str, schema: type[T], max_tokens: int = 8000) -> T:
    """Ask Claude for a structured answer validated against `schema`."""
    if not available():
        raise LLMUnavailable("offline mode")
    content = prompt if isinstance(prompt, list) else [{"type": "text", "text": prompt}]
    cacheable = all(block.get("type") == "text" for block in content)
    path = _cache_path(kind, {"m": LLM_MODEL, "c": content, "s": schema.__name__}) if cacheable else None
    if path and path.exists():
        return schema.model_validate_json(path.read_text(encoding="utf-8"))
    try:
        response = _get_client().messages.parse(
            model=LLM_MODEL,
            max_tokens=max_tokens,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": content}],
            output_format=schema,
        )
    except anthropic.APIConnectionError as e:
        raise LLMUnavailable(f"connexion impossible : {e}") from e
    except anthropic.RateLimitError as e:
        raise LLMUnavailable("limite de requêtes atteinte") from e
    except (anthropic.AuthenticationError, anthropic.PermissionDeniedError) as e:
        _disable("Clé API refusée")
        raise LLMUnavailable("clé API refusée") from e
    except anthropic.BadRequestError as e:
        if "credit balance" in str(e):
            _disable("Crédit API épuisé : mode hors ligne")
        raise LLMUnavailable(f"requête refusée : {e.message}") from e
    except anthropic.APIStatusError as e:
        raise LLMUnavailable(f"erreur API {e.status_code}") from e
    if response.stop_reason == "refusal" or response.parsed_output is None:
        raise LLMUnavailable(f"réponse inexploitable (stop_reason={response.stop_reason})")
    result = response.parsed_output
    if path:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(result.model_dump_json(), encoding="utf-8")
    return result
