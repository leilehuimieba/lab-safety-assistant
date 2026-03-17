#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -f run/cloudflared.pid ]]; then
  echo "[信息] 未找到 run/cloudflared.pid。"
  exit 0
fi

pid="$(cat run/cloudflared.pid || true)"
if [[ -n "${pid}" ]] && ps -p "${pid}" >/dev/null 2>&1; then
  kill "${pid}" || true
  sleep 1
  if ps -p "${pid}" >/dev/null 2>&1; then
    kill -9 "${pid}" || true
  fi
  echo "[成功] 已停止 cloudflared。PID=${pid}"
else
  echo "[信息] cloudflared 进程不存在。"
fi

rm -f run/cloudflared.pid

