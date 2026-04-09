#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"

cd "$ROOT_DIR"

if [ ! -d ".venv" ]; then
  "$PYTHON_BIN" -m venv .venv
fi

source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if ! command -v soffice >/dev/null 2>&1; then
  echo "WARN: soffice not found; review-image export will be unavailable."
fi

if ! command -v pdftoppm >/dev/null 2>&1; then
  echo "WARN: pdftoppm not found; review-image export will be unavailable."
fi

echo "OK Codex cloud setup complete"
