"""Tests for src.v3.builder — code generation, extraction, prompt assembly."""

from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.v3.builder import (
    assemble_user_message,
    build_deck,
    check_syntax,
    extract_code,
)
from src.v3.example_selector import ExampleSnippet
from src.v3.llm_client import LLMInfraError


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

        # Mock sandbox success — side_effect creates the expected PPTX
        def _sandbox_side_effect(script_path, **kwargs):
            # The builder passes script_args=[str(expected_output)]
            out = Path(kwargs["script_args"][0])
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(b"fake pptx")
            mock_exec = MagicMock()
            mock_exec.success = True
            mock_exec.ast_scan_ok = True
            mock_exec.to_report.return_value = {"success": True}
            return mock_exec

        mock_sandbox.side_effect = _sandbox_side_effect

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

            def _sandbox_side_effect(script_path, **kwargs):
                out = Path(kwargs["script_args"][0])
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(b"fake")
                mock_exec = MagicMock()
                mock_exec.success = True
                mock_exec.ast_scan_ok = True
                mock_exec.to_report.return_value = {"success": True}
                return mock_exec

            mock_sandbox.side_effect = _sandbox_side_effect
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

        def _sandbox_side_effect(script_path, **kwargs):
            out = Path(kwargs["script_args"][0])
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(b"fake")
            mock_exec = MagicMock()
            mock_exec.success = True
            mock_exec.ast_scan_ok = True
            mock_exec.to_report.return_value = {"success": True}
            return mock_exec

        mock_sandbox.side_effect = _sandbox_side_effect

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
        client.generate_code.side_effect = LLMInfraError("API down")

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

            def _sandbox_side_effect(script_path, **kwargs):
                out = Path(kwargs["script_args"][0])
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(b"fake")
                mock_exec = MagicMock()
                mock_exec.success = True
                mock_exec.ast_scan_ok = True
                mock_exec.to_report.return_value = {"success": True}
                return mock_exec

            mock_sandbox.side_effect = _sandbox_side_effect
            mock_scanner.return_value = {"blocking_count": 0, "findings": []}

            build_deck(client, self._plan(), work_dir=tmp_path / "build")

        # Verify the LLM call used caller="builder"
        call_kwargs = client.generate_code.call_args
        assert call_kwargs.kwargs.get("caller") == "builder" or \
               (len(call_kwargs.args) > 0 and "builder" in str(call_kwargs))


# ---------------------------------------------------------------------------
# Regression tests for PR #9 review fixes
# ---------------------------------------------------------------------------

class TestBuildDeckRegressions:
    """Regression tests for bugs found during PR #9 review."""

    def _plan(self):
        return {
            "deck_id": "test",
            "deck_title": "Test",
            "slides": [{"slide_id": "s1", "archetype": "hero_title", "headline": "Hi"}],
        }

    def _mock_client(self, code_text: str):
        client = MagicMock()
        resp = MagicMock()
        resp.text = code_text
        resp.usage = MagicMock(input_tokens=100, output_tokens=200)
        client.generate_code.return_value = resp
        return client

    @patch("src.v3.builder.scan_pptx")
    @patch("src.v3.builder.run_in_sandbox")
    @patch("src.v3.builder.select_examples", return_value=[])
    def test_scanner_exception_triggers_retry(self, mock_select, mock_sandbox, mock_scanner, tmp_path):
        """Fix #1: scanner crash must fail the attempt and retry, not pass silently."""
        code = "import sys\nprint('OK')"
        client = self._mock_client(code)

        def _sandbox_side_effect(script_path, **kwargs):
            out = Path(kwargs["script_args"][0])
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(b"fake")
            mock_exec = MagicMock()
            mock_exec.success = True
            mock_exec.ast_scan_ok = True
            mock_exec.to_report.return_value = {"success": True}
            return mock_exec

        mock_sandbox.side_effect = _sandbox_side_effect
        mock_scanner.side_effect = ValueError("corrupt PPTX XML")

        result = build_deck(
            client, self._plan(),
            max_attempts=2,
            work_dir=tmp_path / "build",
        )

        assert result.success is False
        assert len(result.attempts) == 2
        assert "Scanner crashed" in result.attempts[0].error

    @patch("src.v3.builder.run_in_sandbox")
    @patch("src.v3.builder.select_examples", return_value=[])
    def test_missing_output_file_triggers_retry(self, mock_select, mock_sandbox, tmp_path):
        """Fix #2: script exits 0 but doesn't write to expected path → retry."""
        code = "import sys\nprint('OK')"
        client = self._mock_client(code)

        # Sandbox succeeds but does NOT create the expected output file
        mock_exec = MagicMock()
        mock_exec.success = True
        mock_exec.ast_scan_ok = True
        mock_exec.to_report.return_value = {"success": True}
        mock_sandbox.return_value = mock_exec

        result = build_deck(
            client, self._plan(),
            max_attempts=2,
            work_dir=tmp_path / "build",
        )

        assert result.success is False
        assert len(result.attempts) == 2
        assert "expected output path" in result.attempts[0].error

    @patch("src.v3.builder.select_examples", return_value=[])
    def test_exhaustion_preserves_last_error(self, mock_select, tmp_path):
        """Fix #7: exhaustion message must include last attempt's error."""
        code = "import sys\nraise ValueError('oops')"
        client = self._mock_client(code)

        with patch("src.v3.builder.run_in_sandbox") as mock_sandbox:
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
        assert "last error:" in result.error

    @patch("src.v3.builder.select_examples", return_value=[])
    def test_narrow_llm_catch_allows_unexpected_errors(self, mock_select, tmp_path):
        """Fix #5: unexpected errors (not LLMError/ValueError) must propagate."""
        client = MagicMock()
        client.generate_code.side_effect = RuntimeError("Unexpected bug")

        with pytest.raises(RuntimeError, match="Unexpected bug"):
            build_deck(client, self._plan(), work_dir=tmp_path / "build")

    @patch("src.v3.builder.run_in_sandbox")
    @patch("src.v3.builder.select_examples", return_value=[])
    def test_stale_attempt_dir_cleaned(self, mock_select, mock_sandbox, tmp_path):
        """Fix #6: stale attempt dirs are cleaned before reuse."""
        work_dir = tmp_path / "build"
        attempt_dir = work_dir / "attempt_01"
        attempt_dir.mkdir(parents=True)
        stale_file = attempt_dir / "old_deck.pptx"
        stale_file.write_bytes(b"stale")

        code = "print('hi')"
        client = self._mock_client(code)

        mock_exec = MagicMock()
        mock_exec.success = False
        mock_exec.ast_scan_ok = True
        mock_exec.error = "fail"
        mock_exec.traceback_str = ""
        mock_exec.stderr = ""
        mock_exec.to_report.return_value = {"success": False}
        mock_sandbox.return_value = mock_exec

        build_deck(client, self._plan(), max_attempts=1, work_dir=work_dir)

        # The stale file should be gone (dir was cleaned and recreated)
        assert not stale_file.exists()
        # But the attempt dir itself should exist (recreated)
        assert attempt_dir.exists()

    def test_prompt_no_os_environ(self):
        """Fix #4: prompt must not instruct LLM to use os.environ (blocked by AST scanner)."""
        from src.v3.builder import assemble_user_message
        plan = self._plan()
        msg = assemble_user_message(plan, [])
        assert "os.environ" not in msg
        assert "src.ppt_runtime" in msg  # uses module-path derivation instead


# ---------------------------------------------------------------------------
# extract_code edge cases (Fix #8)
# ---------------------------------------------------------------------------

class TestExtractCodeEdgeCases:
    def test_nested_fences(self):
        """Code containing triple backticks inside strings."""
        text = '```python\ncode = """\\n```\\n"""\nprint(code)\n```'
        result = extract_code(text)
        assert "print(code)" in result

    def test_multiple_languages(self):
        """Only the Python-fenced block should be picked if it's longest."""
        text = (
            "```json\n{\"a\": 1}\n```\n\n"
            "```python\nimport sys\nprint(sys.argv)\ndo_stuff()\n```"
        )
        result = extract_code(text)
        assert "import sys" in result
        assert "do_stuff" in result

    def test_code_with_blank_lines(self):
        text = "```python\nimport sys\n\n\nprint('hello')\n```"
        result = extract_code(text)
        assert "import sys" in result
        assert "print('hello')" in result

    def test_only_whitespace_inside_fences(self):
        text = "```python\n   \n```"
        result = extract_code(text)
        assert result == ""

    def test_python_fence_preferred_over_generic(self):
        """Python-tagged fence is preferred even if a generic fence is longer."""
        text = (
            "```\nthis is not python at all and is very long text here\n```\n\n"
            "```python\nprint('hi')\n```"
        )
        result = extract_code(text)
        assert result == "print('hi')"

    def test_parseable_fence_preferred_over_unparseable(self):
        """When multiple fenced blocks exist, prefer one that parses as Python."""
        text = (
            "```python\ndef f(\n  bad syntax\n```\n\n"
            "```python\nimport sys\nprint(sys.argv)\n```"
        )
        result = extract_code(text)
        assert "import sys" in result

    def test_unparseable_python_returned_when_only_option(self):
        """If all python fences have syntax errors, return the longest for error reporting."""
        text = "```python\ndef f(\n  pass\n```"
        result = extract_code(text)
        assert "def f(" in result


# ---------------------------------------------------------------------------
# Additional edge case tests (review #10)
# ---------------------------------------------------------------------------

class TestBuildDeckEdgeCases:
    """Tests for boundary conditions and single-attempt behavior."""

    def _plan(self):
        return {
            "deck_id": "test",
            "deck_title": "Test",
            "slides": [{"slide_id": "s1", "archetype": "hero_title", "headline": "Hi"}],
        }

    @patch("src.v3.builder.run_in_sandbox")
    @patch("src.v3.builder.select_examples", return_value=[])
    def test_max_attempts_1_single_failure(self, mock_select, mock_sandbox, tmp_path):
        """max_attempts=1 means exactly one try — no retries."""
        code = "import sys\nraise ValueError('oops')"
        client = MagicMock()
        resp = MagicMock()
        resp.text = code
        resp.usage = MagicMock(input_tokens=10, output_tokens=20)
        client.generate_code.return_value = resp

        mock_exec = MagicMock()
        mock_exec.success = False
        mock_exec.ast_scan_ok = True
        mock_exec.error = "Script exited with code 1"
        mock_exec.traceback_str = "ValueError: oops"
        mock_exec.stderr = ""
        mock_exec.to_report.return_value = {"success": False}
        mock_sandbox.return_value = mock_exec

        result = build_deck(
            client, self._plan(),
            max_attempts=1,
            work_dir=tmp_path / "build",
        )

        assert result.success is False
        assert len(result.attempts) == 1
        assert client.generate_code.call_count == 1
        assert "last error:" in result.error

    @patch("src.v3.builder.scan_pptx")
    @patch("src.v3.builder.run_in_sandbox")
    @patch("src.v3.builder.select_examples", return_value=[])
    def test_max_attempts_1_success(self, mock_select, mock_sandbox, mock_scanner, tmp_path):
        """max_attempts=1 can succeed on the first try."""
        code = "import sys\nprint('OK')"
        client = MagicMock()
        resp = MagicMock()
        resp.text = code
        resp.usage = MagicMock(input_tokens=10, output_tokens=20)
        client.generate_code.return_value = resp

        def _sandbox_side_effect(script_path, **kwargs):
            out = Path(kwargs["script_args"][0])
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(b"fake")
            mock_exec = MagicMock()
            mock_exec.success = True
            mock_exec.ast_scan_ok = True
            mock_exec.to_report.return_value = {"success": True}
            return mock_exec

        mock_sandbox.side_effect = _sandbox_side_effect
        mock_scanner.return_value = {"blocking_count": 0, "findings": []}

        result = build_deck(
            client, self._plan(),
            max_attempts=1,
            work_dir=tmp_path / "build",
        )

        assert result.success is True
        assert len(result.attempts) == 1

    def test_attempt_dirs_zero_padded(self, tmp_path):
        """Attempt directories use zero-padded names (attempt_01, attempt_02)."""
        code = "print('hi')"
        client = MagicMock()
        resp = MagicMock()
        resp.text = code
        resp.usage = MagicMock(input_tokens=10, output_tokens=20)
        client.generate_code.return_value = resp

        with patch("src.v3.builder.run_in_sandbox") as mock_sandbox, \
             patch("src.v3.builder.select_examples", return_value=[]):
            mock_exec = MagicMock()
            mock_exec.success = False
            mock_exec.ast_scan_ok = True
            mock_exec.error = "fail"
            mock_exec.traceback_str = ""
            mock_exec.stderr = ""
            mock_exec.to_report.return_value = {"success": False}
            mock_sandbox.return_value = mock_exec

            build_deck(client, self._plan(), max_attempts=2, work_dir=tmp_path / "build")

        assert (tmp_path / "build" / "attempt_01").exists()
        assert (tmp_path / "build" / "attempt_02").exists()
        assert not (tmp_path / "build" / "attempt_1").exists()
