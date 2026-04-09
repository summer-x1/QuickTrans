"""Tests for config module."""

import json
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from quicktrans.config import (
    DEFAULT_CONFIG,
    load_config,
    save_config,
    _validate_api_key,
)


class TestConfig(unittest.TestCase):
    def test_default_config_has_required_keys(self):
        required = ["api_key", "api_url", "target_lang", "font_size"]
        for key in required:
            self.assertIn(key, DEFAULT_CONFIG)

    def test_load_config_missing_file_uses_defaults(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "config.json")
            config = load_config(path)
            self.assertEqual(config.font_size, DEFAULT_CONFIG["font_size"])
            self.assertEqual(config.target_lang, DEFAULT_CONFIG["target_lang"])

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

    def test_save_config_writes_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "config.json")
            save_config({"api_key": "test123"}, path)

            with open(path) as f:
                data = json.load(f)
            self.assertEqual(data["api_key"], "test123")

    @patch("quicktrans.config.urlopen")
    def test_validate_api_key_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"translations": [{"text": "你好"}]}).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = _validate_api_key("test-key", "https://api.example.com/translate")
        self.assertTrue(result)

    @patch("quicktrans.config.urlopen")
    def test_validate_api_key_failure(self, mock_urlopen):
        mock_urlopen.side_effect = Exception("Connection failed")
        result = _validate_api_key("bad-key", "https://api.example.com/translate")
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
