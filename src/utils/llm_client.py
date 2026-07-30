#!/usr/bin/env python3
"""
Unified LLM client for all agents.

Failures raise LLMError. They must never be returned as text: an earlier version
returned the string "Error: HTTP 404", callers stored it as an expert review, and
the two astronomy experts silently produced nothing for weeks.
"""

import os
from typing import List, Optional

import requests


class LLMError(RuntimeError):
    """Raised when the LLM backend cannot produce a usable response."""


DEFAULT_URL = "http://127.0.0.1:11434"


class LLMClient:
    """Single reusable LLM client for all agents - supports multiple models"""

    # Generous by default: a cold 20-42 GB model load happens inside the first
    # request, and 180s was not enough for a 32B model loading from disk.
    def __init__(self, base_url: str = None, model: str = "qwen2.5:32b",
                 timeout: int = 420):
        self.base_url = (base_url or os.getenv("OLLAMA_URL", DEFAULT_URL)).rstrip("/")
        self.model = model
        self.timeout = timeout

    def generate(self, prompt: str, model: Optional[str] = None,
                 format: Optional[str] = None, timeout: Optional[int] = None,
                 options: Optional[dict] = None) -> str:
        """
        Generate a response from the LLM.

        Args:
            options: Ollama sampling options, e.g. {"temperature": 0.2}. Ollama
                defaults to 0.8, which is far too loose for translation and
                structured extraction - it is a direct cause of script drift.

        Returns:
            Generated text (never empty)

        Raises:
            LLMError: on transport failure, non-200 status, or empty output
        """
        target = model or self.model
        payload = {"model": target, "prompt": prompt, "stream": False}
        if format:
            payload["format"] = format
        if options:
            payload["options"] = options

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=timeout or self.timeout,
            )
        except requests.exceptions.Timeout as exc:
            raise LLMError(
                f"timeout after {timeout or self.timeout}s for model '{target}'"
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise LLMError(f"request failed for model '{target}': {exc}") from exc

        if response.status_code != 200:
            try:
                detail = response.json().get("error", "")
            except ValueError:
                detail = response.text[:200]
            raise LLMError(f"HTTP {response.status_code} for model '{target}': {detail}")

        try:
            text = response.json().get("response", "")
        except ValueError as exc:
            raise LLMError(f"malformed JSON from model '{target}'") from exc

        if not text or not text.strip():
            raise LLMError(f"empty response from model '{target}'")

        return text

    def embed(self, text: str, model: str = "nomic-embed-text",
              timeout: Optional[int] = None) -> List[float]:
        """
        Embed text into a vector.

        Raises:
            LLMError: on transport failure, non-200 status, or empty vector
        """
        try:
            response = requests.post(
                f"{self.base_url}/api/embeddings",
                json={"model": model, "prompt": text},
                timeout=timeout or 60,
            )
        except requests.exceptions.RequestException as exc:
            raise LLMError(f"embedding request failed for model '{model}': {exc}") from exc

        if response.status_code != 200:
            raise LLMError(f"HTTP {response.status_code} embedding with model '{model}'")

        try:
            vector = response.json().get("embedding") or []
        except ValueError as exc:
            raise LLMError(f"malformed JSON embedding with model '{model}'") from exc

        if not vector:
            raise LLMError(f"empty embedding from model '{model}'")
        return vector

    def is_available(self) -> bool:
        """Check if the LLM service is reachable"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def get_models(self) -> List[str]:
        """List installed model names"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=10)
            if response.status_code != 200:
                return []
            return [m.get("name", "") for m in response.json().get("models", [])]
        except (requests.exceptions.RequestException, ValueError):
            return []

    def require_model(self, name: str) -> str:
        """
        Verify a configured model is installed, returning its canonical tag.

        A bare name resolves to its tagged form (nomic-embed-text ->
        nomic-embed-text:latest). Anything else is a misconfiguration and must
        fail loudly at startup rather than becoming a 404 on every request.

        Raises:
            LLMError: if the model is not installed
        """
        installed = self.get_models()
        if name in installed:
            return name

        for candidate in installed:
            if candidate.rsplit(":", 1)[0] == name:
                return candidate

        listing = "\n  ".join(installed) if installed else "(none - is ollama running?)"
        raise LLMError(
            f"configured model '{name}' is not installed.\n"
            f"Installed models:\n  {listing}\n"
            f"Fix the model name in .env, or run: ollama pull {name}"
        )
