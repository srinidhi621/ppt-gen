## Content

<!-- section_id: aws_landing_zone -->
## AWS Landing Zone Baseline
- Establish account, network, and security boundaries.
- Standardize deployment patterns across product teams.

---

<!-- section_id: aws_compute_data -->
## Compute and Data Plane
- Use EC2 and managed data services with private subnet routing.
- Keep observability and scaling controls explicit.

---

<!-- section_id: aws_governance -->
## AWS Governance Controls
- Enforce tagging, policy checks, and guardrails.
- Provide a reusable architecture template for new workloads.

## Visualization Cues

```json
{
  "cues": [
    {
      "section_id": "aws_landing_zone",
      "layout_hint": "content_image_light",
      "notes": "Prioritize AWS provider iconography for account and cloud boundary concepts.",
      "icon_hints": ["aws account cloud architecture"],
      "image_hint": null
    },
    {
      "section_id": "aws_compute_data",
      "layout_hint": "content_image_light",
      "notes": "Use AWS compute and subnet related icons.",
      "icon_hints": ["aws ec2 instance private subnet"],
      "image_hint": null
    },
    {
      "section_id": "aws_governance",
      "layout_hint": "two_content_image_light",
      "notes": "Use AWS governance and cloud operations visual symbols.",
      "icon_hints": ["aws cloud policy security operations"],
      "image_hint": null
    }
  ]
}
```
