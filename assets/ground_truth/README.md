# Ground Truth Intake

Use this folder to collect and curate reference decks/slides that define the north star for quality.

## Folder Structure

- `internal_inbox/`: internal decks gathered from teams (redacted as needed)
- `external_inbox/`: public decks/slides gathered from external sources
- `curated/`: shortlisted final reference set used for benchmarking
- `annotations/`: structured metadata/labels for curated slides and decks

## Intake Rules

1. Do not place unredacted confidential client information in `internal_inbox/`.
2. Keep original source file names, but prepend date and category when possible.
3. Add one metadata note per deck in `annotations/` with:
- source (`internal` or `external`)
- category (`proposal_rfp`, `solution_approach`, etc.)
- confidentiality and usage status
- quality score and short rationale
4. Move only vetted high-quality samples from `*_inbox/` to `curated/`.

## Recommended Naming Convention

`YYYYMMDD_<category>_<org_or_source>_<short_title>.<ext>`

Example:

`20260303_proposal_rfp_acme_ai_modernization.pptx`
