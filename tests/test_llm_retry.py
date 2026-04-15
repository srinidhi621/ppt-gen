"""Tests for src.v3.llm_retry — structured retry wrapper."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from src.v3.llm_client import (
    LLMBudgetExhausted,
    LLMInfraError,
    LLMResponse,
    LLMUsage,
    LLMValidationError,
    ResponsesClient,
)
from src.v3.llm_retry import retry_generate_json, _build_retry_input


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_response(parsed: dict) -> LLMResponse:
    return LLMResponse(
        text="{}",
        parsed=parsed,
        usage=LLMUsage(input_tokens=10, output_tokens=5, total_tokens=15),
        model="gpt-5.4",
    )


def _mock_client_json(side_effects: list) -> ResponsesClient:
    """Create a mock client whose generate_json returns items from side_effects in order."""
    client = MagicMock(spec=ResponsesClient)
    client.generate_json = MagicMock(side_effect=side_effects)
    return client


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRetryGenerateJson:
    def test_success_on_first_try(self):
        resp = _make_response({"slides": []})
        client = _mock_client_json([resp])

        result = retry_generate_json(
            client, model="gpt-5.4",
            instructions="test", input_text="test",
        )
        assert result.parsed == {"slides": []}
        assert client.generate_json.call_count == 1

    def test_success_after_validation_retry(self):
        bad_resp = _make_response({"bad": True})
        good_resp = _make_response({"slides": [{"ok": True}]})
        client = _mock_client_json([bad_resp, good_resp])

        def validator(parsed):
            if "slides" not in parsed:
                return ["Missing 'slides'"]
            return []

        result = retry_generate_json(
            client, model="gpt-5.4",
            instructions="test", input_text="test",
            validator=validator, max_retries=2,
        )
        assert result.parsed == {"slides": [{"ok": True}]}
        assert client.generate_json.call_count == 2

    def test_budget_exhausted_after_all_retries(self):
        bad_resp = _make_response({"bad": True})
        client = _mock_client_json([bad_resp, bad_resp, bad_resp])

        def validator(parsed):
            return ["Always fails"]

        with pytest.raises(LLMBudgetExhausted, match="3 attempts"):
            retry_generate_json(
                client, model="gpt-5.4",
                instructions="test", input_text="test",
                validator=validator, max_retries=2,
            )
        assert client.generate_json.call_count == 3

    def test_infra_error_not_retried(self):
        client = _mock_client_json([LLMInfraError("auth failure", status_code=401)])

        with pytest.raises(LLMInfraError, match="auth failure"):
            retry_generate_json(
                client, model="gpt-5.4",
                instructions="test", input_text="test",
            )
        assert client.generate_json.call_count == 1

    def test_json_parse_error_retried(self):
        good_resp = _make_response({"slides": []})
        client = _mock_client_json([
            LLMValidationError("not valid JSON"),
            good_resp,
        ])

        result = retry_generate_json(
            client, model="gpt-5.4",
            instructions="test", input_text="test",
            max_retries=1,
        )
        assert result.parsed == {"slides": []}
        assert client.generate_json.call_count == 2

    def test_no_validator_means_any_json_passes(self):
        resp = _make_response({"anything": "goes"})
        client = _mock_client_json([resp])

        result = retry_generate_json(
            client, model="gpt-5.4",
            instructions="test", input_text="test",
            validator=None,
        )
        assert result.parsed == {"anything": "goes"}

    def test_retry_input_includes_error_context(self):
        bad_resp = _make_response({"bad": True})
        good_resp = _make_response({"slides": []})
        client = _mock_client_json([bad_resp, good_resp])

        def validator(parsed):
            if "slides" not in parsed:
                return ["Missing 'slides'"]
            return []

        retry_generate_json(
            client, model="gpt-5.4",
            instructions="test", input_text="original input",
            validator=validator, max_retries=1,
        )

        # Second call should include error context in input
        second_call_input = client.generate_json.call_args_list[1].kwargs.get(
            "input_text",
            client.generate_json.call_args_list[1][0][2] if len(client.generate_json.call_args_list[1][0]) > 2 else "",
        )
        assert "PREVIOUS RESPONSE FAILED" in second_call_input
        assert "Missing 'slides'" in second_call_input


class TestBuildRetryInput:
    def test_includes_original_and_error(self):
        result = _build_retry_input("original text", "some error")
        assert "original text" in result
        assert "some error" in result
        assert "PREVIOUS RESPONSE FAILED" in result
