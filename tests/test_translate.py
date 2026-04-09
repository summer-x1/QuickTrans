"""Tests for translate module."""

import json
import unittest
from unittest.mock import patch, MagicMock
from types import SimpleNamespace

from quicktrans.translate import translate_text


class TestTranslate(unittest.TestCase):
    def setUp(self):
        self.config = SimpleNamespace(
            api_key="test-api-key",
            api_url="https://api-free.deepl.com/v2/translate",
            target_lang="ZH",
        )

    @patch("quicktrans.translate.urlopen")
    def test_translate_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "translations": [{"text": "你好世界"}]
        }).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = translate_text("Hello World", self.config)
        self.assertEqual(result, "你好世界")

    @patch("quicktrans.translate.urlopen")
    def test_translate_empty_response(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"translations": []}).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = translate_text("Hello", self.config)
        self.assertIsNone(result)

    @patch("quicktrans.translate.urlopen")
    def test_translate_http_error(self, mock_urlopen):
        from urllib.error import HTTPError
        mock_urlopen.side_effect = HTTPError(
            "https://api.example.com", 403, "Forbidden", {}, None
        )

        result = translate_text("Hello", self.config)
        self.assertIsNone(result)

    @patch("quicktrans.translate.urlopen")
    def test_translate_timeout(self, mock_urlopen):
        from urllib.error import URLError
        mock_urlopen.side_effect = URLError("Timeout")

        result = translate_text("Hello", self.config)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
