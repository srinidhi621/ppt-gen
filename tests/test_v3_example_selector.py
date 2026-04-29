"""Tests for src.v3.example_selector — few-shot example selection."""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from src.v3.example_selector import (
    ExampleSnippet,
    _discover_examples,
    _load_snippet,
    _load_style,
    _rank_candidates,
    _score_style_match,
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


# ---------------------------------------------------------------------------
# Style-aware selection (PR-B-b)
# ---------------------------------------------------------------------------

@pytest.fixture
def styled_tree(tmp_path):
    """Library where process_flow has two examples with different styles."""
    fixtures = [
        # archetype, name, style block
        ("hero_title", "ex_a", {
            "tone": "executive_formal", "density": "low",
            "illustrative_richness": "minimal", "accent_strategy": "monochrome_plus_one",
        }),
        ("process_flow", "low_dense", {
            "tone": "executive_formal", "density": "low",
            "illustrative_richness": "minimal", "accent_strategy": "monochrome_plus_one",
        }),
        ("process_flow", "high_dense", {
            "tone": "executive_formal", "density": "high",
            "illustrative_richness": "minimal", "accent_strategy": "full_palette",
        }),
        # Third example with no style block, to test missing-style behavior.
        ("comparison_split", "no_style", None),
    ]
    for arch, name, style in fixtures:
        d = tmp_path / arch / name
        d.mkdir(parents=True)
        (d / "build.py").write_text(f"# {arch}/{name}\n")
        meta = {"archetype": arch}
        if style is not None:
            meta["style"] = style
        (d / "metadata.json").write_text(json.dumps(meta))
    return tmp_path


def _plan_with_style(archetypes, style_contract):
    plan = _plan(archetypes)
    plan["style_contract"] = style_contract
    return plan


class TestScoreStyleMatch:
    def test_full_match_scores_4(self):
        s = {"tone": "executive_formal", "density": "medium",
             "illustrative_richness": "minimal", "accent_strategy": "monochrome_plus_one"}
        assert _score_style_match(s, dict(s)) == 4.0

    def test_zero_match_scores_zero(self):
        plan = {"tone": "creative_bold", "density": "high",
                "illustrative_richness": "rich", "accent_strategy": "full_palette"}
        ex = {"tone": "executive_formal", "density": "low",
              "illustrative_richness": "minimal", "accent_strategy": "monochrome_plus_one"}
        # tone diff, density diff=2 (0.0), illust diff, accent diff → 0.0
        assert _score_style_match(plan, ex) == 0.0

    def test_density_one_step_partial_credit(self):
        plan = {"density": "medium"}
        ex_low = {"density": "low"}
        ex_high = {"density": "high"}
        ex_medium = {"density": "medium"}
        assert _score_style_match(plan, ex_medium) == 1.0
        assert _score_style_match(plan, ex_low) == 0.5
        assert _score_style_match(plan, ex_high) == 0.5

    def test_density_two_step_no_credit(self):
        assert _score_style_match({"density": "low"}, {"density": "high"}) == 0.0

    def test_empty_plan_or_example_returns_zero(self):
        assert _score_style_match({}, {"tone": "executive_formal"}) == 0.0
        assert _score_style_match({"tone": "executive_formal"}, {}) == 0.0
        assert _score_style_match({}, {}) == 0.0

    def test_missing_field_contributes_zero(self):
        # Plan has density only; example matches density only.
        assert _score_style_match({"density": "medium"}, {"density": "medium"}) == 1.0

    def test_unknown_density_value_contributes_zero(self):
        # "extreme" is not in the rank map, so the density dimension yields 0.
        assert _score_style_match({"density": "extreme"}, {"density": "high"}) == 0.0


class TestRankCandidates:
    def test_picks_better_match_first(self, styled_tree):
        plan_style = {"density": "high", "tone": "executive_formal",
                      "illustrative_richness": "minimal", "accent_strategy": "full_palette"}
        candidates = [
            styled_tree / "process_flow" / "low_dense",
            styled_tree / "process_flow" / "high_dense",
        ]
        ranked = _rank_candidates(candidates, plan_style)
        assert ranked[0].name == "high_dense"
        assert ranked[1].name == "low_dense"

    def test_no_plan_style_preserves_alpha_order(self, styled_tree):
        candidates = [
            styled_tree / "process_flow" / "low_dense",
            styled_tree / "process_flow" / "high_dense",
        ]
        # Empty plan style → input order preserved (alpha from sorted iterdir)
        assert _rank_candidates(candidates, {}) == candidates

    def test_tie_breaks_alphabetically(self, styled_tree):
        plan_style = {"density": "low", "tone": "executive_formal",
                      "illustrative_richness": "minimal", "accent_strategy": "monochrome_plus_one"}
        # Both score equally if styles match — but only low_dense matches here.
        # Add a same-score scenario via a twin.
        twin = styled_tree / "process_flow" / "alpha_first"
        twin.mkdir()
        (twin / "build.py").write_text("")
        (twin / "metadata.json").write_text(json.dumps({
            "archetype": "process_flow",
            "style": {"tone": "executive_formal", "density": "low",
                      "illustrative_richness": "minimal",
                      "accent_strategy": "monochrome_plus_one"},
        }))
        ranked = _rank_candidates(
            [styled_tree / "process_flow" / "low_dense", twin], plan_style
        )
        # Both score 4.0, alpha_first wins on name tiebreak.
        assert ranked[0].name == "alpha_first"


class TestStyleAwareSelection:
    def test_picks_high_density_example_for_high_density_plan(self, styled_tree):
        plan = _plan_with_style(["process_flow"], {
            "tone": "executive_formal", "density": "high",
            "illustrative_richness": "minimal", "accent_strategy": "full_palette",
        })
        snippets = select_examples(plan, max_examples=1, examples_dir=styled_tree)
        assert len(snippets) == 1
        assert snippets[0].name == "process_flow/high_dense"

    def test_picks_low_density_example_for_low_density_plan(self, styled_tree):
        plan = _plan_with_style(["process_flow"], {
            "tone": "executive_formal", "density": "low",
            "illustrative_richness": "minimal", "accent_strategy": "monochrome_plus_one",
        })
        snippets = select_examples(plan, max_examples=1, examples_dir=styled_tree)
        assert len(snippets) == 1
        assert snippets[0].name == "process_flow/low_dense"

    def test_no_style_contract_falls_back_to_alpha(self, styled_tree):
        plan = _plan(["process_flow"])  # no style_contract
        snippets = select_examples(plan, max_examples=1, examples_dir=styled_tree)
        # Alpha order: high_dense < low_dense, so high_dense wins.
        assert snippets[0].name == "process_flow/high_dense"

    def test_example_without_style_block_still_selectable(self, styled_tree):
        plan = _plan_with_style(["comparison_split"], {
            "tone": "executive_formal", "density": "medium",
            "illustrative_richness": "minimal", "accent_strategy": "full_palette",
        })
        snippets = select_examples(plan, max_examples=1, examples_dir=styled_tree)
        # Only one comparison_split example exists; it has no style block,
        # but selection must still return it (Phase 1 picks the only candidate).
        assert len(snippets) == 1
        assert snippets[0].archetype == "comparison_split"


class TestLoadStyle:
    def test_returns_style_block(self, styled_tree):
        style = _load_style(styled_tree / "process_flow" / "high_dense")
        assert style["density"] == "high"
        assert style["accent_strategy"] == "full_palette"

    def test_missing_style_returns_empty_dict(self, styled_tree):
        style = _load_style(styled_tree / "comparison_split" / "no_style")
        assert style == {}

    def test_missing_metadata_returns_empty_dict(self, tmp_path):
        assert _load_style(tmp_path / "nonexistent") == {}
