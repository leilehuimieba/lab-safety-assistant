#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -f .env.web_demo ]]; then
  echo "[信息] 未找到 .env.web_demo，默认检查端口 8088。"
  port=8088
else
  set -a
  source .env.web_demo
  set +a
  port="${DEMO_PORT:-8088}"
fi

if [[ -f run/web_demo.pid ]]; then
  pid="$(cat run/web_demo.pid || true)"
  if [[ -n "${pid}" ]] && ps -p "${pid}" >/dev/null 2>&1; then
    echo "[运行中] PID=${pid}"
  else
    echo "[异常] PID 文件存在但进程不存在。"
  fi
else
  echo "[未运行] 未找到 PID 文件。"
fi

echo "[探活] http://127.0.0.1:${port}/health"
curl -sS "http://127.0.0.1:${port}/health" || true
echo

