#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p logs run "$HOME/bin"

if [[ -f .env.web_demo ]]; then
  set -a
  source .env.web_demo
  set +a
fi
DEMO_PORT="${DEMO_PORT:-8088}"

if [[ -f run/cloudflared.pid ]]; then
  old_pid="$(cat run/cloudflared.pid || true)"
  if [[ -n "${old_pid}" ]] && ps -p "${old_pid}" >/dev/null 2>&1; then
    echo "[信息] 检测到旧隧道进程，先停止。PID=${old_pid}"
    kill "${old_pid}" || true
    sleep 1
  fi
fi

if [[ ! -x "$HOME/bin/cloudflared" ]]; then
  echo "[信息] 首次安装 cloudflared..."
  curl -L --fail \
    https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 \
    -o "$HOME/bin/cloudflared"
  chmod +x "$HOME/bin/cloudflared"
fi

nohup "$HOME/bin/cloudflared" tunnel --url "http://127.0.0.1:${DEMO_PORT}" --no-autoupdate > logs/cloudflared.log 2>&1 &
echo $! > run/cloudflared.pid

echo "[信息] 正在等待隧道地址生成..."
for i in {1..20}; do
  url="$(grep -Eo 'https://[-a-z0-9]+\.trycloudflare\.com' logs/cloudflared.log | head -n 1 || true)"
  if [[ -n "${url}" ]]; then
    echo "[成功] 公网临时地址：${url}"
    echo "[提示] 该地址为临时地址，重启隧道后会变化。"
    exit 0
  fi
  sleep 1
done

echo "[失败] 未在日志中解析到 trycloudflare 地址，请查看 logs/cloudflared.log"
exit 1

