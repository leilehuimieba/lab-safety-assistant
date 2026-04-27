#!/usr/bin/env bash
set -euo pipefail

MARK_BEGIN="# >>> lab-safe-go-live-bundle >>>"
MARK_END="# <<< lab-safe-go-live-bundle <<<"

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

crontab "$UPDATED"
echo "[cron] go-live bundle schedule removed."
