"""LLM planner with visual vocabulary and branded image resolution."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Tuple

from pydantic import ValidationError

from ..assets import (
    ensure_asset_catalog,
    load_branded_images_catalog,
    load_visual_vocabulary,
    match_asset,
    resolve_branded_image,
    resolve_visual_concept,
    resolve_visual_concepts_for_text,
)
from ..models.content import ContentModel
from ..models.deck_ir import AssetRef, DeckIR, DeckSlide
from .base import LLMClient, LLMClientError, LLMUsage

logger = logging.getLogger(__name__)


class PlannerError(RuntimeError):
    """Raised when planning fails across all retries."""


@dataclass
class PlanningStats:
    provider: str
    model: str
    attempts: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float | None
    usage_by_attempt: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "attempts": self.attempts,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": self.estimated_cost_usd,
            "usage_by_attempt": self.usage_by_attempt,
        }


def plan_deck_with_llm(
    *,
    client: LLMClient,
    content_model: ContentModel,
    cues_data: Dict[str, Any],
    layout_catalog_path: Path,
    icons_json_path: Path,
    run_id: str,
    deck_id: str,
    template_id: str = "corp_deck_2025",
    max_retries: int = 2,
) -> Tuple[DeckIR, PlanningStats]:
    """Return schema-valid DeckIR and number of attempts used."""
    layout_catalog = _load_json(layout_catalog_path)
    icons_catalog = _load_json(icons_json_path)
    assets_dir = layout_catalog_path.parents[1]
    vocabulary = load_visual_vocabulary(assets_dir)
    branded_catalog = load_branded_images_catalog(assets_dir)

    system_prompt = _build_system_prompt(layout_catalog, vocabulary, branded_catalog)
    user_prompt = _build_user_prompt(
        content_model=content_model,
        cues_data=cues_data,
        run_id=run_id,
        deck_id=deck_id,
        template_id=template_id,
    )

    attempts = max_retries + 1
    errors: List[str] = []
    usage_records: List[LLMUsage] = []
    project_root = layout_catalog_path.parents[1]
    for attempt in range(1, attempts + 1):
        try:
            response = client.generate_json(system_prompt=system_prompt, user_prompt=user_prompt)
            if response.usage is not None:
                usage_records.append(response.usage)
            candidate = response.data
            candidate = _sanitize_candidate(candidate)
            deck = DeckIR.model_validate(candidate)
            # Resolve concept-level asset refs to actual icon/image IDs
            _resolve_concept_refs(deck, vocabulary, branded_catalog, project_root)
            _normalize_asset_refs(deck, layout_catalog, icons_catalog, project_root)
            _fill_missing_visuals(deck, layout_catalog_path, cues_data, vocabulary, branded_catalog)
            _enforce_catalog_constraints(deck, layout_catalog, icons_catalog, project_root)
            return deck, _aggregate_planning_stats(client, attempt, usage_records)
        except (LLMClientError, ValidationError, ValueError) as exc:
            errors.append(f"attempt {attempt}: {exc}")

    raise PlannerError("LLM planner failed after retries: " + " | ".join(errors))


def plan_deck_with_gemini(
    *,
    client: LLMClient,
    content_model: ContentModel,
    cues_data: Dict[str, Any],
    layout_catalog_path: Path,
    icons_json_path: Path,
    run_id: str,
    deck_id: str,
    template_id: str = "corp_deck_2025",
    max_retries: int = 2,
) -> Tuple[DeckIR, PlanningStats]:
    """Backward-compatible alias; planner is now provider-agnostic."""
    return plan_deck_with_llm(
        client=client,
        content_model=content_model,
        cues_data=cues_data,
        layout_catalog_path=layout_catalog_path,
        icons_json_path=icons_json_path,
        run_id=run_id,
        deck_id=deck_id,
        template_id=template_id,
        max_retries=max_retries,
    )


def _aggregate_planning_stats(
    client: LLMClient, attempts_used: int, usage_records: List[LLMUsage]
) -> PlanningStats:
    prompt_tokens = sum(u.prompt_tokens for u in usage_records)
    completion_tokens = sum(u.completion_tokens for u in usage_records)
    total_tokens = sum(u.total_tokens for u in usage_records)
    known_costs = [u.estimated_cost_usd for u in usage_records if u.estimated_cost_usd is not None]
    estimated_cost_usd = round(sum(known_costs), 8) if known_costs else None
    return PlanningStats(
        provider=getattr(client, "provider", "unknown"),
        model=getattr(client, "model", "unknown"),
        attempts=attempts_used,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        estimated_cost_usd=estimated_cost_usd,
        usage_by_attempt=[u.to_dict() for u in usage_records],
    )


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected object JSON at {path}")
    return data


def _sanitize_candidate(candidate: Dict[str, Any]) -> Dict[str, Any]:
    """Repair common LLM JSON type drift before strict validation."""
    if not isinstance(candidate.get("global_constraints"), dict):
        candidate["global_constraints"] = {}

    slides = candidate.get("slides")
    if isinstance(slides, list):
        for slide in slides:
            if not isinstance(slide, dict):
                continue
            constraints_override = slide.get("constraints_override")
            if not isinstance(constraints_override, dict):
                slide["constraints_override"] = None
            speaker_notes = slide.get("speaker_notes")
            if isinstance(speaker_notes, list):
                slide["speaker_notes"] = "\n".join(str(item) for item in speaker_notes if item is not None)
            elif speaker_notes is None:
                slide["speaker_notes"] = ""
            fields = slide.get("fields")
            if isinstance(fields, dict):
                normalized_fields: Dict[str, Any] = {}
                for key, value in fields.items():
                    if isinstance(value, list):
                        normalized_fields[key] = [str(item) for item in value]
                    elif value is None:
                        normalized_fields[key] = ""
                    else:
                        normalized_fields[key] = str(value)
                slide["fields"] = normalized_fields
    return candidate


def _allowed_layouts(layout_catalog: Dict[str, Any]) -> Dict[str, set[str]]:
    layouts = {}
    for layout in layout_catalog.get("layouts", []):
        layout_id = layout.get("layout_id")
        if not layout_id:
            continue
        fields = set()
        for field in layout.get("fields", []):
            field_key = field.get("field_key")
            if field_key:
                fields.add(field_key)
        layouts[layout_id] = fields
    return layouts


def _allowed_icon_ids(icons_catalog: Dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for icon in icons_catalog.get("icons", []):
        icon_id = icon.get("icon_id")
        if icon_id:
            out.add(str(icon_id))
    return out


def _resolve_concept_refs(
    deck: DeckIR,
    vocabulary: Dict[str, Any],
    branded_catalog: Dict[str, Any],
    project_root: Path,
) -> None:
    """Resolve concept-level asset_refs from the LLM to actual icon/image IDs."""
    branded_images = branded_catalog.get("images", {})

    for slide in deck.slides:
        resolved_refs: List[AssetRef] = []
        for asset in slide.asset_refs:
            if asset.asset_type == "icon":
                # Try resolving as a concept name first
                icon_id = resolve_visual_concept(asset.asset_id, vocabulary)
                if icon_id:
                    asset.asset_id = icon_id
                    resolved_refs.append(asset)
                else:
                    # Keep as-is (might be a direct icon_id from the catalog)
                    resolved_refs.append(asset)
            elif asset.asset_type == "image":
                # Try resolving as a branded image ID
                if asset.asset_id in branded_images:
                    entry = branded_images[asset.asset_id]
                    color_pref = entry.get("color_preference", {})
                    color = color_pref.get("light_theme", "Teal")
                    paths = entry.get("paths", {})
                    resolved_path = paths.get(color) or next(iter(paths.values()), None)
                    if resolved_path:
                        asset.asset_id = resolved_path
                        resolved_refs.append(asset)
                    else:
                        logger.warning("Branded image %s has no paths", asset.asset_id)
                elif _image_asset_exists(asset.asset_id, project_root):
                    resolved_refs.append(asset)
                else:
                    # Try resolving the asset_id as a theme query
                    path = resolve_branded_image(asset.asset_id, branded_catalog)
                    if path:
                        asset.asset_id = path
                        resolved_refs.append(asset)
                    else:
                        logger.warning("Could not resolve image asset: %s", asset.asset_id)
            else:
                resolved_refs.append(asset)
        slide.asset_refs = resolved_refs


def _enforce_catalog_constraints(
    deck: DeckIR,
    layout_catalog: Dict[str, Any],
    icons_catalog: Dict[str, Any],
    project_root: Path,
) -> None:
    allowed_layouts = _allowed_layouts(layout_catalog)
    allowed_icons = _allowed_icon_ids(icons_catalog)

    for slide in deck.slides:
        if slide.layout_id not in allowed_layouts:
            raise ValueError(f"layout_id not allowed: {slide.layout_id}")
        allowed_fields = allowed_layouts[slide.layout_id]
        for field_key in slide.fields.keys():
            if field_key not in allowed_fields:
                raise ValueError(
                    f"field_key '{field_key}' not allowed for layout '{slide.layout_id}'"
                )
        for asset in slide.asset_refs:
            if asset.target_field_key and asset.target_field_key not in allowed_fields:
                raise ValueError(
                    f"asset target_field_key '{asset.target_field_key}' not allowed "
                    f"for layout '{slide.layout_id}'"
                )
            if asset.asset_type == "icon" and asset.asset_id not in allowed_icons:
                raise ValueError(f"icon_id not allowed: {asset.asset_id}")
            if asset.asset_type == "image" and not _image_asset_exists(asset.asset_id, project_root):
                raise ValueError(f"image asset not found: {asset.asset_id}")


def _normalize_asset_refs(
    deck: DeckIR,
    layout_catalog: Dict[str, Any],
    icons_catalog: Dict[str, Any],
    project_root: Path,
) -> None:
    """Normalize/downgrade asset refs so invalid hints do not crash render."""
    allowed_layouts = _allowed_layouts(layout_catalog)
    allowed_icons = _allowed_icon_ids(icons_catalog)
    for slide in deck.slides:
        allowed_fields = allowed_layouts.get(slide.layout_id, set())
        image_fields = sorted([field for field in allowed_fields if field.startswith("ph_image")])
        normalized_refs = []
        default_target = image_fields[0] if image_fields else None
        for asset in slide.asset_refs:
            if asset.asset_type == "icon" and asset.asset_id not in allowed_icons:
                continue
            if asset.asset_type == "image" and not _image_asset_exists(asset.asset_id, project_root):
                continue
            if default_target is None:
                continue
            if not asset.target_field_key or asset.target_field_key not in allowed_fields:
                asset.target_field_key = default_target
            normalized_refs.append(asset)
        slide.asset_refs = normalized_refs


def _image_asset_exists(asset_id: str, project_root: Path) -> bool:
    path = Path(asset_id)
    if path.is_absolute():
        return path.exists()
    direct = project_root / asset_id
    if direct.exists():
        return True
    under_assets = project_root / "assets" / asset_id
    return under_assets.exists()


# ── Prompt builders ──────────────────────────────────────────────────────

def _build_system_prompt(
    layout_catalog: Dict[str, Any],
    vocabulary: Dict[str, Any],
    branded_catalog: Dict[str, Any],
) -> str:
    # Build layout info with image-capability flag
    layout_info = []
    for layout in layout_catalog.get("layouts", []):
        layout_id = layout.get("layout_id")
        if not layout_id:
            continue
        field_keys = []
        has_image = False
        for f in layout.get("fields", []):
            fk = f.get("field_key")
            if fk:
                field_keys.append(fk)
                if fk.startswith("ph_image"):
                    has_image = True
        constraints = layout.get("constraints", {})
        layout_info.append({
            "layout_id": layout_id,
            "field_keys": field_keys,
            "has_ph_image": has_image,
            "max_bullets": constraints.get("max_bullets", 7),
            "max_total_body_chars": constraints.get("max_total_body_chars", 500),
        })

    # Build compact vocabulary summary (concept: domains)
    vocab_summary = {}
    for concept, entry in vocabulary.get("concepts", {}).items():
        vocab_summary[concept] = entry.get("domains", [])

    # Build branded image summary (id: theme)
    branded_summary = {}
    for img_id, entry in branded_catalog.get("images", {}).items():
        branded_summary[img_id] = entry.get("theme", "")

    return (
        "You are a deck planner. Output ONLY a valid JSON object for DeckIR.\n"
        "No markdown fences, no explanations, no comments — pure JSON only.\n\n"
        "=== LAYOUTS ===\n"
        f"{json.dumps(layout_info, ensure_ascii=True)}\n\n"
        "=== VISUAL VOCABULARY (icon concepts) ===\n"
        "For asset_refs with icons, set asset_type='icon' and asset_id to a CONCEPT NAME from this list.\n"
        "The pipeline resolves concepts to actual icons. Do NOT use raw icon_ids.\n"
        f"{json.dumps(vocab_summary, ensure_ascii=True)}\n\n"
        "=== BRANDED IMAGES (for title/section slides) ===\n"
        "For branded hero images, set asset_type='image' and asset_id to a BRANDED IMAGE ID from this list.\n"
        "Use these on title_image_light and section_break_light layouts.\n"
        f"{json.dumps(branded_summary, ensure_ascii=True)}\n\n"
        "=== RULES ===\n"
        "1. One slide per content section. Do not invent extra slides.\n"
        "2. Choose layout based on content density:\n"
        "   - Title/opening -> title_image_light or section_break_light (with branded image)\n"
        "   - Few bullets -> content_image_light (with icon concept)\n"
        "   - Dense content -> one_content_light, two_content_light\n"
        "   - Process/agenda -> agenda_light or three_content_light\n"
        "   - Statement -> statement_light\n"
        "3. HARD RULE: Every slide whose layout has_ph_image=true MUST have at least one asset_ref\n"
        "   targeting ph_image. Do NOT leave image placeholders empty.\n"
        "4. For icon concepts, pick the concept that best matches the slide's topic.\n"
        "5. For section breaks and title slides, prefer a branded image over an icon.\n"
        "6. Keep bullets concise. Respect max_bullets and max_total_body_chars limits.\n"
        "7. Move overflow detail to speaker_notes.\n"
        "8. Honor layout_hint from cues when the hint is a valid layout_id.\n"
        "9. Honor icon_hints from cues by selecting the matching concept.\n\n"
        "=== WORKED EXAMPLES ===\n"
        '{\n'
        '  "slide_id": "opening",\n'
        '  "layout_id": "title_image_light",\n'
        '  "fields": {"ph_title": "Legacy System Navigator", "ph_body": "Modernization roadmap for enterprise systems"},\n'
        '  "speaker_notes": "",\n'
        '  "asset_refs": [{"asset_type": "image", "asset_id": "transform_reality", "target_field_key": "ph_image"}],\n'
        '  "constraints_override": null\n'
        '}\n\n'
        '{\n'
        '  "slide_id": "data_integration",\n'
        '  "layout_id": "content_image_light",\n'
        '  "fields": {"ph_title": "Data Integration Strategy", "ph_body": ["Unified data layer", "Real-time sync", "API-first approach"]},\n'
        '  "speaker_notes": "Additional technical details...",\n'
        '  "asset_refs": [{"asset_type": "icon", "asset_id": "integration", "target_field_key": "ph_image"}],\n'
        '  "constraints_override": null\n'
        '}\n\n'
        '{\n'
        '  "slide_id": "risk_governance",\n'
        '  "layout_id": "content_image_light",\n'
        '  "fields": {"ph_title": "Risk & Governance", "ph_body": ["Compliance framework", "Audit trail", "Access controls"]},\n'
        '  "speaker_notes": "",\n'
        '  "asset_refs": [{"asset_type": "icon", "asset_id": "governance", "target_field_key": "ph_image"}],\n'
        '  "constraints_override": null\n'
        '}\n'
    )


def _build_user_prompt(
    *,
    content_model: ContentModel,
    cues_data: Dict[str, Any],
    run_id: str,
    deck_id: str,
    template_id: str,
) -> str:
    content_json = content_model.to_json()

    # Format cues prominently so the LLM can use them for visual decisions
    cues_block = _format_cues_for_prompt(cues_data)

    return (
        "Build DeckIR JSON with this exact top-level schema:\n"
        "{deck_id, run_id, template_id, title, subtitle, global_constraints, slides}\n"
        "Each slide must include: slide_id, layout_id, fields, speaker_notes, asset_refs, constraints_override.\n"
        "field values must be string or array of strings.\n"
        "asset_refs items must include asset_type(icon|image), asset_id, target_field_key.\n"
        "Set deck_id/run_id/template_id exactly as provided.\n\n"
        "Rules:\n"
        "- Keep slide_id stable and slug-like, ideally derived from section_id.\n"
        "- Keep key business points on slide and move overflow detail into speaker_notes.\n"
        "- If a section contains explicit layout hints, honor them when valid.\n"
        "- Use the visualization cues below to drive layout and visual choices for each section.\n"
        "- For layouts with ph_image, you MUST include an asset_ref. Use icon concepts or branded image IDs.\n\n"
        f"Required deck_id: {deck_id}\n"
        f"Required run_id: {run_id}\n"
        f"Required template_id: {template_id}\n\n"
        f"ContentModel:\n{content_json}\n\n"
        "=== VISUALIZATION CUES (use these to drive layout and visual choices) ===\n"
        f"{cues_block}\n"
    )


def _format_cues_for_prompt(cues_data: Dict[str, Any]) -> str:
    """Format cues into a clear, readable block for the LLM."""
    cues_list = cues_data.get("cues", [])
    if not cues_list:
        return "No visualization cues provided."

    lines: List[str] = []
    for cue in cues_list:
        if not isinstance(cue, dict):
            continue
        section_id = cue.get("section_id", "unknown")
        layout_hint = cue.get("layout_hint", "")
        icon_hints = cue.get("icon_hints", [])
        image_hint = cue.get("image_hint", "")
        notes = cue.get("notes", "")

        lines.append(f"Section: {section_id}")
        if layout_hint:
            lines.append(f"  layout_hint: {layout_hint}")
        if icon_hints:
            lines.append(f"  icon_hints: {', '.join(str(h) for h in icon_hints)}")
        if image_hint:
            lines.append(f"  image_hint: {image_hint}")
        if notes:
            lines.append(f"  notes: {notes}")
        lines.append("")

    return "\n".join(lines)


# ── Visual fill (safety net) ────────────────────────────────────────────

def _fill_missing_visuals(
    deck: DeckIR,
    layout_catalog_path: Path,
    cues_data: Dict[str, Any] | None = None,
    vocabulary: Dict[str, Any] | None = None,
    branded_catalog: Dict[str, Any] | None = None,
) -> None:
    """Deterministic visual fill for slides missing asset_refs on ph_image."""
    with layout_catalog_path.open("r", encoding="utf-8") as handle:
        layout_catalog = json.load(handle)
    layouts = {entry["layout_id"]: entry for entry in layout_catalog.get("layouts", [])}
    assets_dir = layout_catalog_path.parents[1]

    if vocabulary is None:
        vocabulary = load_visual_vocabulary(assets_dir)
    if branded_catalog is None:
        branded_catalog = load_branded_images_catalog(assets_dir)

    # Build cues lookup
    cues_by_section: Dict[str, Dict[str, Any]] = {}
    if cues_data:
        for cue in cues_data.get("cues", []):
            if isinstance(cue, dict) and cue.get("section_id"):
                cues_by_section[cue["section_id"]] = cue

    for slide in deck.slides:
        layout = layouts.get(slide.layout_id, {})
        field_keys = [f.get("field_key") for f in layout.get("fields", []) if f.get("field_key")]
        image_fields = sorted([key for key in field_keys if key.startswith("ph_image")])
        if not image_fields:
            # Strip any asset_refs for layouts without image placeholders
            slide.asset_refs = []
            continue
        if slide.asset_refs:
            continue

        target_field = image_fields[0]

        # 1. Try cue icon_hints via vocabulary
        cue = cues_by_section.get(slide.slide_id, {})
        icon_hints = cue.get("icon_hints", [])
        for hint in icon_hints:
            icon_id = resolve_visual_concepts_for_text(str(hint), vocabulary)
            if icon_id:
                slide.asset_refs = [AssetRef(asset_type="icon", asset_id=icon_id, target_field_key=target_field)]
                break
        if slide.asset_refs:
            continue

        # 2. Try cue image_hint via branded catalog
        image_hint = cue.get("image_hint", "")
        if image_hint:
            path = resolve_branded_image(str(image_hint), branded_catalog)
            if path:
                slide.asset_refs = [AssetRef(asset_type="image", asset_id=path, target_field_key=target_field)]
                continue

        # 3. Fall back: extract keywords from slide content -> vocabulary
        search_text = _slide_search_text(slide)
        icon_id = resolve_visual_concepts_for_text(search_text, vocabulary)
        if icon_id:
            slide.asset_refs = [AssetRef(asset_type="icon", asset_id=icon_id, target_field_key=target_field)]
            continue

        # 4. For section_break / title_image layouts, try branded image by content theme
        if slide.layout_id in ("section_break_light", "title_image_light"):
            path = resolve_branded_image(search_text, branded_catalog)
            if path:
                slide.asset_refs = [AssetRef(asset_type="image", asset_id=path, target_field_key=target_field)]
                continue

        # 5. Last resort: token-overlap match against full asset catalog
        asset_catalog = ensure_asset_catalog(assets_dir)
        assets = asset_catalog.get("assets", [])
        icon_match = match_asset(search_text, assets, allowed_types=("icon",), min_score=1)
        if icon_match:
            slide.asset_refs = [AssetRef(asset_type="icon", asset_id=str(icon_match["asset_id"]), target_field_key=target_field)]
            continue

        image_match = match_asset(search_text, assets, allowed_types=("image",), min_score=1)
        if image_match:
            slide.asset_refs = [AssetRef(asset_type="image", asset_id=str(image_match["asset_id"]), target_field_key=target_field)]
            continue

        logger.warning("VISUAL_CUE_UNRESOLVED slide=%s search=%s", slide.slide_id, search_text[:100])


def _slide_search_text(slide: DeckSlide) -> str:
    parts: List[str] = [slide.slide_id, slide.layout_id]
    for value in slide.fields.values():
        if isinstance(value, list):
            parts.extend([str(item) for item in value])
        else:
            parts.append(str(value))
    return " | ".join(part for part in parts if part)
