"""LLM planner using Gemini with strict DeckIR validation."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Tuple

from pydantic import ValidationError

from ..assets import ensure_asset_catalog, match_asset
from ..models.content import ContentModel
from ..models.deck_ir import AssetRef, DeckIR, DeckSlide
from .base import LLMClient, LLMClientError, LLMUsage


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
    system_prompt = _build_system_prompt(layout_catalog, icons_catalog)
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
    for attempt in range(1, attempts + 1):
        try:
            response = client.generate_json(system_prompt=system_prompt, user_prompt=user_prompt)
            if response.usage is not None:
                usage_records.append(response.usage)
            candidate = response.data
            candidate = _sanitize_candidate(candidate)
            deck = DeckIR.model_validate(candidate)
            project_root = layout_catalog_path.parents[1]
            _normalize_asset_refs(deck, layout_catalog, icons_catalog, project_root)
            _fill_missing_visuals(deck, layout_catalog_path)
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
            if isinstance(slide.get("constraints_override"), list):
                slide["constraints_override"] = None
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


def _build_system_prompt(layout_catalog: Dict[str, Any], icons_catalog: Dict[str, Any]) -> str:
    allowed_layouts = []
    for layout in layout_catalog.get("layouts", []):
        layout_id = layout.get("layout_id")
        if not layout_id:
            continue
        field_keys = []
        for field in layout.get("fields", []):
            field_key = field.get("field_key")
            if field_key:
                field_keys.append(field_key)
        allowed_layouts.append({"layout_id": layout_id, "field_keys": field_keys})

    icon_ids = sorted(list(_allowed_icon_ids(icons_catalog)))
    # Keep prompt bounded.
    icon_ids_preview = icon_ids[:400]

    return (
        "You are a deck planner. Output ONLY valid JSON object for DeckIR.\n"
        "No markdown, no explanations.\n"
        "Use only the allowed layouts/fields and icon IDs.\n"
        "Prefer concise bullets to avoid overflow.\n"
        "Use one slide per section from input; do not invent extra slides.\n"
        "For each slide, choose a layout that matches content density:\n"
        "- few points -> title/statement layouts\n"
        "- list-heavy sections -> one_content/two_content/three_content\n"
        "- process sections -> agenda/timeline-like layouts if available\n"
        "Only emit asset_refs when the chosen layout has an image placeholder field key.\n"
        "For image placeholders, prefer icon asset refs unless there is a clear concrete image cue.\n"
        "If uncertain, choose layout_id 'one_content_light'.\n\n"
        f"Allowed layouts and field keys:\n{json.dumps(allowed_layouts, ensure_ascii=True)}\n\n"
        f"Allowed icon_ids (subset):\n{json.dumps(icon_ids_preview, ensure_ascii=True)}\n"
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
    cues_json = json.dumps(cues_data, sort_keys=True, ensure_ascii=True)

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
        "- If a section contains explicit layout hints, honor them when valid.\n\n"
        f"Required deck_id: {deck_id}\n"
        f"Required run_id: {run_id}\n"
        f"Required template_id: {template_id}\n\n"
        f"ContentModel:\n{content_json}\n\n"
        f"Cues:\n{cues_json}\n"
    )


def _fill_missing_visuals(deck: DeckIR, layout_catalog_path: Path) -> None:
    """Deterministic visual search to fill absent asset refs."""
    with layout_catalog_path.open("r", encoding="utf-8") as handle:
        layout_catalog = json.load(handle)
    layouts = {entry["layout_id"]: entry for entry in layout_catalog.get("layouts", [])}
    assets_dir = layout_catalog_path.parents[1]
    asset_catalog = ensure_asset_catalog(assets_dir)
    assets = asset_catalog.get("assets", [])

    for slide in deck.slides:
        layout = layouts.get(slide.layout_id, {})
        field_keys = [f.get("field_key") for f in layout.get("fields", []) if f.get("field_key")]
        image_fields = sorted([key for key in field_keys if key.startswith("ph_image")])
        if not image_fields:
            slide.asset_refs = []
            continue
        if slide.asset_refs:
            continue

        search_text = _slide_search_text(slide)
        icon_match = match_asset(search_text, assets, allowed_types=("icon",), min_score=1)
        if icon_match:
            slide.asset_refs = [
                AssetRef(
                    asset_type="icon",
                    asset_id=str(icon_match["asset_id"]),
                    target_field_key=image_fields[0],
                )
            ]
            continue

        image_match = match_asset(search_text, assets, allowed_types=("image",), min_score=1)
        if image_match:
            slide.asset_refs = [
                AssetRef(
                    asset_type="image",
                    asset_id=str(image_match["asset_id"]),
                    target_field_key=image_fields[0],
                )
            ]


def _slide_search_text(slide: DeckSlide) -> str:
    parts: List[str] = [slide.slide_id, slide.layout_id]
    for value in slide.fields.values():
        if isinstance(value, list):
            parts.extend([str(item) for item in value])
        else:
            parts.append(str(value))
    return " | ".join(part for part in parts if part)
