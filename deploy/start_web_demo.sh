#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p logs run

if [[ ! -f ".env.web_demo" ]]; then
  cp deploy/.env.web_demo.example .env.web_demo
  echo "[错误] 未找到 .env.web_demo，已自动生成模板。"
  echo "请先编辑 .env.web_demo 填写 OPENAI_API_KEY 后重试。"
  exit 1
fi

set -a
source .env.web_demo
set +a

if [[ ( -z "${OPENAI_API_KEY:-}" || "${OPENAI_API_KEY}" == "请替换成你的key" ) && -z "${DIFY_APP_API_KEY:-}" ]]; then
  echo "[错误] .env.web_demo 中至少要配置 DIFY_APP_API_KEY 或 OPENAI_API_KEY。"
  exit 1
fi

RUN_CMD=()
if [[ ! -d ".venv" ]]; then
  if ! python3 -m venv .venv >/dev/null 2>&1; then
    echo "[信息] 当前环境不支持 venv（通常缺少 python3-venv），切换到 user 模式。"
  fi
fi

if [[ -d ".venv" ]]; then
  if .venv/bin/pip install -r web_demo/requirements.txt >/dev/null 2>&1; then
    RUN_CMD=(.venv/bin/uvicorn)
  else
    echo "[信息] venv 安装依赖失败，切换到 user 模式。"
  fi
fi

if [[ ${#RUN_CMD[@]} -eq 0 ]]; then
  python3 -m pip install --user -r web_demo/requirements.txt >/dev/null
  RUN_CMD=(python3 -m uvicorn)
fi

if [[ -f run/web_demo.pid ]]; then
  old_pid="$(cat run/web_demo.pid || true)"
  if [[ -n "${old_pid}" ]] && ps -p "${old_pid}" >/dev/null 2>&1; then
    echo "[信息] 检测到旧进程 PID=${old_pid}，先停止。"
    kill "${old_pid}" || true
    sleep 1
  fi
fi

DEMO_PORT="${DEMO_PORT:-8088}"
nohup "${RUN_CMD[@]}" web_demo.app:app --host 0.0.0.0 --port "${DEMO_PORT}" > logs/web_demo.log 2>&1 &
echo $! > run/web_demo.pid

READY=0
for _ in $(seq 1 20); do
  if ! ps -p "$(cat run/web_demo.pid)" >/dev/null 2>&1; then
    break
  fi
  if curl -fsS "http://127.0.0.1:${DEMO_PORT}/health" >/dev/null 2>&1; then
    READY=1
    break
  fi
  sleep 1
done

if [[ "$READY" == "1" ]] && ps -p "$(cat run/web_demo.pid)" >/dev/null 2>&1; then
  echo "[成功] 演示服务已启动。"
  echo "PID: $(cat run/web_demo.pid)"
  echo "URL: http://$(hostname -I | awk '{print $1}'):${DEMO_PORT}"
  echo "日志: ${ROOT_DIR}/logs/web_demo.log"
else
  echo "[失败] 演示服务启动失败，请查看日志。"
  exit 1
fi
