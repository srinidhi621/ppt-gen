"""Gemini REST client for JSON generation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict
from urllib import error, parse, request

from .base import LLMClientError, LLMResponse, LLMUsage
from .pricing import estimate_cost_usd


@dataclass
class GeminiClient:
    """Small client that calls Gemini generateContent endpoint."""

    api_key: str
    model: str = "gemini-2.5-flash"
    provider: str = "gemini"
    timeout_seconds: int = 90

    def generate_json(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        endpoint = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{parse.quote(self.model)}:generateContent?key={parse.quote(self.api_key)}"
        )
        payload = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
            },
        }
        req = request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except TimeoutError as exc:
            raise LLMClientError("Gemini request timed out.") from exc
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise LLMClientError(f"Gemini HTTP error {exc.code}: {detail}") from exc
        except error.URLError as exc:
            raise LLMClientError(f"Gemini network error: {exc.reason}") from exc

        try:
            body = json.loads(raw)
            text = _extract_text_payload(body)
            parsed = json.loads(text)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise LLMClientError("Gemini response is not valid JSON payload.") from exc

        if not isinstance(parsed, dict):
            raise LLMClientError("Gemini response JSON must be an object.")

        usage_metadata = body.get("usageMetadata", {}) if isinstance(body, dict) else {}
        prompt_tokens = int(usage_metadata.get("promptTokenCount", 0) or 0)
        completion_tokens = int(usage_metadata.get("candidatesTokenCount", 0) or 0)
        total_tokens = int(
            usage_metadata.get("totalTokenCount", prompt_tokens + completion_tokens)
            or (prompt_tokens + completion_tokens)
        )
        usage = LLMUsage(
            provider=self.provider,
            model=self.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=estimate_cost_usd(
                self.provider, self.model, prompt_tokens, completion_tokens
            ),
            raw_usage=usage_metadata if isinstance(usage_metadata, dict) else {},
        )
        return LLMResponse(data=parsed, usage=usage)


def _extract_text_payload(response_body: Dict[str, Any]) -> str:
    candidates = response_body["candidates"]
    first = candidates[0]
    content = first["content"]
    parts = content["parts"]
    first_part = parts[0]
    text = first_part["text"]
    if not isinstance(text, str):
        raise LLMClientError("Gemini response text is missing.")
    return text
