"""Template drift detection."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from pptx import Presentation
from pptx.oxml.ns import qn


def _read_alt_text(shape) -> Optional[str]:
    elem = shape.element
    nvSpPr = elem.find(qn("p:nvSpPr"))
    if nvSpPr is not None:
        cNvPr = nvSpPr.find(qn("p:cNvPr"))
        if cNvPr is not None:
            descr = cNvPr.get("descr", "")
            if descr:
                return descr
    nvPicPr = elem.find(qn("p:nvPicPr"))
    if nvPicPr is not None:
        cNvPr = nvPicPr.find(qn("p:cNvPr"))
        if cNvPr is not None:
            descr = cNvPr.get("descr", "")
            if descr:
                return descr
    return None


def _layout_field_keys(layout) -> Set[str]:
    keys: Set[str] = set()
    for shape in layout.shapes:
        alt_text = _read_alt_text(shape)
        if alt_text:
            keys.add(alt_text)
    return keys


def _load_catalog(catalog_path: Path) -> Dict[str, Any]:
    with open(catalog_path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_template_catalog(template_path: Path, catalog_path: Path) -> List[str]:
    """Return a list of validation errors; empty list means pass."""
    errors: List[str] = []
    catalog = _load_catalog(catalog_path)
    layouts = catalog.get("layouts", [])

    prs = Presentation(str(template_path))
    masters = prs.slide_masters

    seen_layout_ids: Set[str] = set()

    for layout_entry in layouts:
        layout_id = layout_entry.get("layout_id")
        if not layout_id:
            errors.append("Catalog entry missing layout_id")
            continue

        if layout_id in seen_layout_ids:
            errors.append(f"Duplicate layout_id in catalog: {layout_id}")
            continue
        seen_layout_ids.add(layout_id)

        master_index = layout_entry.get("master_index")
        layout_index = layout_entry.get("layout_index")
        template_layout_name = layout_entry.get("template_layout_name")

        if not isinstance(master_index, int) or master_index < 0 or master_index >= len(masters):
            errors.append(
                f"Layout {layout_id} missing in template: master_index={master_index}"
            )
            continue

        master = masters[master_index]
        if not isinstance(layout_index, int) or layout_index < 0 or layout_index >= len(master.slide_layouts):
            errors.append(
                f"Layout {layout_id} missing in template: master_index={master_index}, layout_index={layout_index}"
            )
            continue

        layout = master.slide_layouts[layout_index]
        if template_layout_name and layout.name != template_layout_name:
            errors.append(
                f"Layout {layout_id} name mismatch: catalog='{template_layout_name}' template='{layout.name}'"
            )

        field_keys = _layout_field_keys(layout)
        for field in layout_entry.get("fields", []):
            if not field.get("required", False):
                continue
            field_key = field.get("field_key")
            if field_key and field_key not in field_keys:
                errors.append(
                    f"Layout {layout_id} missing required field_key: {field_key}"
                )

    return errors
