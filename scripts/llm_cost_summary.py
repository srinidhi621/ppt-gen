#!/usr/bin/env python3
"""Print a summary of LLM API costs from the cost log CSV.

Usage::

    python scripts/llm_cost_summary.py              # default log path
    python scripts/llm_cost_summary.py --log runs/llm_cost_log.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure project root is on sys.path
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.v3.cost_logger import CostLogger


def main() -> None:
    parser = argparse.ArgumentParser(description="Print LLM cost summary")
    parser.add_argument(
        "--log",
        type=Path,
        default=None,
        help="Path to cost log CSV (default: runs/llm_cost_log.csv)",
    )
    args = parser.parse_args()

    logger = CostLogger(log_path=args.log)
    print(logger.summarize())


if __name__ == "__main__":
    main()
