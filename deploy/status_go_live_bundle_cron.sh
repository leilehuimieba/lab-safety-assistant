#!/usr/bin/env bash
set -euo pipefail

MARK_BEGIN="# >>> lab-safe-go-live-bundle >>>"
MARK_END="# <<< lab-safe-go-live-bundle <<<"

TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

crontab -l >"$TMP" 2>/dev/null || true

if grep -qF "$MARK_BEGIN" "$TMP"; then
  echo "[cron] go-live bundle schedule is installed."
  awk -v b="$MARK_BEGIN" -v e="$MARK_END" '
    $0==b {print; flag=1; next}
    flag==1 {print}
    $0==e {flag=0; exit}
  ' "$TMP"
else
  echo "[cron] go-live bundle schedule is not installed."
fi
