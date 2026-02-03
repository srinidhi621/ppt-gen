"""Shared Pydantic base model helpers."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict


class PptxBaseModel(BaseModel):
    """Base model enforcing strict fields and stable JSON output."""

    model_config = ConfigDict(extra="forbid")

    def to_dict(self) -> dict[str, Any]:
        """Return a deterministic dict representation."""
        return self.model_dump(by_alias=True, exclude_none=False)

    def to_json(self) -> str:
        """Return deterministic JSON with sorted keys."""
        return json.dumps(self.to_dict(), sort_keys=True, ensure_ascii=True)
