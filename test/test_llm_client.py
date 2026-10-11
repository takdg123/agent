#!/usr/bin/env python3
"""
Tests for LLMClient error handling and model resolution.

Regression context: generate() used to return the *string* "Error: HTTP 404" on
failure. Callers treated it as a successful review, so every paper in
data/memory/ stored "Error: HTTP 404" as its GRB and kilonova expert review for
weeks without a single visible error.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.llm_client import LLMClient, LLMError


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = str(self._payload)

    def json(self):
        return self._payload


class TestGenerateRaises(unittest.TestCase):
    def setUp(self):
        self.client = LLMClient(model="test-model")

    def test_http_error_raises(self):
        with patch("requests.post", return_value=FakeResponse(404, {"error": "model not found"})):
            with self.assertRaises(LLMError) as ctx:
                self.client.generate("hi")
        message = str(ctx.exception)
        self.assertIn("404", message)
        self.assertIn("test-model", message)  # the model name must be in the message

    def test_timeout_raises(self):
        import requests

        with patch("requests.post", side_effect=requests.exceptions.Timeout()):
            with self.assertRaises(LLMError):
                self.client.generate("hi")

    def test_connection_error_raises(self):
        import requests

        with patch("requests.post", side_effect=requests.exceptions.ConnectionError()):
            with self.assertRaises(LLMError):
                self.client.generate("hi")

    def test_empty_response_raises(self):
        # A 200 with no text is also a failure; it used to produce empty analyses.
        with patch("requests.post", return_value=FakeResponse(200, {"response": "   "})):
            with self.assertRaises(LLMError):
                self.client.generate("hi")

    def test_success_returns_text(self):
        with patch("requests.post", return_value=FakeResponse(200, {"response": "an analysis"})):
            self.assertEqual(self.client.generate("hi"), "an analysis")

    def test_thinking_disabled_in_payload(self):
        # qwen3.x thinks by default: a one-line translation took 38s with
        # thinking on and 1s with it off. The pipeline never needs the trace.
        with patch("requests.post", return_value=FakeResponse(200, {"response": "ok"})) as post:
            self.client.generate("hi")
        self.assertIs(post.call_args.kwargs["json"]["think"], False)

    def test_error_string_never_returned(self):
        """No failure mode may yield a string that looks like prose."""
        with patch("requests.post", return_value=FakeResponse(500, {})):
            try:
                result = self.client.generate("hi")
            except LLMError:
                return
            self.fail(f"expected LLMError, got return value {result!r}")


class TestModelResolution(unittest.TestCase):
    INSTALLED = [
        "hf.co/mradermacher/AstroSage-70B-i1-GGUF:Q4_K_M",
        "qwen2.5:32b",
        "nomic-embed-text:latest",
    ]

    def setUp(self):
        self.client = LLMClient()

    def test_exact_name_accepted(self):
        with patch.object(LLMClient, "get_models", return_value=self.INSTALLED):
            self.assertEqual(self.client.require_model("qwen2.5:32b"), "qwen2.5:32b")

    def test_missing_model_raises_with_available_list(self):
        with patch.object(LLMClient, "get_models", return_value=self.INSTALLED):
            with self.assertRaises(LLMError) as ctx:
                self.client.require_model("astrosage:70b-q4_K_M")
        message = str(ctx.exception)
        self.assertIn("astrosage:70b-q4_K_M", message)
        self.assertIn("qwen2.5:32b", message)  # available models shown so the fix is obvious

    def test_tag_suffix_match(self):
        # Ollama reports 'name:latest'; a bare name should still resolve.
        with patch.object(LLMClient, "get_models", return_value=self.INSTALLED):
            self.assertEqual(
                self.client.require_model("nomic-embed-text"), "nomic-embed-text:latest"
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
