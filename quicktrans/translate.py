"""Translation API client with multiple provider backends."""

from __future__ import annotations

import json
import logging
from types import SimpleNamespace
from typing import Any, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

logger: logging.Logger = logging.getLogger("quicktrans")

LANGUAGE_NAMES: Dict[str, str] = {
    "ZH": "Chinese",
    "EN": "English",
    "JA": "Japanese",
    "KO": "Korean",
    "DE": "German",
    "FR": "French",
    "ES": "Spanish",
    "RU": "Russian",
}

PROVIDER_STYLES: Dict[str, str] = {
    "deepl": "deepl",
    "openai": "openai_compatible",
    "deepseek": "openai_compatible",
    "qwen": "openai_compatible",
    "gemini": "gemini",
    "openai_compatible": "openai_compatible",
}


def translate_text(text: str, config: SimpleNamespace) -> tuple[Optional[str], Optional[str]]:
    """Translate text using the configured provider.

    Returns (translated_text, error_message). One of them will be None.
    """
    provider = _normalize_provider(getattr(config, "provider", getattr(config, "engine", "deepl")))
    style = PROVIDER_STYLES.get(provider, "openai_compatible")

    if not text.strip():
        return None, "翻译内容为空"

    try:
        if style == "deepl":
            return _translate_with_deepl(text, config)
        if style == "gemini":
            return _translate_with_gemini(text, config)
        return _translate_with_openai_compatible(text, config, provider)
    except HTTPError as e:
        return _handle_http_error(e, provider)
    except URLError as e:
        logger.error("%s network error: %s", provider, e.reason)
        return None, "网络连接失败，请检查网络"
    except Exception as e:
        logger.error("%s unexpected error: %s", provider, e)
        return None, "翻译失败，请重试"


def _translate_with_deepl(
    text: str,
    config: SimpleNamespace,
) -> tuple[Optional[str], Optional[str]]:
    body = _encode_json_or_form(
        {"text": [text], "target_lang": config.target_lang},
        form_encoded=True,
    )
    req = Request(_require_api_url(config), data=body, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    req.add_header("Authorization", f"DeepL-Auth-Key {_require_api_key(config)}")

    result = _request_json(req)
    translations = result.get("translations", [])
    if translations:
        translated = translations[0].get("text", "").strip()
        if translated:
            return translated, None
    return None, "翻译结果为空"


def _translate_with_openai_compatible(
    text: str,
    config: SimpleNamespace,
    provider: str,
) -> tuple[Optional[str], Optional[str]]:
    api_url = _normalize_openai_compatible_url(_require_api_url(config))
    model = _require_model(config)
    target_language = _language_name(config.target_lang)
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a translation engine. Return only the translated text. "
                    "Preserve line breaks, numbering, and formatting."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Translate the following text into {target_language}. "
                    "Do not explain. Output translation only.\n\n"
                    f"{text}"
                ),
            },
        ],
    }
    req = Request(api_url, data=_encode_json_or_form(payload), method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {_require_api_key(config)}")

    result = _request_json(req)
    choices = result.get("choices", [])
    if not choices:
        return None, "翻译结果为空"

    message = choices[0].get("message", {})
    translated = _extract_text_content(message.get("content")).strip()
    if translated:
        return translated, None

    logger.error("%s empty response payload: %s", provider, result)
    return None, "翻译结果为空"


def _translate_with_gemini(
    text: str,
    config: SimpleNamespace,
) -> tuple[Optional[str], Optional[str]]:
    model = _require_model(config)
    api_url = _require_api_url(config).format(model=model)
    target_language = _language_name(config.target_lang)
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": (
                            "You are a translation engine. Return only the translated text. "
                            "Preserve line breaks, numbering, and formatting.\n\n"
                            f"Translate the following text into {target_language}. "
                            "Do not explain. Output translation only.\n\n"
                            f"{text}"
                        )
                    }
                ]
            }
        ]
    }
    req = Request(api_url, data=_encode_json_or_form(payload), method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("x-goog-api-key", _require_api_key(config))

    result = _request_json(req)
    candidates = result.get("candidates", [])
    if not candidates:
        return None, "翻译结果为空"

    translated = _extract_gemini_text(candidates[0]).strip()
    if translated:
        return translated, None

    return None, "翻译结果为空"


def _request_json(req: Request) -> Dict[str, Any]:
    with urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _encode_json_or_form(payload: Dict[str, Any], form_encoded: bool = False) -> bytes:
    if form_encoded:
        from urllib.parse import urlencode

        normalized: Dict[str, Any] = {}
        for key, value in payload.items():
            normalized[key] = value[0] if isinstance(value, list) and len(value) == 1 else value
        return urlencode(normalized).encode("utf-8")

    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def _extract_text_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text")
                if text:
                    parts.append(str(text))
        return "".join(parts)
    return ""


def _extract_gemini_text(candidate: Dict[str, Any]) -> str:
    content = candidate.get("content", {})
    parts = content.get("parts", [])
    texts = []
    for part in parts:
        text = part.get("text")
        if text:
            texts.append(str(text))
    return "".join(texts)


def _normalize_provider(provider: str) -> str:
    return (provider or "deepl").strip().lower().replace("-", "_")


def _normalize_openai_compatible_url(api_url: str) -> str:
    if "chat/completions" in api_url:
        return api_url

    parsed = urlparse(api_url)
    path = parsed.path.rstrip("/")
    if not path:
        path = "/chat/completions"
    elif path.endswith("/v1") or path.endswith("/v4"):
        path = f"{path}/chat/completions"
    else:
        path = f"{path}/chat/completions"

    return parsed._replace(path=path).geturl()


def _language_name(target_lang: str) -> str:
    return LANGUAGE_NAMES.get(target_lang.upper(), target_lang.upper())


def _require_api_key(config: SimpleNamespace) -> str:
    api_key = getattr(config, "api_key", "").strip()
    if not api_key:
        raise ValueError("Missing API key")
    return api_key


def _require_api_url(config: SimpleNamespace) -> str:
    api_url = getattr(config, "api_url", "").strip()
    if not api_url:
        raise ValueError("Missing API URL")
    return api_url


def _require_model(config: SimpleNamespace) -> str:
    model = getattr(config, "model", "").strip()
    if not model:
        raise ValueError("Missing model name")
    return model


def _provider_display_name(provider: str) -> str:
    names = {
        "deepl": "DeepL",
        "openai": "OpenAI",
        "deepseek": "DeepSeek",
        "gemini": "Gemini",
        "qwen": "Qwen",
        "openai_compatible": "兼容模型",
    }
    return names.get(provider, provider)


def _handle_http_error(
    error: HTTPError,
    provider: str,
) -> tuple[Optional[str], Optional[str]]:
    body = ""
    try:
        body = error.read().decode("utf-8")
    except Exception:
        body = ""

    logger.error("%s HTTP error: %s %s %s", provider, error.code, error.reason, body[:300])

    if provider == "deepl":
        if error.code == 403:
            return None, "API Key 无效，请检查配置"
        if error.code == 456:
            return None, "DeepL 额度已用完"
        return None, f"翻译服务错误 ({error.code})"

    if error.code in (401, 403):
        return None, f"{_provider_display_name(provider)} API Key 无效，请检查配置"
    if error.code == 429:
        return None, f"{_provider_display_name(provider)} 请求过于频繁，请稍后再试"
    if error.code == 400:
        return None, f"{_provider_display_name(provider)} 请求参数无效，请检查模型与接口地址"
    return None, f"翻译服务错误 ({error.code})"
