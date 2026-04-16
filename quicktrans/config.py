"""Configuration loading, defaults, and first-run setup wizard."""

from __future__ import annotations

import json
import os
from types import SimpleNamespace
from typing import Any, Dict, Optional

CONFIG_DIR: str = os.path.expanduser("~/.config/quicktrans")
CONFIG_FILE: str = os.path.join(CONFIG_DIR, "config.json")

DEFAULT_CONFIG: Dict[str, Any] = {
    "provider": "deepl",
    "engine": "deepl",
    "api_key": "",
    "api_url": "https://api-free.deepl.com/v2/translate",
    "model": "",
    "target_lang": "ZH",
    "min_drag_distance": 10,
    "min_text_length": 1,
    "popup_duration": 12,
    "font_size": 16,
    "icon_size": 44,
    "icon_dismiss_delay": 5,
    "log_max_bytes": 1048576,
    "log_backup_count": 3,
}

PROVIDER_PRESETS: Dict[str, Dict[str, str]] = {
    "deepl": {
        "label": "DeepL",
        "api_style": "deepl",
        "api_url": "https://api-free.deepl.com/v2/translate",
        "model": "",
    },
    "openai": {
        "label": "OpenAI",
        "api_style": "openai_compatible",
        "api_url": "https://api.openai.com/v1/chat/completions",
        "model": "gpt-4.1-mini",
    },
    "deepseek": {
        "label": "DeepSeek",
        "api_style": "openai_compatible",
        "api_url": "https://api.deepseek.com/chat/completions",
        "model": "deepseek-chat",
    },
    "gemini": {
        "label": "Gemini",
        "api_style": "gemini",
        "api_url": "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        "model": "gemini-2.5-flash",
    },
    "qwen": {
        "label": "Qwen / DashScope",
        "api_style": "openai_compatible",
        "api_url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        "model": "qwen-plus",
    },
    "openai_compatible": {
        "label": "OpenAI-Compatible (Custom)",
        "api_style": "openai_compatible",
        "api_url": "",
        "model": "",
    },
}

LANG_OPTIONS: Dict[str, str] = {
    "ZH": "Chinese (中文)",
    "EN": "English",
    "JA": "Japanese (日本語)",
    "KO": "Korean (한국어)",
    "DE": "German (Deutsch)",
    "FR": "French (Français)",
    "ES": "Spanish (Español)",
    "RU": "Russian (Русский)",
}


def normalize_provider(provider: Optional[str]) -> str:
    """Normalize provider names while keeping unknown labels intact."""
    value = (provider or "deepl").strip().lower()
    aliases = {
        "custom": "openai_compatible",
        "openai-compatible": "openai_compatible",
        "openai_compatible": "openai_compatible",
    }
    return aliases.get(value, value or "deepl")


def get_provider_preset(provider: Optional[str]) -> Dict[str, str]:
    """Return provider metadata or the generic OpenAI-compatible fallback."""
    return PROVIDER_PRESETS.get(
        normalize_provider(provider),
        PROVIDER_PRESETS["openai_compatible"],
    )


def is_config_complete(config: SimpleNamespace) -> bool:
    """Check whether the minimum provider configuration is present."""
    provider = normalize_provider(getattr(config, "provider", getattr(config, "engine", "deepl")))
    api_key = getattr(config, "api_key", "").strip()
    api_url = getattr(config, "api_url", "").strip()
    model = getattr(config, "model", "").strip()

    if not api_key or not api_url:
        return False

    return get_provider_preset(provider)["api_style"] == "deepl" or bool(model)


def _normalize_loaded_config(
    merged: Dict[str, Any],
    user_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Fill provider defaults while preserving explicit user overrides."""
    user_config = user_config or {}
    provider = normalize_provider(
        user_config.get("provider")
        or user_config.get("engine")
        or merged.get("provider")
        or merged.get("engine")
    )
    preset = get_provider_preset(provider)

    merged["provider"] = provider
    merged["engine"] = provider

    api_url_missing = "api_url" not in user_config or not str(user_config.get("api_url", "")).strip()
    if provider != "deepl" and preset["api_url"] and api_url_missing:
        merged["api_url"] = preset["api_url"]
    elif not str(merged.get("api_url", "")).strip() and preset["api_url"]:
        merged["api_url"] = preset["api_url"]

    model_missing = "model" not in user_config or not str(user_config.get("model", "")).strip()
    if preset["api_style"] != "deepl" and model_missing:
        merged["model"] = preset["model"]

    if preset["api_style"] == "deepl":
        merged["model"] = ""

    return merged


def _validate_api_key(
    api_key: str,
    api_url: str,
    provider: str = "deepl",
    model: str = "",
) -> bool:
    """Test the configured provider with a simple translation request."""
    from quicktrans.translate import translate_text

    probe_config = SimpleNamespace(
        provider=normalize_provider(provider),
        engine=normalize_provider(provider),
        api_key=api_key,
        api_url=api_url,
        model=model,
        target_lang="ZH",
    )
    try:
        translated, error = translate_text("hello", probe_config)
        return bool(translated) and not error
    except Exception:
        return False


def load_config(path: Optional[str] = None) -> SimpleNamespace:
    """Load config from JSON file, merging with defaults."""
    path = path or CONFIG_FILE
    merged: Dict[str, Any] = dict(DEFAULT_CONFIG)
    user_config: Dict[str, Any] = {}
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            user_config = json.load(f)
        merged.update(user_config)
    return SimpleNamespace(**_normalize_loaded_config(merged, user_config))


def save_config(config: Dict[str, Any], path: Optional[str] = None) -> None:
    """Save config dict to JSON file."""
    path = path or CONFIG_FILE
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
        f.write("\n")


def first_run_wizard() -> SimpleNamespace:
    """Interactive setup wizard for first-time users."""
    print("=" * 50)
    print("  QuickTrans — First-Time Setup")
    print("=" * 50)
    print()
    print("QuickTrans translates selected text on your Mac.")
    print("Choose a translation provider or LLM endpoint first.")
    print()

    provider_keys: list[str] = list(PROVIDER_PRESETS.keys())
    print("Provider:")
    for i, key in enumerate(provider_keys, 1):
        marker = " (default)" if key == "deepl" else ""
        print(f"  {i}. {key} — {PROVIDER_PRESETS[key]['label']}{marker}")

    provider_choice = input(f"Choose [1-{len(provider_keys)}] (default: 1): ").strip()
    if provider_choice.isdigit() and 1 <= int(provider_choice) <= len(provider_keys):
        provider = provider_keys[int(provider_choice) - 1]
    else:
        provider = "deepl"

    preset = get_provider_preset(provider)

    api_key: str = ""
    api_url: str = preset["api_url"]
    model: str = preset["model"]
    while True:
        api_key = input(f"Enter your {preset['label']} API key: ").strip()
        if not api_key:
            print("API key cannot be empty.")
            continue

        if provider == "deepl" and api_key.endswith(":fx"):
            api_url = "https://api-free.deepl.com/v2/translate"
        elif provider == "deepl":
            api_url = "https://api.deepl.com/v2/translate"

        if provider == "openai_compatible":
            api_url = input("Enter the full chat/completions endpoint URL: ").strip()
            model = input("Enter the model name: ").strip()
            if not api_url or not model:
                print("Custom compatible mode needs both endpoint URL and model.")
                continue
        elif preset["api_style"] != "deepl":
            model_input = input(f"Model [{model}]: ").strip()
            if model_input:
                model = model_input

        print("Validating API config...", end=" ", flush=True)
        if _validate_api_key(api_key, api_url, provider=provider, model=model):
            print("OK")
            break

        print("FAILED")
        print("Could not connect with this configuration. Please check and try again.")

    # Target language
    print()
    print("Target language (translate INTO):")
    lang_keys: list[str] = list(LANG_OPTIONS.keys())
    for i, key in enumerate(lang_keys, 1):
        marker = " (default)" if key == "ZH" else ""
        print(f"  {i}. {key} — {LANG_OPTIONS[key]}{marker}")

    choice: str = input(f"Choose [1-{len(lang_keys)}] (default: 1): ").strip()
    target_lang: str
    if choice.isdigit() and 1 <= int(choice) <= len(lang_keys):
        target_lang = lang_keys[int(choice) - 1]
    else:
        target_lang = "ZH"

    print(f"Target language: {target_lang} — {LANG_OPTIONS[target_lang]}")

    # Build and save config
    config: Dict[str, Any] = dict(DEFAULT_CONFIG)
    config["provider"] = provider
    config["engine"] = provider
    config["api_key"] = api_key
    config["api_url"] = api_url
    config["model"] = model
    config["target_lang"] = target_lang
    config = _normalize_loaded_config(config)
    save_config(config)

    print()
    print(f"Config saved to: {CONFIG_FILE}")
    print("You can edit this file to change settings.")
    print("=" * 50)
    print()

    return SimpleNamespace(**config)
