"""Tests for translate module."""

import json
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from quicktrans.translate import _normalize_openai_compatible_url, translate_text


class TestTranslate(unittest.TestCase):
    def setUp(self):
        self.deepl_config = SimpleNamespace(
            provider="deepl",
            api_key="test-api-key",
            api_url="https://api-free.deepl.com/v2/translate",
            model="",
            target_lang="ZH",
        )
        self.openai_config = SimpleNamespace(
            provider="openai",
            api_key="test-api-key",
            api_url="https://api.openai.com/v1/chat/completions",
            model="gpt-4.1-mini",
            target_lang="ZH",
        )
        self.gemini_config = SimpleNamespace(
            provider="gemini",
            api_key="test-api-key",
            api_url="https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            model="gemini-2.5-flash",
            target_lang="ZH",
        )

    @patch("quicktrans.translate.urlopen")
    def test_deepl_translate_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "translations": [{"text": "你好世界"}]
        }).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        translated, error = translate_text("Hello World", self.deepl_config)
        self.assertEqual(translated, "你好世界")
        self.assertIsNone(error)

    @patch("quicktrans.translate.urlopen")
    def test_openai_compatible_translate_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "choices": [{"message": {"content": "你好，世界"}}]
        }).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        translated, error = translate_text("Hello World", self.openai_config)
        self.assertEqual(translated, "你好，世界")
        self.assertIsNone(error)

    @patch("quicktrans.translate.urlopen")
    def test_openai_compatible_unknown_provider_uses_same_protocol(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "choices": [{"message": {"content": [{"text": "你好"}]}}]
        }).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        custom_config = SimpleNamespace(
            provider="kimi",
            api_key="test-api-key",
            api_url="https://kimi.example.com/v1",
            model="moonshot-v1-8k",
            target_lang="ZH",
        )

        translated, error = translate_text("Hello", custom_config)
        self.assertEqual(translated, "你好")
        self.assertIsNone(error)

    @patch("quicktrans.translate.urlopen")
    def test_gemini_translate_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "candidates": [{"content": {"parts": [{"text": "你好世界"}]}}]
        }).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        translated, error = translate_text("Hello World", self.gemini_config)
        self.assertEqual(translated, "你好世界")
        self.assertIsNone(error)

    def test_normalize_openai_compatible_url_adds_v1_for_bare_domain(self):
        self.assertEqual(
            _normalize_openai_compatible_url("https://api.example.com"),
            "https://api.example.com/v1/chat/completions",
        )

    def test_normalize_openai_compatible_url_adds_v1_for_base_path(self):
        self.assertEqual(
            _normalize_openai_compatible_url("https://api.example.com/compatible-mode"),
            "https://api.example.com/compatible-mode/v1/chat/completions",
        )

    def test_normalize_openai_compatible_url_preserves_versioned_path(self):
        self.assertEqual(
            _normalize_openai_compatible_url("https://api.example.com/v4"),
            "https://api.example.com/v4/chat/completions",
        )

    @patch("quicktrans.translate.urlopen")
    def test_translate_empty_response(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"translations": []}).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        translated, error = translate_text("Hello", self.deepl_config)
        self.assertIsNone(translated)
        self.assertEqual(error, "翻译结果为空")

    @patch("quicktrans.translate.urlopen")
    def test_translate_http_error(self, mock_urlopen):
        from urllib.error import HTTPError

        mock_urlopen.side_effect = HTTPError(
            "https://api.example.com", 403, "Forbidden", {}, None
        )

        translated, error = translate_text("Hello", self.deepl_config)
        self.assertIsNone(translated)
        self.assertEqual(error, "API Key 无效，请检查配置")

    @patch("quicktrans.translate.urlopen")
    def test_translate_timeout(self, mock_urlopen):
        from urllib.error import URLError

        mock_urlopen.side_effect = URLError("Timeout")

        translated, error = translate_text("Hello", self.deepl_config)
        self.assertIsNone(translated)
        self.assertEqual(error, "网络连接失败，请检查网络")


if __name__ == "__main__":
    unittest.main()
