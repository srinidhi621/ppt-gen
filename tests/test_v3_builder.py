"""Tests for src.v3.builder — code generation, extraction, prompt assembly."""

from __future__ import annotations

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.v3.builder import (
    BuildAttempt,
    BuildResult,
    assemble_user_message,
    build_deck,
    check_syntax,
    extract_code,
)
from src.v3.example_selector import ExampleSnippet


# ---------------------------------------------------------------------------
# extract_code
# ---------------------------------------------------------------------------

class TestExtractCode:
    def test_strips_markdown_fences(self):
        text = "Here's the code:\n\n```python\nprint('hello')\n```\n\nDone."
        assert extract_code(text) == "print('hello')"

    def test_strips_plain_fences(self):
        text = "```\nimport sys\nprint(sys.argv)\n```"
        assert extract_code(text) == "import sys\nprint(sys.argv)"

    def test_picks_longest_block(self):
        text = (
            "```python\nshort\n```\n\n"
            "```python\nimport sys\nfrom pathlib import Path\nprint('hello')\n```"
        )
        result = extract_code(text)
        assert "import sys" in result
        assert "pathlib" in result

    def test_no_fences_returns_whole_text(self):
        text = "import sys\nprint('hi')"
        assert extract_code(text) == "import sys\nprint('hi')"

    def test_empty_string(self):
        assert extract_code("") == ""

    def test_whitespace_stripped(self):
        text = "  \n```python\n  code  \n```\n  "
        assert extract_code(text) == "code"


# ---------------------------------------------------------------------------
# check_syntax
# ---------------------------------------------------------------------------

class TestCheckSyntax:
    def test_valid_python(self):
        ok, err = check_syntax("print('hello')")
        assert ok is True
        assert err == ""

    def test_syntax_error(self):
        ok, err = check_syntax("def f(\n  pass")
        assert ok is False
        assert "SyntaxError" in err

    def test_empty_code_is_valid(self):
        ok, err = check_syntax("")
        assert ok is True

    def test_multiline_valid(self):
        code = "def f(x):\n    return x * 2\n\nf(3)\n"
        ok, err = check_syntax(code)
        assert ok is True


# ---------------------------------------------------------------------------
# assemble_user_message
# ---------------------------------------------------------------------------

class TestAssembleUserMessage:
    def _plan(self):
        return {
            "deck_id": "test",
            "deck_title": "Test",
            "slides": [{"slide_id": "s1", "archetype": "hero_title", "headline": "Hi"}],
        }

    def test_includes_deck_plan(self):
        msg = assemble_user_message(self._plan(), [])
        assert "deck_plan" in msg.lower() or "Deck plan" in msg
        assert "hero_title" in msg

    def test_includes_design_system_summary(self):
        msg = assemble_user_message(self._plan(), [])
        assert "Design system" in msg or "design_system" in msg.lower()
        # Should mention color tokens
        assert "accent_1" in msg

    def test_includes_examples(self):
        examples = [ExampleSnippet("hero_title", "hero_title/ex", "print('hi')")]
        msg = assemble_user_message(self._plan(), examples)
        assert "print('hi')" in msg
        assert "hero_title" in msg

    def test_retry_context_included(self):
        msg = assemble_user_message(
            self._plan(), [],
            prior_code="bad_code()",
            error_context="SyntaxError at line 1",
        )
        assert "RETRY" in msg
        assert "bad_code()" in msg
        assert "SyntaxError" in msg

    def test_no_retry_without_context(self):
        msg = assemble_user_message(self._plan(), [])
        assert "RETRY" not in msg


# ---------------------------------------------------------------------------
# build_deck (mocked LLM + sandbox)
# ---------------------------------------------------------------------------

class TestBuildDeck:
    def _plan(self):
        return {
            "deck_id": "test",
            "deck_title": "Test",
            "slides": [{"slide_id": "s1", "archetype": "hero_title", "headline": "Hi"}],
        }

    def _mock_client(self, code_text: str):
        """Create a mock client that returns the given code."""
        client = MagicMock()
        resp = MagicMock()
        resp.text = code_text
        resp.usage = MagicMock()
        resp.usage.input_tokens = 100
        resp.usage.output_tokens = 200
        client.generate_code.return_value = resp
        return client

    @patch("src.v3.builder.scan_pptx")
    @patch("src.v3.builder.run_in_sandbox")
    @patch("src.v3.builder.select_examples", return_value=[])
    def test_happy_path(self, mock_select, mock_sandbox, mock_scanner, tmp_path):
        code = "import sys\nprint('OK  saved', sys.argv[1])"
        client = self._mock_client(code)

        # Mock sandbox success
        mock_exec = MagicMock()
        mock_exec.success = True
        mock_exec.ast_scan_ok = True
        mock_exec.pptx_path = str(tmp_path / "build" / "attempt_1" / "deck.pptx")
        mock_exec.to_report.return_value = {"success": True}
        mock_sandbox.return_value = mock_exec

        # Create the fake PPTX
        pptx_path = Path(mock_exec.pptx_path)
        pptx_path.parent.mkdir(parents=True, exist_ok=True)
        pptx_path.write_bytes(b"fake pptx")

        # Mock scanner pass
        mock_scanner.return_value = {"blocking_count": 0, "findings": []}

        result = build_deck(client, self._plan(), work_dir=tmp_path / "build")

        assert result.success is True
        assert result.code == code
        assert len(result.attempts) == 1
        assert result.attempts[0].syntax_ok is True
        assert result.attempts[0].exec_success is True
        assert result.attempts[0].scanner_pass is True

    @patch("src.v3.builder.select_examples", return_value=[])
    def test_syntax_error_triggers_retry(self, mock_select, tmp_path):
        bad_code = "def f(\n  pass"
        good_code = "import sys\nprint('OK')"

        client = MagicMock()
        # First call returns bad syntax, second returns good code
        resp_bad = MagicMock()
        resp_bad.text = bad_code
        resp_bad.usage = MagicMock(input_tokens=10, output_tokens=20)

        resp_good = MagicMock()
        resp_good.text = good_code
        resp_good.usage = MagicMock(input_tokens=10, output_tokens=20)

        client.generate_code.side_effect = [resp_bad, resp_good]

        with patch("src.v3.builder.run_in_sandbox") as mock_sandbox, \
             patch("src.v3.builder.scan_pptx") as mock_scanner:

            mock_exec = MagicMock()
            mock_exec.success = True
            mock_exec.ast_scan_ok = True
            mock_exec.pptx_path = str(tmp_path / "build" / "attempt_2" / "deck.pptx")
            mock_exec.to_report.return_value = {"success": True}
            mock_sandbox.return_value = mock_exec

            pptx_path = Path(mock_exec.pptx_path)
            pptx_path.parent.mkdir(parents=True, exist_ok=True)
            pptx_path.write_bytes(b"fake")

            mock_scanner.return_value = {"blocking_count": 0, "findings": []}

            result = build_deck(client, self._plan(), work_dir=tmp_path / "build")

        assert result.success is True
        assert len(result.attempts) == 2
        assert result.attempts[0].syntax_ok is False
        assert result.attempts[1].syntax_ok is True

    @patch("src.v3.builder.select_examples", return_value=[])
    def test_ast_scan_failure_triggers_retry(self, mock_select, tmp_path):
        code = "import os\nos.system('rm -rf /')"
        client = self._mock_client(code)

        with patch("src.v3.builder.run_in_sandbox") as mock_sandbox:
            mock_exec = MagicMock()
            mock_exec.success = False
            mock_exec.ast_scan_ok = False
            mock_exec.ast_violations = ["Disallowed import: os"]
            mock_exec.to_report.return_value = {"success": False}
            mock_sandbox.return_value = mock_exec

            result = build_deck(
                client, self._plan(),
                max_attempts=2,
                work_dir=tmp_path / "build",
            )

        # Both attempts fail (same code returned each time)
        assert result.success is False
        assert len(result.attempts) == 2
        assert not result.attempts[0].ast_scan_ok

    @patch("src.v3.builder.run_in_sandbox")
    @patch("src.v3.builder.select_examples", return_value=[])
    def test_exec_failure_triggers_retry(self, mock_select, mock_sandbox, tmp_path):
        code = "import sys\nraise ValueError('oops')"
        client = self._mock_client(code)

        mock_exec = MagicMock()
        mock_exec.success = False
        mock_exec.ast_scan_ok = True
        mock_exec.error = "Script exited with code 1"
        mock_exec.traceback_str = "ValueError: oops"
        mock_exec.stderr = "ValueError: oops"
        mock_exec.to_report.return_value = {"success": False}
        mock_sandbox.return_value = mock_exec

        result = build_deck(
            client, self._plan(),
            max_attempts=2,
            work_dir=tmp_path / "build",
        )

        assert result.success is False
        assert len(result.attempts) == 2

    @patch("src.v3.builder.scan_pptx")
    @patch("src.v3.builder.run_in_sandbox")
    @patch("src.v3.builder.select_examples", return_value=[])
    def test_scanner_blocking_triggers_retry(self, mock_select, mock_sandbox, mock_scanner, tmp_path):
        code = "import sys\nprint('OK')"
        client = self._mock_client(code)

        mock_exec = MagicMock()
        mock_exec.success = True
        mock_exec.ast_scan_ok = True
        mock_exec.pptx_path = str(tmp_path / "build" / "attempt_1" / "deck.pptx")
        mock_exec.to_report.return_value = {"success": True}
        mock_sandbox.return_value = mock_exec

        pptx_path = Path(mock_exec.pptx_path)
        pptx_path.parent.mkdir(parents=True, exist_ok=True)
        pptx_path.write_bytes(b"fake")

        # Scanner returns blocking findings
        mock_scanner.return_value = {
            "blocking_count": 1,
            "findings": [
                {"severity": "BLOCKING", "check_id": "VH-01", "message": "Off-canvas shape", "slide_index": 0}
            ],
        }

        result = build_deck(
            client, self._plan(),
            max_attempts=2,
            work_dir=tmp_path / "build",
        )

        assert result.success is False
        assert len(result.attempts) == 2
        assert "BLOCKING" in result.attempts[0].error

    @patch("src.v3.builder.select_examples", return_value=[])
    def test_llm_exception_stops_loop(self, mock_select, tmp_path):
        client = MagicMock()
        client.generate_code.side_effect = RuntimeError("API down")

        result = build_deck(
            client, self._plan(),
            work_dir=tmp_path / "build",
        )

        assert result.success is False
        assert "LLM call failed" in result.error
        assert len(result.attempts) == 0

    @patch("src.v3.builder.select_examples", return_value=[])
    def test_caller_is_builder(self, mock_select, tmp_path):
        code = "print('hi')"
        client = self._mock_client(code)

        with patch("src.v3.builder.run_in_sandbox") as mock_sandbox, \
             patch("src.v3.builder.scan_pptx") as mock_scanner:

            mock_exec = MagicMock()
            mock_exec.success = True
            mock_exec.ast_scan_ok = True
            mock_exec.pptx_path = str(tmp_path / "build" / "attempt_1" / "deck.pptx")
            mock_exec.to_report.return_value = {"success": True}
            mock_sandbox.return_value = mock_exec

            Path(mock_exec.pptx_path).parent.mkdir(parents=True, exist_ok=True)
            Path(mock_exec.pptx_path).write_bytes(b"fake")

            mock_scanner.return_value = {"blocking_count": 0, "findings": []}

            build_deck(client, self._plan(), work_dir=tmp_path / "build")

        # Verify the LLM call used caller="builder"
        call_kwargs = client.generate_code.call_args
        assert call_kwargs.kwargs.get("caller") == "builder" or \
               (len(call_kwargs.args) > 0 and "builder" in str(call_kwargs))
