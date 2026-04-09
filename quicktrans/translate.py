"""Translation API client (DeepL)."""

from __future__ import annotations

import json
import logging
from types import SimpleNamespace
from typing import Any, Dict, Optional
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from urllib.error import URLError, HTTPError

logger: logging.Logger = logging.getLogger("quicktrans")


def translate_text(text: str, config: SimpleNamespace) -> Optional[str]:
    """Translate text using the configured engine. Returns translated text or None."""
    data: bytes = urlencode({
        "text": text,
        "target_lang": config.target_lang,
    }).encode("utf-8")

    req = Request(config.api_url, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    req.add_header("Authorization", f"DeepL-Auth-Key {config.api_key}")

    try:
        with urlopen(req, timeout=10) as resp:
            result: Dict[str, Any] = json.loads(resp.read().decode("utf-8"))
            translations: list[Dict[str, Any]] = result.get("translations", [])
            if translations:
                return translations[0].get("text", "")
    except HTTPError as e:
        logger.error("DeepL HTTP error: %s %s", e.code, e.reason)
    except URLError as e:
        logger.error("DeepL network error: %s", e.reason)
    except Exception as e:
        logger.error("DeepL unexpected error: %s", e)

    return None
