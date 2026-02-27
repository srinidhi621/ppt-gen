# CLAUDE.md — Repo Quick Guide

## Environment

```bash
source .venv/bin/activate
set -a && source .env && set +a
```

## Runtime Commands

Validate template/catalog:

```bash
python -m src.cli validate
```

Single-pass generation:

```bash
python -m src.cli generate --input inputs/legacy-system-navigator.combined.md --run-id run_single
```

Full one-loop generation:

```bash
python -m src.cli generate-auto --input inputs/legacy-system-navigator.combined.md --run-id run_auto
```

## Tests

```bash
python -m pytest -q
```

## Notes

- Default review-image conversion uses `soffice` + `pdftoppm` (headless).
- Core contracts are documented in `SPEC.md`.
- Active quality-recovery work is tracked in `PLAN.md`.
- Follow `AGENTS.md` as operational policy.

