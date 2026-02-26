# diagrams-map-approach.md
**Goal:** Fully headless, deterministic diagram generation for an automated PPT deck pipeline.  
**Constraints:**  
- No human review, no editor UI, no “open diagram in draw.io” step  
- Pipeline needs a single tool call from the agent layer (your backend can orchestrate multiple internal steps)  
- Output must be ready-to-insert **PNG** (preferred for python-pptx) and also preserve **editable source**  
- Must support an automated “vision QA → targeted fixes → regenerate” loop  
- Must be self-hostable / offline-friendly

---

## 1) Recommended approach (best fit for your flow)

### 1.1 Choose: **Programmatic XML generator + headless renderer**
**Use:**
- **`yohasacura/drawio-mcp`** to generate/modify **draw.io / diagrams.net XML** programmatically (headless MCP server).  [oai_citation:0‡GitHub](https://github.com/yohasacura/drawio-mcp?utm_source=chatgpt.com)  
- **`jgraph/draw-image-export2`** to render XML to **PNG** (server-side export) with options like `embedXml` and `base64`.  [oai_citation:1‡GitHub](https://github.com/jgraph/draw-image-export2?utm_source=chatgpt.com)  
- Store outputs as:
  - `diagram.drawio.xml` (source of truth)
  - `diagram.png` with embedded XML (`embedXml=1`) so it can be reopened if ever needed.  [oai_citation:2‡GitHub](https://github.com/jgraph/draw-image-export2?utm_source=chatgpt.com)

**Why this matches your flow**
- `yohasacura/drawio-mcp` is explicitly “generates draw.io / diagrams.net XML programmatically” and works with MCP-compatible clients.  [oai_citation:3‡GitHub](https://github.com/yohasacura/drawio-mcp?utm_source=chatgpt.com)  
- `draw-image-export2` is explicitly intended for server-side rendering and documents the rendering parameters you need.  [oai_citation:4‡GitHub](https://github.com/jgraph/draw-image-export2?utm_source=chatgpt.com)  
- diagrams.net supports embedding the XML inside PNG (`zTxt`) and the export stack supports PNG/SVG with embedded XML.  [oai_citation:5‡draw.io](https://www.drawio.com/blog/xml-in-png?utm_source=chatgpt.com)

### 1.2 Avoid (for your case): editor-coupled official MCP
The official draw.io MCP server is positioned around creating diagrams and opening them in the draw.io editor. That is not aligned with “no UI, seamless automation.”  [oai_citation:6‡GitHub](https://github.com/jgraph/drawio-mcp?utm_source=chatgpt.com)

---

## 2) High-level architecture

### 2.1 Services (self-hosted)
1) **Diagram Compiler Service (you build)**
   - Exposes one MCP tool (or one internal API endpoint) that the agent calls once per deck.
   - Internally orchestrates:
     1) IR → draw.io XML (via yohasacura/drawio-mcp)
     2) XML → PNG (via jgraph/draw-image-export2)
   - Returns `{xml, png_base64, width, height, warnings}` for each diagram.

2) **drawio-mcp (yohasacura)**
   - Headless MCP server that produces and edits draw.io XML.  [oai_citation:7‡GitHub](https://github.com/yohasacura/drawio-mcp?utm_source=chatgpt.com)

3) **draw-image-export2 (jgraph)**
   - Headless export server that renders PNG/PDF/SVG from draw.io data and supports `embedXml` and `base64`.  [oai_citation:8‡GitHub](https://github.com/jgraph/draw-image-export2?utm_source=chatgpt.com)

4) **Vision QA component (your existing plan)**
   - Looks at the placed PNG inside the slide to detect layout issues.
   - Emits patch suggestions (preferably against your IR, not raw XML).

---

## 3) Deterministic artifact strategy

### 3.1 Canonical source: **Diagram IR**
Do **not** generate raw draw.io XML directly from the LLM as the primary output. Instead:
- LLM produces a structured **Diagram IR** (nodes, edges, groups, lanes, layout intent, style profile).
- Compiler converts IR → XML deterministically.
- Vision QA patches the IR (or patches the compiler inputs), then regenerate.

**Reason:** XML is verbose and brittle to patch. A stable IR makes targeted fixes reliable.

### 3.2 Store these artifacts per diagram
- `diagram.ir.json` (your schema)
- `diagram.drawio.xml` (compiled)
- `diagram.png` (rendered, ideally with embedded XML)
- `diagram.qa.json` (vision feedback + applied patches)
- `diagram.render.json` (compiler warnings + dimensions)

### 3.3 Embed XML in PNG (recommended)
Use `draw-image-export2` with:
- `format=png`
- `embedXml=1` (embed diagram data into PNG)
- `base64=1` (easy transport)
These are documented parameters.  [oai_citation:9‡GitHub](https://github.com/jgraph/draw-image-export2?utm_source=chatgpt.com)  
diagrams.net blog confirms embedded XML in PNG is supported via PNG metadata `zTxt`.  [oai_citation:10‡draw.io](https://www.drawio.com/blog/xml-in-png?utm_source=chatgpt.com)

---

## 4) The “one external call” design

### 4.1 Batch-by-deck tool contract
You only get one external call from the agent layer. Make that call **batch** all diagrams for the deck:

**Tool:** `render_drawio_diagrams_batch`

**Input:** `{deck_id, style_profile, diagrams:[{diagram_id, type, ir_spec, output_opts}]}`  
**Output:** `[{diagram_id, xml, png_base64, width, height, warnings}]`

### 4.2 Your backend can do multiple internal steps
Even if the agent can only make one call, your backend service can:
- call `drawio-mcp` internally
- call `draw-image-export2` internally
This keeps the LLM-agent contract “one call” while still enabling robust orchestration.

---

## 5) Render format guidance for PPT insertion

### 5.1 Prefer PNG for python-pptx insertion
PNG is the simplest and most predictable for python-pptx.
- Use transparent background if your corporate template uses colored slide backgrounds.
- Use solid background if your template uses gradients that cause haloing artifacts.

### 5.2 When to use SVG
SVG can be useful if you need:
- hyperlinks embedded in the diagram
- high-fidelity vector scaling
But note diagrams.net SVG export uses foreignObject in some cases; compatibility varies.  [oai_citation:11‡jgraph.github.io](https://jgraph.github.io/drawio-integration/?utm_source=chatgpt.com)  
For PPT generation, PNG is usually the pragmatic default.

---

## 6) Vision QA → targeted fixes loop

### 6.1 Vision QA checks (minimum)
- Text overlap
- Edge crossings above threshold
- Node overlap
- Labels too long for allocated area
- Mis-grouped components (wrong boundary)
- Flow direction inconsistent with requested layout (LR vs TB)

### 6.2 Patch format (recommend patch IR, not XML)
Vision QA emits patches like:
- increase spacing in a region
- switch layout direction
- move a node to another group/lane
- simplify an edge route style
- shorten label (keep full label in metadata if needed)

Then regenerate via the same batch tool.

---

## 7) Diagram types to support (enterprise deck coverage)

### 7.1 Start with these “high ROI” types
- **Architecture overview** (C4-ish boxes + boundaries)
- **Data flow / integration flow** (DAG)
- **Sequence** (request/response across actors)
- **Lineage** (sources → transforms → sinks; DAG)
- **Timeline / roadmap** (phases + milestones)

### 7.2 Recommended layout defaults
- Architecture: LR, orthogonal edges, bounded groups
- Flow/Lineage: LR or TB DAG (Sugiyama-style layout)
- Sequence: vertical lifelines + horizontal messages
- Timeline: TB with swimlanes for phases

---

## 8) Implementation anchors (the exact tools to build around)

### 8.1 Headless XML generator
- `yohasacura/drawio-mcp` — programmatic draw.io/diagrams.net XML generation as an MCP server.  [oai_citation:12‡GitHub](https://github.com/yohasacura/drawio-mcp?utm_source=chatgpt.com)

### 8.2 Headless renderer
- `jgraph/draw-image-export2` — server-side rendering with key params:
  - `embedXml` (embed diagram XML in PNG)
  - `base64` (base64 response)
  - `bg` (background color)
  - `format` (png/pdf/svg)
These are documented in its parameter table.  [oai_citation:13‡GitHub](https://github.com/jgraph/draw-image-export2?utm_source=chatgpt.com)

### 8.3 Embedded XML in PNG
- diagrams.net supports embedding XML in PNG metadata; draw.io blog explains the `zTxt` mechanism.  [oai_citation:14‡draw.io](https://www.drawio.com/blog/xml-in-png?utm_source=chatgpt.com)  
- diagrams.net embed/export flows explicitly support `xmlpng` and `xmlsvg`.  [oai_citation:15‡draw.io](https://www.drawio.com/doc/faq/embed-mode?utm_source=chatgpt.com)

### 8.4 Why not official draw.io MCP
- Official `jgraph/drawio-mcp` and `@drawio/mcp` emphasize opening the diagram in the draw.io editor.  [oai_citation:16‡GitHub](https://github.com/jgraph/drawio-mcp?utm_source=chatgpt.com)  
This is contrary to your “seamless headless compilation” requirement.

---

## 9) Codex execution instructions (what to build)

### 9.1 Build an internal “Diagram Compiler Service”
- Input: Diagram IR batch
- Output: PNG + XML batch

**Core functions:**
1) `validate_ir(ir)`
2) `compile_ir_to_drawio_xml(ir)`: calls yohasacura/drawio-mcp internally
3) `render_xml_to_png(xml, opts)`: calls draw-image-export2 internally using `embedXml=1`, `base64=1`
4) `return_artifacts()`

**Non-negotiables:**
- Version-pin all dependencies and container images.
- Deterministic layout rules per diagram type.
- Fail fast with actionable errors when IR is invalid.

### 9.2 Make the LLM do less
- LLM writes IR + constraints.
- Compiler service enforces style profile and layout discipline.
- Vision QA produces structured patches.

This reduces “diagram spaghetti” and keeps outputs stable across runs.

---

## 10) Decision summary (what you should do)

**Use this stack:**
- **yohasacura/drawio-mcp** for programmatic XML generation (headless)  [oai_citation:17‡GitHub](https://github.com/yohasacura/drawio-mcp?utm_source=chatgpt.com)
- **jgraph/draw-image-export2** for XML→PNG rendering with `embedXml`/`base64`  [oai_citation:18‡GitHub](https://github.com/jgraph/draw-image-export2?utm_source=chatgpt.com)
- Store XML + PNG(embedded XML) as artifacts  [oai_citation:19‡draw.io](https://www.drawio.com/blog/xml-in-png?utm_source=chatgpt.com)

**Do NOT rely on official draw.io MCP editor workflow** for production automation.  [oai_citation:20‡GitHub](https://github.com/jgraph/drawio-mcp?utm_source=chatgpt.com)

