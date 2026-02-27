"""Token pricing helpers for cost estimates."""

from __future__ import annotations

import os
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
        rate = _rate_from_env(provider)
    if rate is None:
        return None
    in_cost = (prompt_tokens / 1_000_000.0) * rate.input_per_million_usd
    out_cost = (completion_tokens / 1_000_000.0) * rate.output_per_million_usd
    return round(in_cost + out_cost, 8)


def _rate_from_env(provider: str) -> Optional[TokenRate]:
    """Allow runtime pricing config for providers/models not in defaults."""
    prefix = provider.upper()
    in_key = f"{prefix}_INPUT_USD_PER_MILLION"
    out_key = f"{prefix}_OUTPUT_USD_PER_MILLION"
    in_rate = _parse_positive_float(os.environ.get(in_key, ""))
    out_rate = _parse_positive_float(os.environ.get(out_key, ""))
    if in_rate is not None and out_rate is not None:
        return TokenRate(in_rate, out_rate)

    # Global fallback keys if provider-specific keys are not supplied.
    global_in = _parse_positive_float(os.environ.get("LLM_INPUT_USD_PER_MILLION", ""))
    global_out = _parse_positive_float(os.environ.get("LLM_OUTPUT_USD_PER_MILLION", ""))
    if global_in is not None and global_out is not None:
        return TokenRate(global_in, global_out)
    return None


def _parse_positive_float(value: str) -> Optional[float]:
    raw = value.strip()
    if not raw:
        return None
    try:
        parsed = float(raw)
    except ValueError:
        return None
    return parsed if parsed > 0 else None
