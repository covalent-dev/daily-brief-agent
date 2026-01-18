#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/Users/taxman/covalent-dev/daily-brief-agent"
VENV_PATH="$PROJECT_ROOT/.venv"
PYTHON_BIN="$VENV_PATH/bin/python"
VAULT_PATH="/Users/taxman/Taxman_Progression_v4/05_Knowledge_Base/Daily-Briefs"
MIN_HOUR=5

log() {
  echo "$(date '+%Y-%m-%d %H:%M:%S') - $*"
}

is_reachable() {
  local host="$1"
  /usr/sbin/scutil -r "$host" 2>/dev/null | /usr/bin/grep -q "Reachable"
}

today="$(date +%Y-%m-%d)"
hour="$(date +%H)"
output_md="$PROJECT_ROOT/output/brief_${today}.md"
vault_md="$VAULT_PATH/brief_${today}.md"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Python not found at $PYTHON_BIN"
  echo "Create venv: python3 -m venv $VENV_PATH"
  exit 1
fi

cd "$PROJECT_ROOT"

if (( 10#${hour} < MIN_HOUR )); then
  log "Skipping run before ${MIN_HOUR}:00 (hour=${hour})" >> "$PROJECT_ROOT/output/launchd.log"
  exit 0
fi

if [[ -s "$output_md" || -s "$vault_md" ]]; then
  log "Brief already exists for ${today}, skipping" >> "$PROJECT_ROOT/output/launchd.log"
  exit 0
fi

if ! is_reachable "www.apple.com"; then
  log "Network not reachable; will retry later" >> "$PROJECT_ROOT/output/launchd.log"
  exit 0
fi

"$HOME/.local/bin/dailybrief" --create-only
"$PYTHON_BIN" src/brief.py >> "$PROJECT_ROOT/output/launchd.log" 2>&1
"$PYTHON_BIN" scripts/notify_email.py >> "$PROJECT_ROOT/output/launchd.log" 2>&1
