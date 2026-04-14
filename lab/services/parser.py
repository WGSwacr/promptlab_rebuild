import json
import re


JSON_BLOCK_RE = re.compile(r'```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```', re.DOTALL)


def parse_json_from_text(raw_text):
    text = raw_text.strip()
    match = JSON_BLOCK_RE.search(text)
    if match:
        text = match.group(1).strip()
    if '{' in text:
        text = text[text.find('{'):]
    elif '[' in text:
        text = text[text.find('['):]
    parsed = json.loads(text)
    if isinstance(parsed, list):
        return {'items': parsed}
    if isinstance(parsed, dict):
        return parsed
    return {'value': parsed}
