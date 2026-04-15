"""Tests for src.v3.cost_logger — CSV cost logging."""

from __future__ import annotations

import csv
import os
import pytest
from pathlib import Path

from src.v3.cost_logger import CostLogger, _get_pricing


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_log(tmp_path):
    """Return a CostLogger pointed at a temp CSV file."""
    return CostLogger(log_path=tmp_path / "test_cost.csv")


# ---------------------------------------------------------------------------
# _get_pricing
# ---------------------------------------------------------------------------

class TestGetPricing:
    def test_returns_zeros_when_no_env(self, monkeypatch):
        monkeypatch.delenv("AZURE_OPENAI_INPUT_USD_PER_MILLION", raising=False)
        monkeypatch.delenv("AZURE_OPENAI_OUTPUT_USD_PER_MILLION", raising=False)
        assert _get_pricing("gpt-5.4") == (0.0, 0.0)

    def test_reads_global_env(self, monkeypatch):
        monkeypatch.setenv("AZURE_OPENAI_INPUT_USD_PER_MILLION", "2.50")
        monkeypatch.setenv("AZURE_OPENAI_OUTPUT_USD_PER_MILLION", "10.00")
        assert _get_pricing("gpt-5.4") == (2.50, 10.00)

    def test_per_model_overrides_global(self, monkeypatch):
        monkeypatch.setenv("AZURE_OPENAI_INPUT_USD_PER_MILLION", "2.50")
        monkeypatch.setenv("AZURE_OPENAI_OUTPUT_USD_PER_MILLION", "10.00")
        monkeypatch.setenv("V3_COST_GPT_5_4_INPUT", "5.00")
        monkeypatch.setenv("V3_COST_GPT_5_4_OUTPUT", "15.00")
        assert _get_pricing("gpt-5.4") == (5.00, 15.00)

    def test_model_slug_handles_dots_and_dashes(self, monkeypatch):
        monkeypatch.setenv("V3_COST_GPT_5_3_CODEX_INPUT", "1.00")
        monkeypatch.setenv("V3_COST_GPT_5_3_CODEX_OUTPUT", "3.00")
        assert _get_pricing("gpt-5.3-codex") == (1.00, 3.00)


# ---------------------------------------------------------------------------
# CostLogger.log_call
# ---------------------------------------------------------------------------

class TestLogCall:
    def test_creates_csv_with_header(self, tmp_log):
        tmp_log.log_call("gpt-5.4", "generate_json", "planner",
                         input_tokens=100, output_tokens=50)

        rows = _read_csv(tmp_log.log_path)
        assert len(rows) == 1
        assert rows[0]["model"] == "gpt-5.4"
        assert rows[0]["method"] == "generate_json"
        assert rows[0]["caller"] == "planner"
        assert rows[0]["input_tokens"] == "100"
        assert rows[0]["output_tokens"] == "50"
        assert rows[0]["total_tokens"] == "150"

    def test_appends_multiple_rows(self, tmp_log):
        tmp_log.log_call("gpt-5.4", "generate_json", "planner",
                         input_tokens=100, output_tokens=50)
        tmp_log.log_call("gpt-5.3-codex", "generate_code", "builder",
                         input_tokens=200, output_tokens=300)

        rows = _read_csv(tmp_log.log_path)
        assert len(rows) == 2
        assert rows[0]["model"] == "gpt-5.4"
        assert rows[1]["model"] == "gpt-5.3-codex"

    def test_cost_computed_from_env(self, tmp_log, monkeypatch):
        monkeypatch.setenv("AZURE_OPENAI_INPUT_USD_PER_MILLION", "2.00")
        monkeypatch.setenv("AZURE_OPENAI_OUTPUT_USD_PER_MILLION", "8.00")

        row = tmp_log.log_call("gpt-5.4", "generate_json", "planner",
                               input_tokens=1_000_000, output_tokens=500_000)

        assert float(row["input_cost_usd"]) == pytest.approx(2.00)
        assert float(row["output_cost_usd"]) == pytest.approx(4.00)
        assert float(row["total_cost_usd"]) == pytest.approx(6.00)

    def test_cost_zero_without_env(self, tmp_log, monkeypatch):
        monkeypatch.delenv("AZURE_OPENAI_INPUT_USD_PER_MILLION", raising=False)
        monkeypatch.delenv("AZURE_OPENAI_OUTPUT_USD_PER_MILLION", raising=False)

        row = tmp_log.log_call("gpt-5.4", "generate_json", "planner",
                               input_tokens=500, output_tokens=200)

        assert float(row["total_cost_usd"]) == 0.0

    def test_prompt_preview_truncated(self, tmp_log):
        long_prompt = "word " * 100  # 500 chars
        row = tmp_log.log_call("gpt-5.4", "generate_json", "planner",
                               input_tokens=10, output_tokens=5,
                               prompt_preview=long_prompt)

        assert len(row["prompt_preview"]) <= 200

    def test_prompt_preview_newlines_collapsed(self, tmp_log):
        prompt = "line one\n\nline two\n\tline three"
        row = tmp_log.log_call("gpt-5.4", "generate_json", "planner",
                               input_tokens=10, output_tokens=5,
                               prompt_preview=prompt)

        assert "\n" not in row["prompt_preview"]
        assert "\t" not in row["prompt_preview"]

    def test_response_id_stored(self, tmp_log):
        row = tmp_log.log_call("gpt-5.4", "generate_json", "planner",
                               input_tokens=10, output_tokens=5,
                               response_id="resp_abc123")

        assert row["response_id"] == "resp_abc123"

    def test_timestamp_is_iso_utc(self, tmp_log):
        row = tmp_log.log_call("gpt-5.4", "generate_json", "planner",
                               input_tokens=10, output_tokens=5)

        assert row["timestamp"].endswith("Z")
        assert "T" in row["timestamp"]

    def test_total_tokens_override(self, tmp_log):
        row = tmp_log.log_call("gpt-5.4", "generate_json", "planner",
                               input_tokens=100, output_tokens=50,
                               total_tokens=200)

        assert row["total_tokens"] == "200"


# ---------------------------------------------------------------------------
# CostLogger.read_log
# ---------------------------------------------------------------------------

class TestReadLog:
    def test_empty_when_no_file(self, tmp_path):
        logger = CostLogger(log_path=tmp_path / "nonexistent.csv")
        assert logger.read_log() == []

    def test_reads_back_written_rows(self, tmp_log):
        tmp_log.log_call("gpt-5.4", "generate_json", "planner",
                         input_tokens=100, output_tokens=50)
        tmp_log.log_call("gpt-5.2", "generate_code", "builder",
                         input_tokens=200, output_tokens=300)

        rows = tmp_log.read_log()
        assert len(rows) == 2
        assert rows[0]["model"] == "gpt-5.4"
        assert rows[1]["model"] == "gpt-5.2"


# ---------------------------------------------------------------------------
# CostLogger.summarize
# ---------------------------------------------------------------------------

class TestSummarize:
    def test_no_calls_message(self, tmp_path):
        logger = CostLogger(log_path=tmp_path / "empty.csv")
        summary = logger.summarize()
        assert "No LLM calls logged yet" in summary

    def test_summary_contains_sections(self, tmp_log):
        tmp_log.log_call("gpt-5.4", "generate_json", "planner",
                         input_tokens=500, output_tokens=200)
        tmp_log.log_call("gpt-5.3-codex", "generate_code", "builder",
                         input_tokens=1000, output_tokens=800)

        summary = tmp_log.summarize()
        assert "LLM COST SUMMARY" in summary
        assert "Total calls: 2" in summary
        assert "By Model" in summary
        assert "By Caller" in summary
        assert "Daily" in summary
        assert "Weekly" in summary
        assert "Monthly" in summary
        assert "gpt-5.4" in summary
        assert "gpt-5.3-codex" in summary
        assert "planner" in summary
        assert "builder" in summary

    def test_summary_token_totals(self, tmp_log):
        tmp_log.log_call("gpt-5.4", "generate_json", "planner",
                         input_tokens=500, output_tokens=200)
        tmp_log.log_call("gpt-5.4", "generate_json", "reviewer",
                         input_tokens=300, output_tokens=100)

        summary = tmp_log.summarize()
        assert "800" in summary  # total input
        assert "300" in summary  # total output

    def test_summary_cost_note_zero(self, tmp_log, monkeypatch):
        monkeypatch.delenv("AZURE_OPENAI_INPUT_USD_PER_MILLION", raising=False)
        monkeypatch.delenv("AZURE_OPENAI_OUTPUT_USD_PER_MILLION", raising=False)
        tmp_log.log_call("gpt-5.4", "generate_json", "planner",
                         input_tokens=500, output_tokens=200)

        summary = tmp_log.summarize()
        assert "Costs are $0" in summary

    def test_summary_cost_note_configured(self, tmp_log, monkeypatch):
        monkeypatch.setenv("AZURE_OPENAI_INPUT_USD_PER_MILLION", "2.00")
        monkeypatch.setenv("AZURE_OPENAI_OUTPUT_USD_PER_MILLION", "8.00")
        tmp_log.log_call("gpt-5.4", "generate_json", "planner",
                         input_tokens=1_000_000, output_tokens=500_000)

        summary = tmp_log.summarize()
        assert "Costs computed from env-configured rates" in summary


# ---------------------------------------------------------------------------
# Integration: CostLogger wired into ResponsesClient
# ---------------------------------------------------------------------------

class TestCostLoggerIntegration:
    def test_client_logs_generate_json(self, tmp_path):
        """ResponsesClient.generate_json writes a row to the cost CSV."""
        import json
        from unittest.mock import MagicMock, patch
        from src.v3.llm_client import ResponsesClient

        log_path = tmp_path / "cost.csv"
        cost_logger = CostLogger(log_path=log_path)
        client = ResponsesClient("https://example.com", "key",
                                 cost_logger=cost_logger)

        body = {
            "id": "resp_test",
            "model": "gpt-5.4",
            "output": [{"type": "message", "role": "assistant",
                        "content": [{"type": "output_text", "text": '{"ok": true}'}]}],
            "usage": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(body).encode("utf-8")
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("src.v3.llm_client.request.urlopen", return_value=mock_resp):
            client.generate_json("gpt-5.4", instructions="test", input_text="test input")

        rows = _read_csv(log_path)
        assert len(rows) == 1
        assert rows[0]["model"] == "gpt-5.4"
        assert rows[0]["method"] == "generate_json"
        assert rows[0]["input_tokens"] == "100"
        assert rows[0]["output_tokens"] == "50"
        assert rows[0]["response_id"] == "resp_test"
        assert "test input" in rows[0]["prompt_preview"]

    def test_client_logs_generate_code(self, tmp_path):
        """ResponsesClient.generate_code writes a row to the cost CSV."""
        import json
        from unittest.mock import MagicMock, patch
        from src.v3.llm_client import ResponsesClient

        log_path = tmp_path / "cost.csv"
        cost_logger = CostLogger(log_path=log_path)
        client = ResponsesClient("https://example.com", "key",
                                 cost_logger=cost_logger)

        body = {
            "id": "resp_code",
            "model": "gpt-5.3-codex",
            "output": [{"type": "message", "role": "assistant",
                        "content": [{"type": "output_text", "text": "def hello(): pass"}]}],
            "usage": {"input_tokens": 200, "output_tokens": 100, "total_tokens": 300},
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(body).encode("utf-8")
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("src.v3.llm_client.request.urlopen", return_value=mock_resp):
            client.generate_code("gpt-5.3-codex", instructions="test", input_text="write code")

        rows = _read_csv(log_path)
        assert len(rows) == 1
        assert rows[0]["method"] == "generate_code"
        assert rows[0]["model"] == "gpt-5.3-codex"

    def test_logging_failure_does_not_break_client(self, tmp_path):
        """If cost logging fails, the API call still succeeds."""
        import json
        from unittest.mock import MagicMock, patch
        from src.v3.llm_client import ResponsesClient

        cost_logger = CostLogger(log_path=tmp_path / "cost.csv")
        cost_logger.log_call = MagicMock(side_effect=IOError("disk full"))
        client = ResponsesClient("https://example.com", "key",
                                 cost_logger=cost_logger)

        body = {
            "id": "resp_ok",
            "model": "gpt-5.4",
            "output": [{"type": "message", "role": "assistant",
                        "content": [{"type": "output_text", "text": '{"ok": true}'}]}],
            "usage": {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(body).encode("utf-8")
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("src.v3.llm_client.request.urlopen", return_value=mock_resp):
            result = client.generate_json("gpt-5.4", instructions="test", input_text="test")

        assert result.parsed == {"ok": True}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))
