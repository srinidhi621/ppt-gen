"""Tests for src.v3.example_selector — few-shot example selection."""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from src.v3.example_selector import (
    ExampleSnippet,
    _discover_examples,
    _load_snippet,
    format_examples_for_prompt,
    select_examples,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def example_tree(tmp_path):
    """Create a minimal example library structure."""
    for arch, names in [
        ("hero_title", ["ex_a"]),
        ("process_flow", ["ex_b", "ex_c"]),
        ("comparison_split", ["ex_d"]),
    ]:
        for name in names:
            d = tmp_path / arch / name
            d.mkdir(parents=True)
            (d / "build.py").write_text(f"# {arch}/{name}\nprint('hello')\n")
            (d / "metadata.json").write_text(json.dumps({"archetype": arch}))
    return tmp_path


def _plan(archetypes: list[str]) -> dict:
    """Build a minimal deck plan with the given archetypes."""
    return {
        "deck_id": "test",
        "deck_title": "Test Deck",
        "slides": [
            {"slide_id": f"s{i}", "archetype": arch, "headline": f"Slide {i}"}
            for i, arch in enumerate(archetypes, 1)
        ],
    }


# ---------------------------------------------------------------------------
# _discover_examples
# ---------------------------------------------------------------------------

class TestDiscoverExamples:
    def test_finds_all_examples(self, example_tree):
        lib = _discover_examples(example_tree)
        assert "hero_title" in lib
        assert "process_flow" in lib
        assert "comparison_split" in lib
        assert len(lib["process_flow"]) == 2

    def test_skips_dirs_without_build_py(self, example_tree):
        # Create dir without build.py
        incomplete = example_tree / "hero_title" / "incomplete"
        incomplete.mkdir()
        (incomplete / "metadata.json").write_text('{"archetype": "hero_title"}')

        lib = _discover_examples(example_tree)
        assert len(lib["hero_title"]) == 1  # Only ex_a

    def test_skips_hidden_dirs(self, example_tree):
        hidden = example_tree / ".hidden" / "ex"
        hidden.mkdir(parents=True)
        (hidden / "build.py").write_text("pass")
        (hidden / "metadata.json").write_text('{"archetype": "hidden"}')

        lib = _discover_examples(example_tree)
        assert "hidden" not in lib

    def test_nonexistent_dir_returns_empty(self, tmp_path):
        lib = _discover_examples(tmp_path / "nonexistent")
        assert lib == {}


# ---------------------------------------------------------------------------
# select_examples
# ---------------------------------------------------------------------------

class TestSelectExamples:
    def test_one_per_archetype(self, example_tree):
        plan = _plan(["hero_title", "process_flow", "comparison_split"])
        snippets = select_examples(plan, max_examples=3, examples_dir=example_tree)

        archetypes = [s.archetype for s in snippets]
        assert "hero_title" in archetypes
        assert "process_flow" in archetypes
        assert "comparison_split" in archetypes
        assert len(snippets) == 3

    def test_caps_at_max_examples(self, example_tree):
        plan = _plan(["hero_title", "process_flow", "comparison_split"])
        snippets = select_examples(plan, max_examples=2, examples_dir=example_tree)
        assert len(snippets) == 2

    def test_fills_with_extra_when_few_archetypes(self, example_tree):
        plan = _plan(["process_flow"])
        snippets = select_examples(plan, max_examples=3, examples_dir=example_tree)
        # Should get process_flow first, then fill from others
        assert len(snippets) >= 2  # process_flow + at least one more
        assert snippets[0].archetype == "process_flow"

    def test_deduplicates_plan_archetypes(self, example_tree):
        plan = _plan(["hero_title", "hero_title", "process_flow"])
        snippets = select_examples(plan, max_examples=3, examples_dir=example_tree)
        # hero_title appears once, process_flow once, then fills
        hero_count = sum(1 for s in snippets if s.archetype == "hero_title")
        assert hero_count == 1  # Not duplicated from plan

    def test_empty_plan_returns_some_examples(self, example_tree):
        plan = _plan([])
        snippets = select_examples(plan, max_examples=3, examples_dir=example_tree)
        # Phase 3 fills from any available
        assert len(snippets) >= 1

    def test_unknown_archetype_skipped(self, example_tree):
        plan = _plan(["nonexistent_type"])
        snippets = select_examples(plan, max_examples=3, examples_dir=example_tree)
        # Should still get examples from phase 3
        assert len(snippets) >= 1
        assert all(s.archetype != "nonexistent_type" for s in snippets)

    def test_code_is_loaded(self, example_tree):
        plan = _plan(["hero_title"])
        snippets = select_examples(plan, max_examples=1, examples_dir=example_tree)
        assert len(snippets) == 1
        assert "hero_title/ex_a" in snippets[0].code or "print" in snippets[0].code


# ---------------------------------------------------------------------------
# _load_snippet
# ---------------------------------------------------------------------------

class TestLoadSnippet:
    def test_reads_build_py(self, example_tree):
        ex_dir = example_tree / "hero_title" / "ex_a"
        snippet = _load_snippet(ex_dir, "hero_title")
        assert snippet is not None
        assert "hero_title" in snippet.name
        assert "print" in snippet.code

    def test_nonexistent_returns_none(self, tmp_path):
        snippet = _load_snippet(tmp_path / "nonexistent", "test")
        assert snippet is None


# ---------------------------------------------------------------------------
# format_examples_for_prompt
# ---------------------------------------------------------------------------

class TestFormatExamples:
    def test_empty_returns_empty(self):
        assert format_examples_for_prompt([]) == ""

    def test_formats_snippets(self):
        snippets = [
            ExampleSnippet("hero_title", "hero_title/ex_a", "print('hi')"),
        ]
        text = format_examples_for_prompt(snippets)
        assert "Example 1" in text
        assert "hero_title" in text
        assert "print('hi')" in text

    def test_multiple_examples_numbered(self):
        snippets = [
            ExampleSnippet("a", "a/1", "code_a"),
            ExampleSnippet("b", "b/2", "code_b"),
        ]
        text = format_examples_for_prompt(snippets)
        assert "Example 1" in text
        assert "Example 2" in text
