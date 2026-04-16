"""Tests for config module."""

import json
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from quicktrans.config import (
    DEFAULT_CONFIG,
    load_config,
    save_config,
    _validate_api_key,
    get_provider_preset,
    is_config_complete,
)


class TestConfig(unittest.TestCase):
    def test_default_config_has_required_keys(self):
        required = ["provider", "engine", "api_key", "api_url", "target_lang", "font_size"]
        for key in required:
            self.assertIn(key, DEFAULT_CONFIG)

    def test_load_config_missing_file_uses_defaults(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "config.json")
            config = load_config(path)
            self.assertEqual(config.font_size, DEFAULT_CONFIG["font_size"])
            self.assertEqual(config.target_lang, DEFAULT_CONFIG["target_lang"])
            self.assertEqual(config.provider, "deepl")

    def test_load_config_merges_with_defaults(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "config.json")
            with open(path, "w") as f:
                json.dump({"font_size": 20, "target_lang": "EN"}, f)

            config = load_config(path)
            self.assertEqual(config.font_size, 20)
            self.assertEqual(config.target_lang, "EN")
            # Default preserved
            self.assertEqual(config.popup_duration, DEFAULT_CONFIG["popup_duration"])

    def test_load_config_fills_provider_defaults(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "config.json")
            with open(path, "w") as f:
                json.dump({"provider": "openai", "api_key": "test"}, f)

            config = load_config(path)
            self.assertEqual(config.provider, "openai")
            self.assertEqual(config.engine, "openai")
            self.assertEqual(config.api_url, get_provider_preset("openai")["api_url"])
            self.assertEqual(config.model, get_provider_preset("openai")["model"])

    def test_load_config_uses_legacy_engine_field(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "config.json")
            with open(path, "w") as f:
                json.dump({"engine": "deepseek", "api_key": "test"}, f)

            config = load_config(path)
            self.assertEqual(config.provider, "deepseek")
            self.assertEqual(config.engine, "deepseek")
            self.assertEqual(config.api_url, get_provider_preset("deepseek")["api_url"])
            self.assertEqual(config.model, get_provider_preset("deepseek")["model"])

    def test_save_config_writes_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "config.json")
            save_config({"api_key": "test123"}, path)

            with open(path) as f:
                data = json.load(f)
            self.assertEqual(data["api_key"], "test123")

    def test_validate_api_key_success(self):
        with patch("quicktrans.translate.translate_text", return_value=("你好", None)):
            result = _validate_api_key("test-key", "https://api.example.com/translate")
        self.assertTrue(result)

    def test_validate_api_key_failure(self):
        with patch("quicktrans.translate.translate_text", return_value=(None, "bad key")):
            result = _validate_api_key("bad-key", "https://api.example.com/translate")
        self.assertFalse(result)

    def test_is_config_complete_requires_model_for_llm_providers(self):
        config = SimpleNamespace(
            provider="deepl",
            engine="deepl",
            api_key="test-key",
            api_url="https://api-free.deepl.com/v2/translate",
            model="",
        )
        self.assertTrue(is_config_complete(config))

        config.provider = "openai"
        config.engine = "openai"
        config.model = ""
        self.assertFalse(is_config_complete(config))

        config.model = "gpt-4.1-mini"
        self.assertTrue(is_config_complete(config))


if __name__ == "__main__":
    unittest.main()
