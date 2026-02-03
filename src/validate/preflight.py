"""Preflight validation + remediation (scaffold)."""

from __future__ import annotations

from typing import Tuple

from ..models.deck_ir import DeckIR
from ..models.validation import ValidationReport


def validate_and_remediate(deck: DeckIR) -> Tuple[DeckIR, ValidationReport]:
    """Validate and remediate DeckIR, returning (deck_v1_1, report)."""
    raise NotImplementedError("Preflight validation is not implemented yet")
