#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -f run/cloudflared.pid ]]; then
  pid="$(cat run/cloudflared.pid || true)"
  if [[ -n "${pid}" ]] && ps -p "${pid}" >/dev/null 2>&1; then
    echo "[运行中] cloudflared PID=${pid}"
  else
    echo "[异常] PID 文件存在但进程不存在。"
  fi
else
  echo "[未运行] 未找到 cloudflared PID 文件。"
fi

url="$(grep -Eo 'https://[-a-z0-9]+\.trycloudflare\.com' logs/cloudflared.log | head -n 1 || true)"
if [[ -n "${url}" ]]; then
  echo "[地址] ${url}"
else
  echo "[地址] 暂未解析到 trycloudflare 链接。"
fi

