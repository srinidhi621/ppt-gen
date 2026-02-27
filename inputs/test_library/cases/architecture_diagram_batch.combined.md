## Content

<!-- section_id: arch_overview -->
## Platform Architecture Overview
- Describe service boundaries, ingress, and core processing components.
- Keep flow direction left-to-right.

---

<!-- section_id: arch_data_flow -->
## Data Flow and Processing Stages
- Capture source systems, transformation stages, and downstream consumers.
- Highlight one bottleneck and one resilience control.

---

<!-- section_id: arch_sequence -->
## Critical Request Sequence
- Show user request, API handling, orchestration, and persistence steps.
- Include success path and one retry/failure branch.

## Visualization Cues

```json
{
  "cues": [
    {
      "section_id": "arch_overview",
      "layout_hint": "content_image_light",
      "notes": "Intended for MCP diagram generation. Use architecture overview style with groups and orthogonal connectors.",
      "icon_hints": ["architecture", "service", "network", "cloud"],
      "image_hint": "Clean architecture diagram placeholder with bounded groups",
      "diagram_request": {
        "diagram_id": "arch_overview_001",
        "diagram_type": "architecture_overview",
        "layout_direction": "LR",
        "output_format": "png",
        "embed_xml": true,
        "components": [
          "API Gateway",
          "Orchestrator",
          "Rules Engine",
          "Data Store",
          "Observability"
        ]
      }
    },
    {
      "section_id": "arch_data_flow",
      "layout_hint": "two_content_image_light",
      "notes": "Intended for MCP diagram generation. Use data-flow style with directional edges.",
      "icon_hints": ["data", "pipeline", "integration", "lineage"],
      "image_hint": "Data flow diagram placeholder with three processing stages",
      "diagram_request": {
        "diagram_id": "arch_data_flow_001",
        "diagram_type": "data_flow",
        "layout_direction": "TB",
        "output_format": "png",
        "embed_xml": true,
        "stages": [
          "Ingest",
          "Transform",
          "Serve"
        ]
      }
    },
    {
      "section_id": "arch_sequence",
      "layout_hint": "content_image_light",
      "notes": "Intended for MCP diagram generation. Use sequence style with explicit actors and message labels.",
      "icon_hints": ["sequence", "request", "response", "retry"],
      "image_hint": "Sequence diagram placeholder showing request-response path",
      "diagram_request": {
        "diagram_id": "arch_sequence_001",
        "diagram_type": "sequence",
        "layout_direction": "TB",
        "output_format": "png",
        "embed_xml": true,
        "actors": [
          "User",
          "Web App",
          "API",
          "Worker",
          "Database"
        ]
      }
    }
  ]
}
```
