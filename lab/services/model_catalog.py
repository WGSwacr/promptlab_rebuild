import random
from typing import List

import requests
from django.conf import settings


RANDOM_MODEL_CHOICE = '__random__'
EXCLUDED_MODEL_IDS = {'text-embedding-nomic-embed-text-v1.5'}

_MODEL_CACHE: List[str] | None = None


def _fallback_models():
    return [settings.LM_STUDIO_MODEL]


def refresh_model_catalog():
    global _MODEL_CACHE
    try:
        response = requests.get(
            f"{settings.LM_STUDIO_BASE_URL.rstrip('/')}/v1/models",
            headers={'Authorization': f'Bearer {settings.LM_STUDIO_API_KEY}'},
            timeout=settings.LM_STUDIO_CHAT_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
        models = sorted(
            {
                str(item.get('id', '')).strip()
                for item in payload.get('data', [])
                if str(item.get('id', '')).strip() and str(item.get('id', '')).strip() not in EXCLUDED_MODEL_IDS
            }
        )
        _MODEL_CACHE = models or _fallback_models()
    except Exception:
        _MODEL_CACHE = _fallback_models()
    return list(_MODEL_CACHE)


def get_model_catalog():
    if _MODEL_CACHE is None:
        return refresh_model_catalog()
    return list(_MODEL_CACHE)


def get_model_choice_options(*, include_random=True):
    choices = []
    if include_random:
        choices.append((RANDOM_MODEL_CHOICE, 'Random available model'))
    choices.extend((model_name, model_name) for model_name in get_model_catalog())
    return choices


def resolve_model_choice(model_choice):
    available_models = get_model_catalog()
    if model_choice == RANDOM_MODEL_CHOICE:
        return random.choice(available_models) if available_models else settings.LM_STUDIO_MODEL
    if model_choice:
        return model_choice
    return settings.LM_STUDIO_MODEL
