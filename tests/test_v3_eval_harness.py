"""Tests for V3 eval harness prompt loading."""

from __future__ import annotations

from scripts.run_v3_eval_prompts import (
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
