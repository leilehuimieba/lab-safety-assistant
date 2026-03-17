#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -f run/web_demo.pid ]]; then
  echo "[信息] 未找到 PID 文件，服务可能未启动。"
  exit 0
fi

pid="$(cat run/web_demo.pid || true)"
if [[ -z "${pid}" ]]; then
  echo "[信息] PID 文件为空。"
  rm -f run/web_demo.pid
  exit 0
fi

if ps -p "${pid}" >/dev/null 2>&1; then
  kill "${pid}" || true
  sleep 1
  if ps -p "${pid}" >/dev/null 2>&1; then
    kill -9 "${pid}" || true
  fi
  echo "[成功] 演示服务已停止。PID=${pid}"
else
  echo "[信息] 进程不存在，清理 PID 文件。"
fi

rm -f run/web_demo.pid

