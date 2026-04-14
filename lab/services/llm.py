import requests
from django.conf import settings


class LLMError(RuntimeError):
    pass


def chat_completion(messages, temperature=None, timeout=None):
    response = requests.post(
        f"{settings.LM_STUDIO_BASE_URL.rstrip('/')}/v1/chat/completions",
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {settings.LM_STUDIO_API_KEY}',
        },
        json={
            'model': settings.LM_STUDIO_MODEL,
            'temperature': settings.LM_STUDIO_TEMPERATURE if temperature is None else temperature,
            'messages': messages,
            'stream': False,
        },
        timeout=timeout or settings.LM_STUDIO_CHAT_TIMEOUT,
    )
    try:
        payload = response.json()
    except ValueError as exc:
        raise LLMError('The model endpoint returned malformed JSON.') from exc
    if response.status_code >= 400:
        raise LLMError(str(payload))
    return payload


def extract_content(payload):
    return str(payload.get('choices', [{}])[0].get('message', {}).get('content', '')).strip()
