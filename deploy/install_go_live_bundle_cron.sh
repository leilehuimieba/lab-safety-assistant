#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

ENV_FILE="${1:-$ROOT_DIR/deploy/env/go_live_bundle.env}"
CRON_SCHEDULE="${CRON_SCHEDULE:-20 2 * * *}"
LOG_FILE="${LOG_FILE:-$ROOT_DIR/artifacts/go_live_bundle/cron_daily.log}"
MARK_BEGIN="# >>> lab-safe-go-live-bundle >>>"
MARK_END="# <<< lab-safe-go-live-bundle <<<"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "[ERROR] env file not found: $ENV_FILE" >&2
  exit 2
fi

mkdir -p "$(dirname "$LOG_FILE")"

CURRENT="$(mktemp)"
UPDATED="$(mktemp)"
trap 'rm -f "$CURRENT" "$UPDATED"' EXIT

crontab -l >"$CURRENT" 2>/dev/null || true

awk -v b="$MARK_BEGIN" -v e="$MARK_END" '
  BEGIN{skip=0}
  $0==b {skip=1; next}
  $0==e {skip=0; next}
  skip==0 {print}
' "$CURRENT" >"$UPDATED"

{
  cat "$UPDATED"
  echo "$MARK_BEGIN"
  echo "$CRON_SCHEDULE cd \"$ROOT_DIR\" && /usr/bin/env bash \"$ROOT_DIR/deploy/run_server_go_live_bundle.sh\" \"$ENV_FILE\" >> \"$LOG_FILE\" 2>&1"
  echo "$MARK_END"
} >"$CURRENT"

crontab "$CURRENT"

echo "[cron] installed."
echo "- schedule: $CRON_SCHEDULE"
echo "- env file: $ENV_FILE"
echo "- log file: $LOG_FILE"
