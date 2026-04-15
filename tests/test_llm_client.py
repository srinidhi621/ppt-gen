"""Tests for src.v3.llm_client — Responses API client."""

from __future__ import annotations

import json
import pytest
from unittest.mock import MagicMock, patch
from urllib import error

from src.v3.llm_client import (
    CostLogger,
    LLMInfraError,
    LLMResponse,
    LLMUsage,
    LLMValidationError,
    ResponsesClient,
    _check_model,
    _detect_mime,
    _encode_image_with_mime,
    _extract_output_text,
    get_model_for_role,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_responses_body(text: str = "hello", model: str = "gpt-5.4") -> dict:
    """Build a minimal Responses API body."""
    return {
        "id": "resp_abc123",
        "model": model,
        "output": [
            {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": text}],
            }
        ],
        "usage": {
            "input_tokens": 10,
            "output_tokens": 5,
            "total_tokens": 15,
        },
    }


def _mock_urlopen(body_dict: dict):
    """Create a mock for urllib.request.urlopen that returns body_dict."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(body_dict).encode("utf-8")
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


# ---------------------------------------------------------------------------
# _check_model
# ---------------------------------------------------------------------------

class TestCheckModel:
    def test_approved_model_passes(self):
        _check_model("gpt-5.4")
        _check_model("gpt-5.3-codex")
        _check_model("gpt-5.2")

    def test_old_model_rejected(self):
        with pytest.raises(ValueError, match="below the minimum floor"):
            _check_model("gpt-4o")

    def test_gpt4_rejected(self):
        with pytest.raises(ValueError, match="below the minimum floor"):
            _check_model("gpt-4.1")


# ---------------------------------------------------------------------------
# _extract_output_text
# ---------------------------------------------------------------------------

class TestExtractOutputText:
    def test_extracts_text(self):
        body = _make_responses_body("test output")
        assert _extract_output_text(body) == "test output"

    def test_empty_output(self):
        assert _extract_output_text({"output": []}) == ""

    def test_no_message_type(self):
        body = {"output": [{"type": "other", "content": []}]}
        assert _extract_output_text(body) == ""


# ---------------------------------------------------------------------------
# ResponsesClient
# ---------------------------------------------------------------------------

class TestResponsesClient:
    def _client(self):
        return ResponsesClient("https://example.com", "test-key", "2025-04-01-preview")

    @patch("src.v3.llm_client.request.urlopen")
    def test_generate_json_success(self, mock_urlopen_fn):
        body = _make_responses_body('{"slides": []}')
        mock_urlopen_fn.return_value = _mock_urlopen(body)

        client = self._client()
        result = client.generate_json("gpt-5.4", instructions="test", input_text="test")

        assert result.parsed == {"slides": []}
        assert result.usage.input_tokens == 10
        assert result.usage.output_tokens == 5
        assert result.model == "gpt-5.4"

    @patch("src.v3.llm_client.request.urlopen")
    def test_generate_json_invalid_json_raises(self, mock_urlopen_fn):
        body = _make_responses_body("not json at all")
        mock_urlopen_fn.return_value = _mock_urlopen(body)

        client = self._client()
        with pytest.raises(LLMValidationError, match="not valid JSON"):
            client.generate_json("gpt-5.4", instructions="test", input_text="test")

    @patch("src.v3.llm_client.request.urlopen")
    def test_generate_code_success(self, mock_urlopen_fn):
        code = "def hello(): pass"
        body = _make_responses_body(code)
        mock_urlopen_fn.return_value = _mock_urlopen(body)

        client = self._client()
        result = client.generate_code("gpt-5.3-codex", instructions="test", input_text="test")

        assert result.text == code
        assert result.parsed is None

    @patch("src.v3.llm_client.request.urlopen")
    def test_infra_error_on_401(self, mock_urlopen_fn):
        exc = error.HTTPError(
            "https://example.com", 401, "Unauthorized", {}, None
        )
        exc.read = lambda: b"unauthorized"
        mock_urlopen_fn.side_effect = exc

        client = self._client()
        with pytest.raises(LLMInfraError, match="HTTP 401"):
            client.generate_json("gpt-5.4", instructions="test", input_text="test")

    @patch("src.v3.llm_client.request.urlopen")
    def test_infra_error_on_429(self, mock_urlopen_fn):
        exc = error.HTTPError(
            "https://example.com", 429, "Rate limited", {}, None
        )
        exc.read = lambda: b"rate limited"
        mock_urlopen_fn.side_effect = exc

        client = self._client()
        with pytest.raises(LLMInfraError, match="HTTP 429"):
            client.generate_json("gpt-5.4", instructions="test", input_text="test")

    @patch("src.v3.llm_client.request.urlopen")
    def test_validation_error_on_400(self, mock_urlopen_fn):
        exc = error.HTTPError(
            "https://example.com", 400, "Bad Request", {}, None
        )
        exc.read = lambda: b"bad request"
        mock_urlopen_fn.side_effect = exc

        client = self._client()
        with pytest.raises(LLMValidationError, match="HTTP 400"):
            client.generate_json("gpt-5.4", instructions="test", input_text="test")

    def test_model_below_floor_rejected(self):
        client = self._client()
        with pytest.raises(ValueError, match="below the minimum floor"):
            client.generate_json("gpt-4o", instructions="test", input_text="test")


# ---------------------------------------------------------------------------
# _detect_mime / _encode_image_with_mime
# ---------------------------------------------------------------------------

class TestImageMimeDetection:
    def test_png_bytes(self):
        png_header = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        assert _detect_mime(png_header) == "image/png"

    def test_jpeg_bytes(self):
        jpeg_header = b"\xff\xd8\xff\xe0" + b"\x00" * 100
        assert _detect_mime(jpeg_header) == "image/jpeg"

    def test_gif_bytes(self):
        gif_header = b"GIF89a" + b"\x00" * 100
        assert _detect_mime(gif_header) == "image/gif"

    def test_webp_bytes(self):
        webp_header = b"RIFF" + b"\x00" * 4 + b"WEBP" + b"\x00" * 100
        assert _detect_mime(webp_header) == "image/webp"

    def test_unknown_bytes_defaults_to_png(self):
        unknown = b"\x00\x00\x00\x00" + b"\x00" * 100
        assert _detect_mime(unknown) == "image/png"

    def test_encode_from_bytes_detects_jpeg(self):
        jpeg_data = b"\xff\xd8\xff\xe0" + b"\x00" * 50
        raw, mime = _encode_image_with_mime(jpeg_data)
        assert mime == "image/jpeg"
        assert raw == jpeg_data

    def test_encode_from_path_uses_extension(self, tmp_path):
        """When magic bytes are ambiguous, extension is used as fallback."""
        # Write bytes that don't match any known signature
        img_path = tmp_path / "photo.jpg"
        img_path.write_bytes(b"\x00" * 100)
        raw, mime = _encode_image_with_mime(img_path)
        assert mime == "image/jpeg"  # from .jpg extension

    def test_encode_from_path_png_detected(self, tmp_path):
        img_path = tmp_path / "image.png"
        png_data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50
        img_path.write_bytes(png_data)
        raw, mime = _encode_image_with_mime(img_path)
        assert mime == "image/png"
        assert raw == png_data

    def test_encode_from_str_path(self, tmp_path):
        img_path = tmp_path / "test.jpeg"
        img_path.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 50)
        raw, mime = _encode_image_with_mime(str(img_path))
        assert mime == "image/jpeg"


# ---------------------------------------------------------------------------
# get_model_for_role
# ---------------------------------------------------------------------------

class TestGetModelForRole:
    def test_default_is_gpt54(self, monkeypatch):
        monkeypatch.delenv("V3_PLANNER_MODEL", raising=False)
        assert get_model_for_role("planner") == "gpt-5.4"

    def test_reads_env_var(self, monkeypatch):
        monkeypatch.setenv("V3_BUILDER_MODEL", "gpt-5.3-codex")
        assert get_model_for_role("builder") == "gpt-5.3-codex"

    def test_case_insensitive_role(self, monkeypatch):
        monkeypatch.setenv("V3_REVIEWER_MODEL", "gpt-5.2")
        assert get_model_for_role("reviewer") == "gpt-5.2"


# ---------------------------------------------------------------------------
# from_env
# ---------------------------------------------------------------------------

class TestFromEnv:
    def test_missing_vars_raises(self, monkeypatch):
        monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
        monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
        with pytest.raises(LLMInfraError, match="must be set"):
            ResponsesClient.from_env()

    def test_strips_path_from_endpoint(self, monkeypatch):
        monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.com/openai/responses?api-version=2025")
        monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
        client = ResponsesClient.from_env()
        assert client.base_url == "https://example.com"

    def test_enables_persistent_cost_logging_by_default(self, monkeypatch, tmp_path):
        monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.com/openai/responses?api-version=2025")
        monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
        monkeypatch.setenv("V3_COST_LOG_PATH", str(tmp_path / "persistent_costs.csv"))
        monkeypatch.delenv("V3_COST_LOG_ENABLED", raising=False)

        client = ResponsesClient.from_env()

        assert isinstance(client._cost_logger, CostLogger)
        assert client._cost_logger.log_path == tmp_path / "persistent_costs.csv"

    def test_can_disable_cost_logging_via_env(self, monkeypatch):
        monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.com/openai/responses?api-version=2025")
        monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
        monkeypatch.setenv("V3_COST_LOG_ENABLED", "0")

        client = ResponsesClient.from_env()

        assert client._cost_logger is None

    @patch("src.v3.llm_client.request.urlopen")
    def test_from_env_logs_calls_to_persistent_file(self, mock_urlopen_fn, monkeypatch, tmp_path):
        body = _make_responses_body('{"slides": []}')
        mock_urlopen_fn.return_value = _mock_urlopen(body)
        log_path = tmp_path / "persistent_costs.csv"

        monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.com/openai/responses?api-version=2025")
        monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
        monkeypatch.setenv("V3_COST_LOG_PATH", str(log_path))
        monkeypatch.delenv("V3_COST_LOG_ENABLED", raising=False)

        client = ResponsesClient.from_env()
        client.generate_json("gpt-5.4", instructions="test", input_text="test", caller="planner")

        rows = client._cost_logger.read_log()
        assert len(rows) == 1
        assert rows[0]["caller"] == "planner"
        assert rows[0]["method"] == "generate_json"
