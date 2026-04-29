"""Tests for V3 eval harness prompt loading."""

from __future__ import annotations

from scripts.run_v3_eval_prompts import (
    _extract_blocking_count,
    _row_key,
    compose_multislide_instruction,
    load_multislide_tests,
    load_prompt_records,
)


def test_multislide_harness_loads_rows():
    tests = load_multislide_tests()

    assert {t["test_id"] for t in tests} == {"MS-01", "MS-02"}
    assert all(t["slides"] for t in tests)
    assert all("deck_brief" in t for t in tests)


def test_multislide_instruction_contains_slide_content_without_answer_link():
    test = next(t for t in load_multislide_tests() if t["test_id"] == "MS-02")

    instruction = compose_multislide_instruction(test)

    assert "Slide 1:" in instruction
    assert "Slide 7:" in instruction
    assert "10x AI Engineering Approach" in instruction
    assert "Visual cues:" in instruction
    assert "assets/ground_truth" not in instruction
    assert ".pptx" not in instruction


def test_load_prompt_records_supports_standard_and_multislide():
    standard = load_prompt_records("standard")
    multislide = load_prompt_records("multislide")

    assert any(r["test_id"] == "TP-21" for r in standard)
    assert [r["test_id"] for r in multislide] == ["MS-01", "MS-02"]
    assert all(r["expected_slides"] != "1" for r in multislide)


# ---------------------------------------------------------------------------
# Multi-run helpers (PR-D-c)
# ---------------------------------------------------------------------------

class TestExtractBlockingCount:
    def test_success_run_returns_zero(self):
        assert _extract_blocking_count("", success=True) == 0
        # Even with a stray error string, success means no blockers.
        assert _extract_blocking_count("anything", success=True) == 0

    def test_parses_count_from_scanner_error(self):
        err = "All 3 build attempts failed; last error: Scanner found 7 BLOCKING finding(s)"
        assert _extract_blocking_count(err, success=False) == 7

    def test_parses_double_digit_count(self):
        err = "Scanner found 24 BLOCKING finding(s)"
        assert _extract_blocking_count(err, success=False) == 24

    def test_parses_zero_blocking_in_failure(self):
        # Edge case: technically failed but scanner reported 0 (e.g.
        # validator failure rather than scanner failure).
        err = "Scanner found 0 BLOCKING finding(s)"
        assert _extract_blocking_count(err, success=False) == 0

    def test_returns_none_for_non_scanner_failure(self):
        # LLM timeout, sandbox error — no BLOCKING count to surface.
        assert _extract_blocking_count(
            "LLM call failed: Network error: read timeout", success=False
        ) is None
        assert _extract_blocking_count("", success=False) is None
        assert _extract_blocking_count(
            "syntax error: unclosed paren at line 200", success=False
        ) is None


class TestRowKey:
    def test_single_run_uses_test_id_directly(self):
        # Backward compatibility: 1-run mode keeps the historic key shape
        # so old manifests can be read without migration.
        assert _row_key("MS-01", 1, total_runs=1) == "MS-01"

    def test_multi_run_appends_index(self):
        assert _row_key("MS-01", 1, total_runs=3) == "MS-01__r1"
        assert _row_key("MS-01", 3, total_runs=3) == "MS-01__r3"

    def test_keys_are_distinct_across_runs(self):
        keys = {_row_key("MS-01", i, total_runs=5) for i in range(1, 6)}
        assert len(keys) == 5
