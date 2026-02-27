"""Azure OpenAI chat-completions client for JSON generation."""

from __future__ import annotations

import base64
import json
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict
from urllib import error, parse, request

from .base import LLMClientError, LLMResponse, LLMUsage
from .pricing import estimate_cost_usd


@dataclass
class AzureOpenAIClient:
    """OpenAI-compatible client against Azure deployment endpoint."""

    endpoint: str
    api_key: str
    deployment: str
    model: str
    provider: str = "azure_openai"
    api_version: str = "2024-10-21"
    timeout_seconds: int = 90

    def generate_json(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        payload = {
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        return self._request_json(payload)

    def generate_json_with_images(
        self, system_prompt: str, user_prompt: str, image_paths: list[Path]
    ) -> LLMResponse:
        if not image_paths:
            return self.generate_json(system_prompt, user_prompt)
        user_content: list[Dict[str, Any]] = [{"type": "text", "text": user_prompt}]
        for image_path in image_paths:
            user_content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": _to_data_url(image_path)},
                }
            )
        payload = {
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        }
        return self._request_json(payload)

    def _request_json(self, payload: Dict[str, Any]) -> LLMResponse:
        base = self.endpoint.rstrip("/")
        path = f"/openai/deployments/{parse.quote(self.deployment)}/chat/completions"
        url = f"{base}{path}?api-version={parse.quote(self.api_version)}"
        req = request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={"api-key": self.api_key, "Content-Type": "application/json"},
        )
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except TimeoutError as exc:
            raise LLMClientError("Azure OpenAI request timed out.") from exc
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise LLMClientError(f"Azure OpenAI HTTP error {exc.code}: {detail}") from exc
        except error.URLError as exc:
            raise LLMClientError(f"Azure OpenAI network error: {exc.reason}") from exc

        try:
            body = json.loads(raw)
            content = body["choices"][0]["message"]["content"]
            parsed = json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise LLMClientError("Azure OpenAI response is not valid JSON payload.") from exc
        if not isinstance(parsed, dict):
            raise LLMClientError("Azure OpenAI response JSON must be an object.")

        usage_raw = body.get("usage", {}) if isinstance(body, dict) else {}
        prompt_tokens = int(usage_raw.get("prompt_tokens", 0) or 0)
        completion_tokens = int(usage_raw.get("completion_tokens", 0) or 0)
        total_tokens = int(
            usage_raw.get("total_tokens", prompt_tokens + completion_tokens)
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
            raw_usage=usage_raw if isinstance(usage_raw, dict) else {},
        )
        return LLMResponse(data=parsed, usage=usage)


def _to_data_url(image_path: Path) -> str:
    if not image_path.exists():
        raise LLMClientError(f"Review image not found: {image_path}")
    mime = mimetypes.guess_type(str(image_path))[0] or "image/png"
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"
