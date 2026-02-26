"""Generate pipeline helpers for combined markdown input."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .assets import (
    ensure_asset_catalog,
    load_branded_images_catalog,
    load_visual_vocabulary,
    match_asset,
    resolve_branded_image,
    resolve_visual_concepts_for_text,
)
from .models.content import ContentModel, ContentSection
from .models.deck_ir import AssetRef, DeckIR, DeckSlide, FieldValue

RENDERABLE_IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp")


class CombinedInputError(ValueError):
    """Raised when combined markdown input is invalid."""


def split_combined_markdown(markdown_text: str) -> Tuple[str, Dict[str, Any]]:
    """Split a combined markdown input into content markdown and cues JSON.

    Expected format:
      ## Content
      ...markdown...

      ## Visualization Cues
      ```json
      {"cues": [...]}
      ```
    """
    content_lines: List[str] = []
    cues_lines: List[str] = []
    current: str | None = None

    for line in markdown_text.splitlines():
        section_kind = _detect_section_heading(line)
        if section_kind is not None:
            current = section_kind
            continue

        if current == "content":
            content_lines.append(line)
        elif current == "cues":
            cues_lines.append(line)

    # Support plain content.md input by treating the entire file as content
    # when explicit combined sections are absent.
    raw_content = "\n".join(content_lines) if (content_lines or cues_lines) else markdown_text
    content_md = _normalize_content_markdown(raw_content).strip()
    if not content_md:
        raise CombinedInputError(
            "Missing or empty content section in combined markdown input."
        )

    cues_raw = "\n".join(cues_lines).strip()
    if not cues_raw:
        cues_data: Dict[str, Any] = {"cues": []}
        return content_md, cues_data

    cues_json_text = _extract_json_payload(cues_raw)
    try:
        parsed = json.loads(cues_json_text)
    except json.JSONDecodeError as exc:
        raise CombinedInputError(
            "Visualization cues section must contain valid JSON."
        ) from exc

    if isinstance(parsed, list):
        cues_data = {"cues": parsed}
    elif isinstance(parsed, dict):
        cues_data = parsed
    else:
        raise CombinedInputError(
            "Visualization cues JSON must be an object or a list."
        )

    if "cues" not in cues_data:
        cues_data = {"cues": []}

    if not isinstance(cues_data["cues"], list):
        raise CombinedInputError("'cues' must be a JSON array.")

    return content_md, cues_data


def _extract_json_payload(text: str) -> str:
    fence_match = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    if fence_match:
        return fence_match.group(1).strip()
    return text.strip()


def _detect_section_heading(line: str) -> str | None:
    stripped = line.strip()
    if not stripped:
        return None

    markdown_match = re.match(r"^\s{0,3}#{1,6}\s+(.+?)\s*$", line)
    heading = markdown_match.group(1).strip() if markdown_match else stripped
    heading = heading.lower().strip(":")

    if heading == "content":
        return "content"
    if heading in {"visualization cues", "cues", "visual cues"}:
        return "cues"
    return None


def _normalize_content_markdown(raw_content: str) -> str:
    lines = raw_content.splitlines()
    out: List[str] = []
    pending_section_title = False

    for line in lines:
        normalized = line.rstrip()
        stripped = normalized.strip()

        if not stripped:
            out.append("")
            continue

        if stripped in {"⸻", "—", "–––"}:
            out.append("---")
            pending_section_title = False
            continue
        if stripped == "---":
            out.append("---")
            pending_section_title = False
            continue

        if _extract_section_id(stripped):
            out.append(stripped)
            pending_section_title = True
            continue

        bullet_match = re.match(r"^\s*[•●▪◦]\s*(.+)$", normalized)
        if bullet_match:
            out.append(f"- {bullet_match.group(1).strip()}")
            continue

        if pending_section_title and not re.match(r"^\s*#{1,6}\s+", normalized):
            out.append(f"## {stripped}")
            pending_section_title = False
            continue

        out.append(normalized)

    return "\n".join(out)


def _extract_section_id(line: str) -> str | None:
    match = re.match(r"<!--\s*section_id\s*:\s*([a-zA-Z0-9_\-]+)\s*-->", line)
    return match.group(1) if match else None


def build_deckir_from_content(
    content_model: ContentModel,
    cues_data: Dict[str, Any],
    layout_catalog_path: Path,
    run_id: str,
    deck_id: str,
    template_id: str = "corp_deck_2025",
) -> DeckIR:
    """Build a deterministic DeckIR from ContentModel + cues."""
    with layout_catalog_path.open("r", encoding="utf-8") as handle:
        catalog = json.load(handle)
    layouts = {entry["layout_id"]: entry for entry in catalog.get("layouts", [])}
    asset_catalog = _load_or_build_asset_catalog(layout_catalog_path)
    assets = asset_catalog.get("assets", [])
    assets_dir = layout_catalog_path.parents[1]
    vocabulary = load_visual_vocabulary(assets_dir)
    branded_catalog = load_branded_images_catalog(assets_dir)

    cues_by_section = {
        cue.get("section_id"): cue
        for cue in cues_data.get("cues", [])
        if isinstance(cue, dict) and cue.get("section_id")
    }

    slides: List[DeckSlide] = []
    used_slide_ids: set[str] = set()

    for idx, section in enumerate(content_model.sections):
        cue = cues_by_section.get(section.section_id, {})
        layout_hint = cue.get("layout_hint")
        layout_id = layout_hint if layout_hint in layouts else "one_content_light"
        layout_entry = layouts.get(layout_id, layouts["one_content_light"])

        slide_id = _make_slide_id(section.section_id, idx + 1, used_slide_ids)
        fields = _section_to_fields(section, layout_entry)
        speaker_notes = str(cue.get("notes", "")).strip()
        asset_refs = _build_asset_refs(
            section=section,
            cue=cue,
            layout_entry=layout_entry,
            assets=assets,
            vocabulary=vocabulary,
            branded_catalog=branded_catalog,
        )

        slides.append(
            DeckSlide(
                slide_id=slide_id,
                layout_id=layout_id,
                fields=fields,
                speaker_notes=speaker_notes,
                asset_refs=asset_refs,
            )
        )

    deck_title = content_model.sections[0].title if content_model.sections else deck_id
    return DeckIR(
        deck_id=deck_id,
        run_id=run_id,
        template_id=template_id,
        title=deck_title,
        slides=slides,
    )


def _make_slide_id(section_id: str, fallback_num: int, used_ids: set[str]) -> str:
    base = re.sub(r"[^a-zA-Z0-9_]+", "_", section_id).strip("_") or f"slide_{fallback_num:03d}"
    candidate = base
    suffix = 2
    while candidate in used_ids:
        candidate = f"{base}_{suffix}"
        suffix += 1
    used_ids.add(candidate)
    return candidate


def _section_to_fields(section: ContentSection, layout_entry: Dict[str, Any]) -> Dict[str, FieldValue]:
    fields_spec = layout_entry.get("fields", [])
    field_keys = [field.get("field_key", "") for field in fields_spec if field.get("field_key")]
    text_items = _section_text_items(section)
    fields: Dict[str, FieldValue] = {}

    if "ph_title" in field_keys:
        fields["ph_title"] = section.title

    column_keys = [key for key in field_keys if key.startswith("ph_col")]
    if column_keys:
        chunks = _split_evenly(text_items, len(column_keys))
        for key, chunk in zip(column_keys, chunks):
            fields[key] = chunk if chunk else ""
        return fields

    side_keys = [key for key in ("ph_body_left", "ph_body_right") if key in field_keys]
    if side_keys:
        chunks = _split_evenly(text_items, len(side_keys))
        for key, chunk in zip(side_keys, chunks):
            fields[key] = chunk if chunk else ""
        return fields

    if "ph_body" in field_keys:
        if len(text_items) == 1:
            fields["ph_body"] = text_items[0]
        elif text_items:
            fields["ph_body"] = text_items
        else:
            fields["ph_body"] = ""

    return fields


def _section_text_items(section: ContentSection) -> List[str]:
    if section.bullets:
        return [str(item) for item in section.bullets]
    if section.paragraphs:
        return [str(item) for item in section.paragraphs]
    return [section.title]


def _split_evenly(items: List[str], buckets: int) -> List[List[str]]:
    if buckets <= 0:
        return []
    out: List[List[str]] = [[] for _ in range(buckets)]
    for idx, item in enumerate(items):
        out[idx % buckets].append(item)
    return out


def _load_or_build_asset_catalog(layout_catalog_path: Path) -> Dict[str, Any]:
    assets_dir = layout_catalog_path.parents[1]
    return ensure_asset_catalog(assets_dir)


def _build_asset_refs(
    section: ContentSection,
    cue: Dict[str, Any],
    layout_entry: Dict[str, Any],
    assets: List[Dict[str, Any]],
    vocabulary: Dict[str, Any] | None = None,
    branded_catalog: Dict[str, Any] | None = None,
) -> List[AssetRef]:
    field_keys = {field.get("field_key") for field in layout_entry.get("fields", [])}
    if "ph_image" not in field_keys:
        return []

    refs: List[AssetRef] = []
    layout_id = layout_entry.get("layout_id", "")

    # 1. Try icon_hints via visual vocabulary
    icon_hints = cue.get("icon_hints", [])
    if vocabulary and icon_hints:
        for hint in icon_hints:
            icon_id = resolve_visual_concepts_for_text(str(hint), vocabulary)
            if icon_id:
                refs.append(AssetRef(asset_type="icon", asset_id=icon_id, target_field_key="ph_image"))
                return refs

    # 2. Try image_hint via branded catalog
    image_hint = str(cue.get("image_hint") or "").strip()
    if branded_catalog and image_hint:
        path = resolve_branded_image(image_hint, branded_catalog)
        if path:
            refs.append(AssetRef(asset_type="image", asset_id=path, target_field_key="ph_image"))
            return refs

    # 3. Try content keywords via vocabulary
    if vocabulary:
        search_text = f"{section.title} {' '.join(str(b) for b in section.bullets)}"
        icon_id = resolve_visual_concepts_for_text(search_text, vocabulary)
        if icon_id:
            refs.append(AssetRef(asset_type="icon", asset_id=icon_id, target_field_key="ph_image"))
            return refs

    # 4. For section/title layouts, try branded image by theme
    if branded_catalog and layout_id in ("section_break_light", "title_image_light"):
        path = resolve_branded_image(section.title, branded_catalog)
        if path:
            refs.append(AssetRef(asset_type="image", asset_id=path, target_field_key="ph_image"))
            return refs

    # 5. Fallback: token-overlap match
    semantic_context = " | ".join(
        part for part in (image_hint, str(cue.get("notes", "")), section.title) if part
    )
    if semantic_context:
        matched_image = match_asset(semantic_context, assets, allowed_types=("image",), min_score=1)
        if matched_image:
            refs.append(AssetRef(asset_type="image", asset_id=str(matched_image["asset_id"]), target_field_key="ph_image"))
            return refs

    renderable_icons = [
        asset for asset in assets
        if asset.get("asset_type") == "icon"
        and _is_renderable_source_path(str(asset.get("source_path", "")))
    ]
    for hint in icon_hints:
        matched_icon = match_asset(str(hint), renderable_icons, allowed_types=("icon",), min_score=1)
        if matched_icon:
            refs.append(AssetRef(asset_type="icon", asset_id=str(matched_icon["asset_id"]), target_field_key="ph_image"))
            return refs

    return refs


def _is_renderable_source_path(source_path: str) -> bool:
    return source_path.lower().endswith(RENDERABLE_IMAGE_SUFFIXES)
