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


def translate_text(text: str, config: SimpleNamespace) -> tuple[Optional[str], Optional[str]]:
    """Translate text using the configured engine.
    Returns (translated_text, error_message). One of them will be None.
    """
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
                return translations[0].get("text", ""), None
    except HTTPError as e:
        logger.error("DeepL HTTP error: %s %s", e.code, e.reason)
        if e.code == 403:
            return None, "API Key 无效，请检查配置"
        elif e.code == 456:
            return None, "DeepL 额度已用完"
        else:
            return None, f"翻译服务错误 ({e.code})"
    except URLError as e:
        logger.error("DeepL network error: %s", e.reason)
        return None, "网络连接失败，请检查网络"
    except Exception as e:
        logger.error("DeepL unexpected error: %s", e)
        return None, "翻译失败，请重试"

    return None, "翻译结果为空"
