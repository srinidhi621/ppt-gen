"""Token pricing helpers for cost estimates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple


@dataclass(frozen=True)
class TokenRate:
    input_per_million_usd: float
    output_per_million_usd: float


# Defaults are estimates and can be overridden via env/CLI later.
DEFAULT_RATES: Dict[Tuple[str, str], TokenRate] = {
    ("gemini", "gemini-2.5-flash"): TokenRate(0.30, 2.50),
    ("gemini", "gemini-3-flash-preview"): TokenRate(0.40, 3.00),
}


def estimate_cost_usd(
    provider: str, model: str, prompt_tokens: int, completion_tokens: int
) -> Optional[float]:
    rate = DEFAULT_RATES.get((provider, model))
    if rate is None:
        return None
    in_cost = (prompt_tokens / 1_000_000.0) * rate.input_per_million_usd
    out_cost = (completion_tokens / 1_000_000.0) * rate.output_per_million_usd
    return round(in_cost + out_cost, 8)
