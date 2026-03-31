#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

declare -a TARGET_PIDS=()

if [[ -f run/web_demo.pid ]]; then
  pid="$(cat run/web_demo.pid || true)"
  if [[ -n "${pid}" ]] && ps -p "${pid}" >/dev/null 2>&1; then
    TARGET_PIDS+=("${pid}")
  fi
fi

while IFS= read -r fallback_pid; do
  if [[ -n "${fallback_pid}" ]]; then
    TARGET_PIDS+=("${fallback_pid}")
  fi
done < <(pgrep -f 'uvicorn web_demo.app:app' || true)

if [[ ${#TARGET_PIDS[@]} -eq 0 ]]; then
  echo "[info] no running web demo process found."
  rm -f run/web_demo.pid
  exit 0
fi

UNIQUE_PIDS="$(printf '%s\n' "${TARGET_PIDS[@]}" | awk '!seen[$0]++')"
while IFS= read -r target_pid; do
  [[ -z "${target_pid}" ]] && continue
  kill "${target_pid}" || true
  sleep 1
  if ps -p "${target_pid}" >/dev/null 2>&1; then
    kill -9 "${target_pid}" || true
  fi
  echo "[ok] stopped web demo pid=${target_pid}"
done <<< "${UNIQUE_PIDS}"

rm -f run/web_demo.pid
