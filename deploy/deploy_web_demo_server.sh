#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[1/4] Preparing env file..."
if [[ ! -f ".env.web_demo" ]]; then
  if [[ -f "deploy/.env.web_demo.server.example" ]]; then
    cp "deploy/.env.web_demo.server.example" ".env.web_demo"
  else
    cp "deploy/.env.web_demo.example" ".env.web_demo"
  fi
  echo "[warn] .env.web_demo created from template."
  echo "[warn] Please edit OPENAI_API_KEY in .env.web_demo before first launch."
fi

echo "[2/4] Checking python and uvicorn runtime..."
if ! command -v python3 >/dev/null 2>&1; then
  echo "[error] python3 not found. Please install Python 3.10+."
  exit 1
fi

echo "[3/4] Starting web demo..."
"$ROOT_DIR/deploy/start_web_demo.sh"

echo "[4/4] Service status..."
"$ROOT_DIR/deploy/status_web_demo.sh"

echo "[done] Web demo deployment command finished."
echo "Logs: $ROOT_DIR/logs/web_demo.log"
