## Content

<!-- section_id: hybrid_reference -->
## Hybrid Cloud Reference Pattern
- Keep core workloads in AWS while integrating Microsoft-centric enterprise workflows.
- Use a clear boundary between platform services and user productivity systems.

---

<!-- section_id: hybrid_security -->
## Security and Compliance Layer
- Unify policy, identity, and audit signals across providers.
- Keep controls simple enough for operations teams to reason about quickly.

---

<!-- section_id: hybrid_data_flow -->
## Data and Event Flow
- Route business events from core services to collaboration channels.
- Preserve traceability and ownership across handoffs.

---

<!-- section_id: hybrid_runbook -->
## Hybrid Operations Runbook
- Define repeatable onboarding steps for each product team.
- Include incident, release, and change-management standards.

## Visualization Cues

```json
{
  "cues": [
    {
      "section_id": "hybrid_reference",
      "layout_hint": "content_image_light",
      "notes": "Use mixed AWS and Fluent icon semantics to indicate cross-provider architecture.",
      "icon_hints": ["aws cloud fluent enterprise hybrid architecture"],
      "image_hint": null
    },
    {
      "section_id": "hybrid_security",
      "layout_hint": "content_image_light",
      "notes": "Security and compliance symbols should be explicit and low-noise.",
      "icon_hints": ["aws security fluent shield audit"],
      "image_hint": null
    },
    {
      "section_id": "hybrid_data_flow",
      "layout_hint": "two_content_image_light",
      "notes": "Show flow-oriented iconography that implies integration and event motion.",
      "icon_hints": ["aws data flow fluent arrow integration"],
      "image_hint": null
    },
    {
      "section_id": "hybrid_runbook",
      "layout_hint": "content_image_light",
      "notes": "Use iconography for process and operations playbooks.",
      "icon_hints": ["fluent task list aws operations"],
      "image_hint": null
    }
  ]
}
```
