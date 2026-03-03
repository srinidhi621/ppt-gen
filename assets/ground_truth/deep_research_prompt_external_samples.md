# Prompt: External Ground-Truth Deck Research

You are a deep research agent supporting an AI consulting presentation-generation project.

Your task is to find public slide decks (or slide-by-slide reports) with top-tier consulting polish (McKinsey/BCG/Bain-level clarity and visual discipline) that fit one or more of these categories:

1. `proposal_rfp`
2. `solution_approach`
3. `case_study`
4. `gtm_offering`
5. `ai_strategy`
6. `opportunity_assessment`
7. `business_case_roi`
8. `responsible_ai_governance`
9. `data_ai_platform_blueprint`
10. `executive_steering_update`

## Search Scope

- Publicly accessible sources only.
- Prefer downloadable `PPTX` or `PDF` decks.
- Include high-quality slide repositories, conference decks, public consulting/industry reports with strong slide design, and procurement/proposal structures.
- Do not use private/shared-drive content.
- Do not copy proprietary text verbatim into output; summarize.

## Quality Bar (must evaluate each candidate)

Score each deck from 1-5 on:
1. Message clarity
2. Narrative flow
3. Visual hierarchy
4. Layout consistency
5. Evidence quality (charts/tables/claims)
6. Non-repetitive visual treatment

Only shortlist decks with average score >= 4.0.

## Output Requirements

Return both:

1. A `longlist` of at least 30 candidates.
2. A `shortlist` of 12 highest-quality candidates, with at least:
- 2 for `proposal_rfp`
- 2 for `solution_approach` or `ai_strategy`
- 2 for `case_study`
- 1 for `gtm_offering`
- 1 for `business_case_roi`
- 1 for `responsible_ai_governance`
- 1 for `data_ai_platform_blueprint`
- 1 for `executive_steering_update`
- 1 wildcard overlap deck

If exact category matches are rare, include closest proxies and explain the mapping.

## Required JSON Schema

```json
{
  "search_summary": {
    "date_utc": "string",
    "queries_used": ["string"],
    "source_types": ["string"],
    "limitations": ["string"]
  },
  "longlist": [
    {
      "title": "string",
      "url": "string",
      "publisher": "string",
      "year": "string",
      "format": "pptx|pdf|html|other",
      "categories": ["string"],
      "quality_scores": {
        "message_clarity": 0,
        "narrative_flow": 0,
        "visual_hierarchy": 0,
        "layout_consistency": 0,
        "evidence_quality": 0,
        "visual_non_repetition": 0,
        "average": 0
      },
      "why_relevant": "string",
      "license_or_usage_notes": "string",
      "downloadable": true
    }
  ],
  "shortlist": [
    {
      "title": "string",
      "url": "string",
      "best_fit_categories": ["string"],
      "what_to_learn": [
        "story structure pattern",
        "visual composition pattern",
        "evidence presentation pattern"
      ],
      "risks_or_caveats": "string"
    }
  ]
}
```

## Practical Guidance

- Favor recent materials where possible, but include older classics if visual/story quality is exceptional.
- Include at least 5 candidates from consulting or strategy firms and at least 5 from enterprise AI/data transformation case sources.
- Call out any source that looks polished but weak in evidence quality.
- Flag any source with unclear reuse rights.

Your output must be fact-based, link-heavy, and immediately usable for building a ground-truth corpus.
