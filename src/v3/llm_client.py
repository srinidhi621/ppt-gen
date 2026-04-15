"""Azure OpenAI Responses API client for V3 pipeline.

Uses the Responses API exclusively (/openai/responses?api-version=...).
Does NOT use the Chat Completions API. See AGENTS.md Rule 9.

Usage::

    client = ResponsesClient.from_env()
    result = client.generate_json("gpt-5.4", instructions="...", input_text="...")
    print(result.parsed)  # dict
"""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib import error, parse, request

from src.v3.cost_logger import CostLogger


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class LLMUsage:
    """Token usage for a single LLM call."""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


@dataclass
class LLMResponse:
    """Response from a Responses API call."""
    text: str = ""
    parsed: dict | None = None
    usage: LLMUsage = field(default_factory=LLMUsage)
    model: str = ""
    response_id: str = ""


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class LLMError(Exception):
    """Base error for LLM client failures."""


class LLMInfraError(LLMError):
    """Infrastructure error (auth, network, rate limit). No retry."""
    def __init__(self, message: str, status_code: int = 0):
        super().__init__(message)
        self.status_code = status_code


class LLMValidationError(LLMError):
    """Response failed parsing or validation. Retryable."""


class LLMBudgetExhausted(LLMError):
    """Retry budget exhausted."""


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

_INFRA_STATUS_CODES = {401, 403, 408, 429, 500, 502, 503, 504}

# Minimum model floor
_APPROVED_MODEL_PREFIXES = ("gpt-5.2", "gpt-5.3", "gpt-5.4", "gpt-5.5",
                            "gpt-5.6", "gpt-5.7", "gpt-5.8", "gpt-5.9",
                            "gpt-6")


class ResponsesClient:
    """Azure OpenAI Responses API client.

    All V3 LLM calls go through this client. It hits a single endpoint:
    POST {base_url}/openai/responses?api-version={api_version}
    with the model name in the request body.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        api_version: str = "2025-04-01-preview",
        cost_logger: CostLogger | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.api_version = api_version
        self._url = f"{self.base_url}/openai/responses?api-version={self.api_version}"
        # Cost logging is opt-in: pass a CostLogger to enable.
        # None means disabled (no CSV writes).
        self._cost_logger = cost_logger

    @classmethod
    def from_env(cls, env_path: str | Path | None = None) -> ResponsesClient:
        """Create a client from environment variables or a .env file."""
        if env_path is not None:
            _load_dotenv(Path(env_path))

        endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
        api_key = os.environ.get("AZURE_OPENAI_API_KEY", "")
        api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2025-04-01-preview")

        if not endpoint or not api_key:
            raise LLMInfraError(
                "AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY must be set"
            )

        # Strip any path suffix from endpoint
        parsed = parse.urlparse(endpoint)
        base_url = f"{parsed.scheme}://{parsed.netloc}"

        return cls(base_url, api_key, api_version)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_json(
        self,
        model: str,
        instructions: str,
        input_text: str,
        *,
        caller: str = "unknown",
        temperature: float = 0.3,
        max_output_tokens: int = 4096,
    ) -> LLMResponse:
        """Generate a JSON response. Returns LLMResponse with .parsed dict."""
        _check_model(model)
        payload = {
            "model": model,
            "instructions": instructions,
            "input": input_text,
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
            "text": {"format": {"type": "json_object"}},
        }
        body, usage, meta = self._post(payload)
        text = _extract_output_text(body)

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise LLMValidationError(f"Response is not valid JSON: {exc}") from exc

        resp = LLMResponse(
            text=text,
            parsed=parsed,
            usage=usage,
            model=meta.get("model", model),
            response_id=meta.get("id", ""),
        )
        self._log(model, "generate_json", caller, usage, meta, input_text)
        return resp

    def generate_code(
        self,
        model: str,
        instructions: str,
        input_text: str,
        *,
        caller: str = "unknown",
        temperature: float = 0.2,
        max_output_tokens: int = 8192,
    ) -> LLMResponse:
        """Generate plain text (code). Returns LLMResponse with .text."""
        _check_model(model)
        payload = {
            "model": model,
            "instructions": instructions,
            "input": input_text,
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
        }
        body, usage, meta = self._post(payload)
        text = _extract_output_text(body)

        resp = LLMResponse(
            text=text,
            parsed=None,
            usage=usage,
            model=meta.get("model", model),
            response_id=meta.get("id", ""),
        )
        self._log(model, "generate_code", caller, usage, meta, input_text)
        return resp

    def generate_json_with_images(
        self,
        model: str,
        instructions: str,
        input_text: str,
        images: list[bytes | str | Path],
        *,
        caller: str = "unknown",
        temperature: float = 0.3,
        max_output_tokens: int = 4096,
    ) -> LLMResponse:
        """Generate JSON with image inputs (vision). Returns LLMResponse with .parsed dict."""
        _check_model(model)

        # Build multimodal input
        content_parts: list[dict] = [
            {"type": "input_text", "text": input_text},
        ]
        for img in images:
            raw_bytes, mime = _encode_image_with_mime(img)
            b64 = base64.b64encode(raw_bytes).decode("ascii")
            content_parts.append({
                "type": "input_image",
                "image_url": f"data:{mime};base64,{b64}",
            })

        payload = {
            "model": model,
            "instructions": instructions,
            "input": [
                {
                    "type": "message",
                    "role": "user",
                    "content": content_parts,
                },
            ],
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
            "text": {"format": {"type": "json_object"}},
        }
        body, usage, meta = self._post(payload)
        text = _extract_output_text(body)

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise LLMValidationError(f"Response is not valid JSON: {exc}") from exc

        resp = LLMResponse(
            text=text,
            parsed=parsed,
            usage=usage,
            model=meta.get("model", model),
            response_id=meta.get("id", ""),
        )
        self._log(model, "generate_json_with_images", caller, usage, meta, input_text)
        return resp

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _log(
        self,
        model: str,
        method: str,
        caller: str,
        usage: LLMUsage,
        meta: dict,
        prompt: str,
    ) -> None:
        """Log an API call to the cost CSV.

        Only persistence-related failures (IOError/OSError) are suppressed.
        Programmer bugs (TypeError, KeyError, etc.) propagate normally.
        """
        if self._cost_logger is None:
            return
        try:
            self._cost_logger.log_call(
                model=model,
                method=method,
                caller=caller,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                total_tokens=usage.total_tokens,
                response_id=meta.get("id", ""),
                prompt_preview=prompt,
            )
        except OSError:
            pass  # disk/permission failures must not break the pipeline

    def _post(self, payload: dict) -> tuple[dict, LLMUsage, dict]:
        """POST to Responses API. Returns (body, usage, metadata)."""
        data = json.dumps(payload).encode("utf-8")
        req = request.Request(
            self._url,
            data=data,
            headers={
                "api-key": self.api_key,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=120) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except error.HTTPError as exc:
            status = exc.code
            detail = exc.read().decode("utf-8", errors="replace")[:1000]
            if status in _INFRA_STATUS_CODES:
                raise LLMInfraError(f"HTTP {status}: {detail}", status_code=status) from exc
            raise LLMValidationError(f"HTTP {status}: {detail}") from exc
        except Exception as exc:
            raise LLMInfraError(f"Network error: {exc}") from exc

        # Extract usage
        raw_usage = body.get("usage", {})
        usage = LLMUsage(
            input_tokens=raw_usage.get("input_tokens", 0),
            output_tokens=raw_usage.get("output_tokens", 0),
            total_tokens=raw_usage.get("total_tokens", 0),
        )

        meta = {"model": body.get("model", ""), "id": body.get("id", "")}
        return body, usage, meta


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _check_model(model: str) -> None:
    """Enforce minimum model floor."""
    if not any(model.startswith(p) for p in _APPROVED_MODEL_PREFIXES):
        raise ValueError(
            f"Model '{model}' is below the minimum floor (gpt-5.2). "
            f"Approved prefixes: {_APPROVED_MODEL_PREFIXES}"
        )


def _extract_output_text(body: dict) -> str:
    """Extract text from a Responses API response body."""
    for item in body.get("output", []):
        if item.get("type") == "message":
            for c in item.get("content", []):
                if c.get("text"):
                    return c["text"]
    return ""


# Mapping of magic-byte prefixes to MIME types
_IMAGE_SIGNATURES: list[tuple[bytes, str]] = [
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"RIFF", "image/webp"),  # WebP starts with RIFF....WEBP
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
]

# File extension to MIME fallback
_EXT_TO_MIME: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


def _detect_mime(data: bytes) -> str:
    """Detect image MIME type from magic bytes. Falls back to image/png."""
    for sig, mime in _IMAGE_SIGNATURES:
        if data[:len(sig)] == sig:
            return mime
    return "image/png"


def _encode_image_with_mime(img: bytes | str | Path) -> tuple[bytes, str]:
    """Read image bytes and detect MIME type.

    Returns (raw_bytes, mime_type).
    """
    ext_hint = ""
    if isinstance(img, str):
        img = Path(img)
    if isinstance(img, Path):
        ext_hint = img.suffix.lower()
        img = img.read_bytes()
    # Detect from magic bytes first, then fall back to extension
    mime = _detect_mime(img)
    if mime == "image/png" and ext_hint in _EXT_TO_MIME:
        mime = _EXT_TO_MIME[ext_hint]
    return img, mime


def _load_dotenv(path: Path) -> None:
    """Load a .env file into os.environ (simple parser, no overwrite)."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if key and key not in os.environ:
            os.environ[key] = value


def get_model_for_role(role: str) -> str:
    """Get the configured model for a pipeline role.

    Reads V3_PLANNER_MODEL, V3_BUILDER_MODEL, V3_REVIEWER_MODEL
    from environment. Falls back to gpt-5.4.
    """
    env_key = f"V3_{role.upper()}_MODEL"
    return os.environ.get(env_key, "gpt-5.4")
