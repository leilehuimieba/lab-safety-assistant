#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

WEB_HEALTH_URL="${WEB_HEALTH_URL:-http://127.0.0.1:${DEMO_PORT:-8088}/health}"
RELEASE_DIR="${RELEASE_DIR:-release_exports/v8.1}"

echo "[go-live] repo: $ROOT_DIR"
echo "[go-live] release_dir: $RELEASE_DIR"
echo "[go-live] web_health_url: $WEB_HEALTH_URL"

python3 scripts/release/go_live_preflight.py \
  --repo-root . \
  --release-dir "$RELEASE_DIR" \
  --web-health-url "$WEB_HEALTH_URL" \
  --output-json docs/ops/go_live_readiness.json \
  --output-md docs/ops/go_live_readiness.md

echo "[go-live] done."
