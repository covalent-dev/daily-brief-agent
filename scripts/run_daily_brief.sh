#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/Users/taxman/covalent-dev/daily-brief-agent"
VENV_PATH="$PROJECT_ROOT/.venv"
PYTHON_BIN="$VENV_PATH/bin/python"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Python not found at $PYTHON_BIN"
  echo "Create venv: python3 -m venv $VENV_PATH"
  exit 1
fi

cd "$PROJECT_ROOT"
"$PYTHON_BIN" src/brief.py >> "$PROJECT_ROOT/output/launchd.log" 2>&1
