"""Config model."""

from __future__ import annotations

from pydantic import Field, constr

from .base import PptxBaseModel

NonEmptyStr = constr(min_length=1)


class Config(PptxBaseModel):
    project_root: NonEmptyStr = Field(..., description="Project root directory")
    assets_dir: NonEmptyStr = Field(..., description="Canonical assets directory")
    template_path: NonEmptyStr = Field(..., description="Template PPTX path")
    layout_catalog_path: NonEmptyStr = Field(..., description="Layout catalog JSON path")
    icons_json_path: NonEmptyStr = Field(..., description="Icons metadata JSON path")
    inputs_dir: NonEmptyStr = Field(..., description="Inputs directory")
    runs_dir: NonEmptyStr = Field(..., description="Runs output directory")
