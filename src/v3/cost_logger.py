"""Persistent CSV cost logger for V3 LLM calls.

Every API call is appended as a row to ``runs/llm_cost_log.csv``.
The file is human-readable and can be opened in any spreadsheet tool.

Usage::

    from src.v3.cost_logger import CostLogger

    logger = CostLogger()                       # default path
    logger.log_call("gpt-5.4", "generate_json", "planner",
                    input_tokens=500, output_tokens=200,
                    prompt_preview="Plan a 6-slide deck...")
    logger.print_summary()                      # daily/weekly/monthly rollups
"""

from __future__ import annotations

import csv
import fcntl
import logging
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

_logger = logging.getLogger(__name__)

_ENV_COST_LOG_ENABLED = "V3_COST_LOG_ENABLED"
_ENV_COST_LOG_PATH = "V3_COST_LOG_PATH"
_FALSEY_ENV_VALUES = {"0", "false", "no", "off", "disabled"}


# ---------------------------------------------------------------------------
# Default pricing (per million tokens)
# ---------------------------------------------------------------------------

# These are configurable via .env.  When not set, we use zeros so rows still
# record tokens even without cost data.
_DEFAULT_PRICING: dict[str, tuple[float, float]] = {
    # model_prefix: (input_usd_per_M, output_usd_per_M)
    # Users fill AZURE_OPENAI_INPUT_USD_PER_MILLION / OUTPUT in .env
    # or per-model overrides via V3_COST_<MODEL_SLUG>_INPUT / OUTPUT
}
_DEFAULT_INR_PRICING: dict[str, tuple[float, float]] = {
    # model_prefix: (input_inr_per_M, output_inr_per_M)
    # Users fill AZURE_OPENAI_INPUT_INR_PER_MILLION / OUTPUT in .env
    # or per-model overrides via V3_COST_<MODEL_SLUG>_INPUT_INR / OUTPUT_INR
}


def _project_root() -> Path:
    """Return the repository root for repo-relative defaults."""
    return Path(__file__).resolve().parent.parent.parent


def resolve_cost_log_path(log_path: str | Path | None = None) -> Path:
    """Resolve the persistent cost log path.

    Precedence:
    1. Explicit ``log_path`` argument
    2. ``V3_COST_LOG_PATH`` environment variable
    3. Repo default ``runs/llm_cost_log.csv``
    """
    if log_path is not None:
        return Path(log_path)

    env_path = os.environ.get(_ENV_COST_LOG_PATH, "").strip()
    if env_path:
        path = Path(env_path).expanduser()
        if not path.is_absolute():
            path = _project_root() / path
        return path

    return _project_root() / "runs" / "llm_cost_log.csv"


def cost_logging_enabled(default: bool = True) -> bool:
    """Return whether application-bootstrapped cost logging is enabled."""
    raw = os.environ.get(_ENV_COST_LOG_ENABLED)
    if raw is None:
        return default
    return raw.strip().lower() not in _FALSEY_ENV_VALUES


def _get_pricing(model: str) -> tuple[float, float]:
    """Return USD (input_cost_per_M_tokens, output_cost_per_M_tokens)."""
    # Try per-model env var first: V3_COST_GPT_5_4_INPUT, V3_COST_GPT_5_4_OUTPUT
    slug = model.replace("-", "_").replace(".", "_").upper()
    input_rate = os.environ.get(f"V3_COST_{slug}_INPUT")
    output_rate = os.environ.get(f"V3_COST_{slug}_OUTPUT")

    if input_rate and output_rate:
        return float(input_rate), float(output_rate)

    # Fall back to global env vars
    input_rate = os.environ.get("AZURE_OPENAI_INPUT_USD_PER_MILLION", "")
    output_rate = os.environ.get("AZURE_OPENAI_OUTPUT_USD_PER_MILLION", "")

    if input_rate and output_rate:
        return float(input_rate), float(output_rate)

    return 0.0, 0.0


def _get_pricing_inr(model: str) -> tuple[float, float]:
    """Return INR (input_cost_per_M_tokens, output_cost_per_M_tokens)."""
    slug = model.replace("-", "_").replace(".", "_").upper()
    input_rate = os.environ.get(f"V3_COST_{slug}_INPUT_INR")
    output_rate = os.environ.get(f"V3_COST_{slug}_OUTPUT_INR")

    if input_rate and output_rate:
        return float(input_rate), float(output_rate)

    input_rate = os.environ.get("AZURE_OPENAI_INPUT_INR_PER_MILLION", "")
    output_rate = os.environ.get("AZURE_OPENAI_OUTPUT_INR_PER_MILLION", "")

    if input_rate and output_rate:
        return float(input_rate), float(output_rate)

    for prefix, rates in _DEFAULT_INR_PRICING.items():
        if model.startswith(prefix):
            return rates

    return 0.0, 0.0


# ---------------------------------------------------------------------------
# CSV schema
# ---------------------------------------------------------------------------

_CSV_COLUMNS = [
    "timestamp",          # ISO-8601 UTC
    "date",               # YYYY-MM-DD (for easy grouping)
    "model",              # e.g. gpt-5.4
    "method",             # generate_json | generate_code | generate_json_with_images
    "caller",             # planner | builder | reviewer | retry | unknown
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "input_cost_usd",     # computed from tokens * rate
    "output_cost_usd",
    "total_cost_usd",
    "input_cost_inr",
    "output_cost_inr",
    "total_cost_inr",
    "response_id",        # Responses API id
    "prompt_preview",     # first 200 chars of the input, for debugging
]


# ---------------------------------------------------------------------------
# CostLogger
# ---------------------------------------------------------------------------

class CostLogger:
    """Append-only CSV logger for LLM API costs."""

    def __init__(self, log_path: str | Path | None = None):
        self.log_path = resolve_cost_log_path(log_path)

    def log_call(
        self,
        model: str,
        method: str,
        caller: str = "unknown",
        *,
        input_tokens: int = 0,
        output_tokens: int = 0,
        total_tokens: int = 0,
        response_id: str = "",
        prompt_preview: str = "",
    ) -> dict:
        """Append one row to the cost log.

        Returns the row dict for convenience (e.g. for testing).
        """
        now = datetime.now(timezone.utc)
        input_rate, output_rate = _get_pricing(model)
        input_rate_inr, output_rate_inr = _get_pricing_inr(model)

        input_cost = (input_tokens / 1_000_000) * input_rate
        output_cost = (output_tokens / 1_000_000) * output_rate
        total_cost = input_cost + output_cost
        input_cost_inr = (input_tokens / 1_000_000) * input_rate_inr
        output_cost_inr = (output_tokens / 1_000_000) * output_rate_inr
        total_cost_inr = input_cost_inr + output_cost_inr

        if not total_tokens:
            total_tokens = input_tokens + output_tokens

        # Sanitize prompt preview: collapse whitespace, truncate, strip newlines
        preview = " ".join(prompt_preview.split())[:200]

        row = {
            "timestamp": now.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "date": now.strftime("%Y-%m-%d"),
            "model": model,
            "method": method,
            "caller": caller,
            "input_tokens": str(input_tokens),
            "output_tokens": str(output_tokens),
            "total_tokens": str(total_tokens),
            "input_cost_usd": f"{input_cost:.6f}",
            "output_cost_usd": f"{output_cost:.6f}",
            "total_cost_usd": f"{total_cost:.6f}",
            "input_cost_inr": f"{input_cost_inr:.6f}",
            "output_cost_inr": f"{output_cost_inr:.6f}",
            "total_cost_inr": f"{total_cost_inr:.6f}",
            "response_id": response_id,
            "prompt_preview": preview,
        }

        self._append_row(row)
        return row

    def _append_row(self, row: dict) -> None:
        """Append a row to the CSV, creating the file + header if needed.

        Uses fcntl advisory locking so concurrent processes don't interleave
        partial lines.
        """
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        write_header = not self.log_path.exists() or self.log_path.stat().st_size == 0

        with open(self.log_path, "a", newline="", encoding="utf-8") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                # Re-check after acquiring lock — another writer may have created header
                if write_header and self.log_path.stat().st_size > 0:
                    write_header = False
                writer = csv.DictWriter(f, fieldnames=_CSV_COLUMNS)
                if write_header:
                    writer.writeheader()
                writer.writerow(row)
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)

    # ------------------------------------------------------------------
    # Summary / reader
    # ------------------------------------------------------------------

    def read_log(self) -> list[dict]:
        """Read all rows from the cost log, skipping malformed rows."""
        if not self.log_path.exists():
            return []
        rows: list[dict] = []
        try:
            with open(self.log_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for line_no, row in enumerate(reader, start=2):
                    # Skip rows that are completely empty or lack required fields
                    if not row.get("timestamp"):
                        _logger.debug("Skipping malformed row at line %d", line_no)
                        continue
                    rows.append(row)
        except (csv.Error, UnicodeDecodeError) as exc:
            _logger.warning("Error reading cost log %s: %s", self.log_path, exc)
        return rows

    def summarize(self) -> str:
        """Generate a human-readable summary of costs by day, week, and month.

        Returns a formatted string suitable for printing to terminal or saving.
        """
        rows = self.read_log()
        if not rows:
            return "No LLM calls logged yet."

        has_inr = any(float(r.get("total_cost_inr") or 0) > 0 for r in rows)
        cost_key = "total_cost_inr" if has_inr else "total_cost_usd"
        currency_label = "INR" if has_inr else "USD"
        currency_symbol = "₹" if has_inr else "$"

        # Parse into structured data, tolerating bad values
        calls = []
        for r in rows:
            try:
                dt = datetime.strptime(r["date"], "%Y-%m-%d")
                calls.append({
                    "date": r["date"],
                    "week": dt.strftime("%Y-W%W"),
                    "month": dt.strftime("%Y-%m"),
                    "model": r.get("model", "?"),
                    "caller": r.get("caller", "?"),
                    "input_tokens": int(r.get("input_tokens") or 0),
                    "output_tokens": int(r.get("output_tokens") or 0),
                    "total_cost": float(r.get(cost_key) or 0),
                })
            except (ValueError, KeyError, TypeError):
                continue

        lines = []
        lines.append("=" * 72)
        lines.append("LLM COST SUMMARY")
        lines.append(f"Log file: {self.log_path}")
        lines.append(f"Total calls: {len(calls)}")
        lines.append("=" * 72)

        # Grand totals
        total_in = sum(c["input_tokens"] for c in calls)
        total_out = sum(c["output_tokens"] for c in calls)
        total_cost = sum(c["total_cost"] for c in calls)
        lines.append("")
        lines.append(f"  Total input tokens:  {total_in:>12,}")
        lines.append(f"  Total output tokens: {total_out:>12,}")
        lines.append(f"  Total cost:          {currency_symbol}{total_cost:>11,.4f}")

        # By model
        lines.append("")
        lines.append("--- By Model ---")
        by_model: dict[str, dict] = defaultdict(lambda: {"calls": 0, "in": 0, "out": 0, "cost": 0.0})
        for c in calls:
            m = by_model[c["model"]]
            m["calls"] += 1
            m["in"] += c["input_tokens"]
            m["out"] += c["output_tokens"]
            m["cost"] += c["total_cost"]
        lines.append(f"  {'Model':<20} {'Calls':>6} {'Input Tok':>12} {'Output Tok':>12} {('Cost ' + currency_label):>12}")
        lines.append(f"  {'-'*20} {'-'*6} {'-'*12} {'-'*12} {'-'*12}")
        for model in sorted(by_model):
            m = by_model[model]
            lines.append(f"  {model:<20} {m['calls']:>6} {m['in']:>12,} {m['out']:>12,} {currency_symbol}{m['cost']:>11,.4f}")

        # By caller
        lines.append("")
        lines.append("--- By Caller ---")
        by_caller: dict[str, dict] = defaultdict(lambda: {"calls": 0, "in": 0, "out": 0, "cost": 0.0})
        for c in calls:
            m = by_caller[c["caller"]]
            m["calls"] += 1
            m["in"] += c["input_tokens"]
            m["out"] += c["output_tokens"]
            m["cost"] += c["total_cost"]
        lines.append(f"  {'Caller':<20} {'Calls':>6} {'Input Tok':>12} {'Output Tok':>12} {('Cost ' + currency_label):>12}")
        lines.append(f"  {'-'*20} {'-'*6} {'-'*12} {'-'*12} {'-'*12}")
        for caller in sorted(by_caller):
            m = by_caller[caller]
            lines.append(f"  {caller:<20} {m['calls']:>6} {m['in']:>12,} {m['out']:>12,} {currency_symbol}{m['cost']:>11,.4f}")

        # Daily
        lines.append("")
        lines.append("--- Daily ---")
        by_day: dict[str, dict] = defaultdict(lambda: {"calls": 0, "in": 0, "out": 0, "cost": 0.0})
        for c in calls:
            m = by_day[c["date"]]
            m["calls"] += 1
            m["in"] += c["input_tokens"]
            m["out"] += c["output_tokens"]
            m["cost"] += c["total_cost"]
        lines.append(f"  {'Date':<12} {'Calls':>6} {'Input Tok':>12} {'Output Tok':>12} {('Cost ' + currency_label):>12}")
        lines.append(f"  {'-'*12} {'-'*6} {'-'*12} {'-'*12} {'-'*12}")
        for date in sorted(by_day):
            m = by_day[date]
            lines.append(f"  {date:<12} {m['calls']:>6} {m['in']:>12,} {m['out']:>12,} {currency_symbol}{m['cost']:>11,.4f}")

        # Weekly
        lines.append("")
        lines.append("--- Weekly ---")
        by_week: dict[str, dict] = defaultdict(lambda: {"calls": 0, "in": 0, "out": 0, "cost": 0.0})
        for c in calls:
            m = by_week[c["week"]]
            m["calls"] += 1
            m["in"] += c["input_tokens"]
            m["out"] += c["output_tokens"]
            m["cost"] += c["total_cost"]
        lines.append(f"  {'Week':<12} {'Calls':>6} {'Input Tok':>12} {'Output Tok':>12} {('Cost ' + currency_label):>12}")
        lines.append(f"  {'-'*12} {'-'*6} {'-'*12} {'-'*12} {'-'*12}")
        for week in sorted(by_week):
            m = by_week[week]
            lines.append(f"  {week:<12} {m['calls']:>6} {m['in']:>12,} {m['out']:>12,} {currency_symbol}{m['cost']:>11,.4f}")

        # Monthly
        lines.append("")
        lines.append("--- Monthly ---")
        by_month: dict[str, dict] = defaultdict(lambda: {"calls": 0, "in": 0, "out": 0, "cost": 0.0})
        for c in calls:
            m = by_month[c["month"]]
            m["calls"] += 1
            m["in"] += c["input_tokens"]
            m["out"] += c["output_tokens"]
            m["cost"] += c["total_cost"]
        lines.append(f"  {'Month':<12} {'Calls':>6} {'Input Tok':>12} {'Output Tok':>12} {('Cost ' + currency_label):>12}")
        lines.append(f"  {'-'*12} {'-'*6} {'-'*12} {'-'*12} {'-'*12}")
        for month in sorted(by_month):
            m = by_month[month]
            lines.append(f"  {month:<12} {m['calls']:>6} {m['in']:>12,} {m['out']:>12,} {currency_symbol}{m['cost']:>11,.4f}")

        lines.append("")
        lines.append("=" * 72)
        pricing_note = (
            "Costs are 0 — set AZURE_OPENAI_INPUT/OUTPUT_INR_PER_MILLION "
            "or AZURE_OPENAI_INPUT/OUTPUT_USD_PER_MILLION in .env"
        )
        if total_cost > 0:
            pricing_note = "Costs computed from env-configured rates"
        lines.append(f"  Note: {pricing_note}")
        lines.append("")

        return "\n".join(lines)

    def print_summary(self) -> None:
        """Print the cost summary to stdout."""
        print(self.summarize())
