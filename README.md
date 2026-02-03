# PPT-Gen: LLM-Assisted PowerPoint Generator

A programmable system that generates **tasteful, on-brand, editable PPTX presentations** using an LLM for planning and `python-pptx` for deterministic rendering.

## Overview

PPT-Gen takes:
- A **corporate PowerPoint template** (theme + masters + curated layouts)
- An **icon pack** (PNG format)
- **Written content** (Markdown)
- **Visualization cues** (structured hints)

...and generates professional presentations by:
1. Using an LLM for **planning** (slide outline, layout selection, concise bullets, icon selection)
2. Using deterministic logic for **fit validation** (preventing text overflow)
3. Using `python-pptx` as a **deterministic renderer**
4. Optionally iterating via a **vision-based critique loop** for quality refinement

## Key Features

- **Template-first rendering**: Preserves corporate theme, fonts, colors, and master slide formatting
- **Placeholder binding via Alt-Text**: Deterministic mapping of content to template placeholders
- **Preflight validation**: Prevents text overflow before rendering (no "auto-fit" assumptions)
- **Pressure valve mechanism**: Excess content moves to speaker notes rather than shrinking text
- **Vision critique loop**: Optional LLM-powered review to catch visual issues

## Project Status

| Phase | Task | Status |
|-------|------|--------|
| 0.1 | Template selection | ✅ Done |
| 0.2 | SVG → PNG icon conversion | ✅ Done |
| 0.3 | Directory structure | ✅ Done |
| 0.4 | Template analysis | ✅ Done |
| 0.5 | Alt-Text placeholder tagging | ✅ Done |
| 0.6 | Layout catalog generation | ✅ Done |
| 1.x | MVP Pipeline | ✅ Done |
| 2.x | LLM Planning + Review Loop | ⏳ Pending |

## Repository Structure

```
ppt-gen/
├── SPEC.md                    # Contract specification
├── PLAN.md                    # Implementation plan
├── AGENTS.md                  # Agent operating guide
│
├── assets/
│   ├── template/
│   │   └── template.pptx      # Corporate template (118 layouts, 387 placeholders)
│   ├── icons/
│   │   ├── icons.json         # Icon metadata (213 icons)
│   │   └── png/               # 512x512 PNG icons
│   └── layout/
│       └── layout_catalog.json  # Layout definitions (12 MVP layouts)
│
├── scripts/
│   ├── inspect_template.py    # Template analysis tool
│   ├── convert_svg_to_png.py  # SVG to PNG converter
│   └── add_alt_text.py        # Automated alt-text assignment
│
├── inputs/                    # Runtime inputs
│   ├── content.md
│   └── cues.json
│
└── runs/<run_id>/             # Output artifacts
```

## Quick Start

### Prerequisites

- Python 3.10+
- PowerPoint (for manual review/export)

### Setup

```bash
# Clone the repository
git clone https://github.com/srinidhi621/ppt-gen.git
cd ppt-gen

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install python-pptx
```

### CLI Commands

**Validate template against layout catalog:**
```bash
python -m src.cli validate
```

**Render a DeckIR JSON to PPTX:**
```bash
python -m src.cli render --deckir inputs/sample_deckir.json
```

**Run smoke test (validate → preflight → render):**
```bash
python -m src.cli smoke --deckir inputs/sample_deckir.json
```

**Run tests:**
```bash
python -m pytest tests/ -v
```

### Utility Scripts

**Analyze template:**
```bash
python scripts/inspect_template.py assets/template/template.pptx
```

**Add alt-text to placeholders (if needed):**
```bash
python scripts/add_alt_text.py              # Apply to all layouts
python scripts/add_alt_text.py --dry-run    # Preview without changes
python scripts/add_alt_text.py --mvp-only   # Only MVP layouts
```

## Architecture

### Pipeline Layers

1. **Layer 0: Config** - Load template paths, model config, defaults
2. **Layer 1: Normalize** - Parse Markdown into ContentModel
3. **Layer 2: Plan** - LLM generates DeckIR (intermediate representation)
4. **Layer 3: Validate** - Preflight fit checks + remediation
5. **Layer 4: Render** - python-pptx generates PPTX
6. **Layer 5: Review** - Manual slide image export
7. **Layer 6: Critique** - Vision model produces CritiqueReport
8. **Layer 7: Patch** - Apply fixes and re-render

### Field Key Convention

Placeholders are bound via alt-text with canonical `field_key` values:

| Placeholder Type | Single | Multiple |
|-----------------|--------|----------|
| Title | `ph_title` | — |
| Subtitle | `ph_subtitle` | — |
| Body/Content | `ph_body` | `ph_body_left`, `ph_body_right` or `ph_col1`, `ph_col2`, ... |
| Image | `ph_image` | `ph_image_left`, `ph_image_right` or `ph_image_1`, `ph_image_2`, ... |

## Documentation

- [SPEC.md](SPEC.md) - Full technical specification and data contracts
- [PLAN.md](PLAN.md) - Implementation plan with task tracking
- [AGENTS.md](AGENTS.md) - Operating guide for AI coding agents

## Design Principles

1. **No auto-layout assumptions**: python-pptx doesn't auto-fit text, so we validate before rendering
2. **Template fidelity**: Rely on PowerPoint template styling, avoid manual font/color overrides
3. **Deterministic rendering**: Same DeckIR + template = same output
4. **Graceful degradation**: Overflow goes to speaker notes, not tiny unreadable text
5. **Fail fast**: Validate template/catalog match at startup

## License

Private project - All rights reserved.

## Author

Srinidhi (srinidhi621@gmail.com)
