"""Configuration loading, defaults, and first-run setup wizard."""

from __future__ import annotations

import json
import os
import sys
from types import SimpleNamespace
from typing import Any, Dict, Optional
from urllib.request import Request, urlopen
from urllib.parse import urlencode

CONFIG_DIR: str = os.path.expanduser("~/.config/quicktrans")
CONFIG_FILE: str = os.path.join(CONFIG_DIR, "config.json")

DEFAULT_CONFIG: Dict[str, Any] = {
    "api_key": "",
    "api_url": "https://api-free.deepl.com/v2/translate",
    "engine": "deepl",
    "target_lang": "ZH",
    "min_drag_distance": 10,
    "min_text_length": 1,
    "popup_duration": 12,
    "font_size": 16,
    "icon_size": 26,
    "icon_dismiss_delay": 5,
    "log_max_bytes": 1048576,
    "log_backup_count": 3,
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


def _validate_api_key(api_key: str, api_url: str) -> bool:
    """Test the API key with a simple translation request."""
    data: bytes = urlencode({"text": "hello", "target_lang": "ZH"}).encode("utf-8")
    req = Request(api_url, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    req.add_header("Authorization", f"DeepL-Auth-Key {api_key}")
    try:
        with urlopen(req, timeout=10) as resp:
            result: Dict[str, Any] = json.loads(resp.read().decode("utf-8"))
            return bool(result.get("translations"))
    except Exception:
        return False


def load_config(path: Optional[str] = None) -> SimpleNamespace:
    """Load config from JSON file, merging with defaults."""
    path = path or CONFIG_FILE
    merged: Dict[str, Any] = dict(DEFAULT_CONFIG)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            user_config: Dict[str, Any] = json.load(f)
        merged.update(user_config)
    return SimpleNamespace(**merged)


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
    print("You need a DeepL API key (free tier available).")
    print("Get one at: https://www.deepl.com/pro-api")
    print()

    # API key
    api_key: str = ""
    api_url: str = DEFAULT_CONFIG["api_url"]
    while True:
        api_key = input("Enter your DeepL API key: ").strip()
        if not api_key:
            print("API key cannot be empty.")
            continue

        if api_key.endswith(":fx"):
            api_url = "https://api-free.deepl.com/v2/translate"
        else:
            api_url = "https://api.deepl.com/v2/translate"

        print("Validating API key...", end=" ", flush=True)
        if _validate_api_key(api_key, api_url):
            print("OK")
            break
        else:
            print("FAILED")
            print("Could not connect with this key. Please check and try again.")

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
    config["api_key"] = api_key
    config["api_url"] = api_url
    config["target_lang"] = target_lang
    save_config(config)

    print()
    print(f"Config saved to: {CONFIG_FILE}")
    print("You can edit this file to change settings.")
    print("=" * 50)
    print()

    return SimpleNamespace(**config)
