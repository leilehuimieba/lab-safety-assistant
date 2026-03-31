#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIFY_BASE_URL="http://127.0.0.1:8080"
WEB_BASE_URL=""
TIMEOUT_SEC=12
VERBOSE=0

usage() {
  cat <<'EOF'
Usage: deploy/server_smoke_check.sh [options]

Options:
  --repo-root PATH        Repo root on the server.
  --dify-base-url URL     Dify base URL. Default: http://127.0.0.1:8080
  --web-base-url URL      Web demo base URL. Default: infer from .env.web_demo or 8088
  --timeout-sec N         Curl timeout in seconds. Default: 12
  --verbose               Print extra process and docker details.
  -h, --help              Show help.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo-root)
      REPO_ROOT="$2"
      shift 2
      ;;
    --dify-base-url)
      DIFY_BASE_URL="$2"
      shift 2
      ;;
    --web-base-url)
      WEB_BASE_URL="$2"
      shift 2
      ;;
    --timeout-sec)
      TIMEOUT_SEC="$2"
      shift 2
      ;;
    --verbose)
      VERBOSE=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[smoke] unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

REPO_ROOT="$(cd "$REPO_ROOT" && pwd)"

if [[ -z "$WEB_BASE_URL" ]]; then
  if [[ -f "$REPO_ROOT/.env.web_demo" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$REPO_ROOT/.env.web_demo"
    set +a
    WEB_BASE_URL="http://127.0.0.1:${DEMO_PORT:-8088}"
  else
    WEB_BASE_URL="http://127.0.0.1:8088"
  fi
fi

PASS_COUNT=0
FAIL_COUNT=0
REPORT_LINES=()

record_pass() {
  local label="$1"
  local detail="$2"
  PASS_COUNT=$((PASS_COUNT + 1))
  echo "[PASS] ${label}: ${detail}"
  REPORT_LINES+=("PASS | ${label} | ${detail}")
}

record_fail() {
  local label="$1"
  local detail="$2"
  FAIL_COUNT=$((FAIL_COUNT + 1))
  echo "[FAIL] ${label}: ${detail}" >&2
  REPORT_LINES+=("FAIL | ${label} | ${detail}")
}

check_http() {
  local label="$1"
  local url="$2"
  local expected_regex="$3"
  local code
  code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time "$TIMEOUT_SEC" "$url" || true)"
  if [[ "$code" =~ $expected_regex ]]; then
    record_pass "$label" "${url} -> ${code}"
  else
    record_fail "$label" "${url} -> ${code:-curl_error}"
  fi
}

echo "[smoke] repo root: $REPO_ROOT"
echo "[smoke] web base : $WEB_BASE_URL"
echo "[smoke] dify base: $DIFY_BASE_URL"

if [[ -d "$REPO_ROOT" ]]; then
  record_pass "repo_root" "$REPO_ROOT"
else
  record_fail "repo_root" "missing directory: $REPO_ROOT"
fi

if [[ -f "$REPO_ROOT/.env.web_demo" ]]; then
  record_pass "env_file" "$REPO_ROOT/.env.web_demo"
else
  record_fail "env_file" "missing .env.web_demo"
fi

if [[ -f "$REPO_ROOT/run/web_demo.pid" ]]; then
  WEB_PID="$(cat "$REPO_ROOT/run/web_demo.pid" 2>/dev/null || true)"
  if [[ -n "${WEB_PID:-}" ]] && ps -p "$WEB_PID" >/dev/null 2>&1; then
    record_pass "web_demo_pid" "pid=${WEB_PID}"
  else
    FALLBACK_PID="$(pgrep -f 'uvicorn web_demo.app:app' | head -n 1 || true)"
    if [[ -n "${FALLBACK_PID:-}" ]]; then
      record_pass "web_demo_process" "stale pid file detected; active pid=${FALLBACK_PID}"
    else
      record_fail "web_demo_pid" "pid file exists but process is not running"
    fi
  fi
else
  FALLBACK_PID="$(pgrep -f 'uvicorn web_demo.app:app' | head -n 1 || true)"
  if [[ -n "${FALLBACK_PID:-}" ]]; then
    record_pass "web_demo_process" "pid=${FALLBACK_PID} via pgrep"
  else
    record_fail "web_demo_process" "uvicorn web_demo.app:app not found"
  fi
fi

check_http "web_health" "${WEB_BASE_URL}/health" '^200$'
check_http "dashboard_api" "${WEB_BASE_URL}/api/admin/dashboard" '^200$'
check_http "training_stats_api" "${WEB_BASE_URL}/api/training/stats" '^200$'
check_http "incidents_api" "${WEB_BASE_URL}/api/incidents" '^200$'
check_http "dify_http" "${DIFY_BASE_URL}" '^(200|301|302|307|308)$'

if command -v docker >/dev/null 2>&1; then
  DIFY_CONTAINERS="$(docker ps --format '{{.Names}} {{.Status}}' | grep -E 'docker-(api|web|worker|db_postgres|redis)-1' || true)"
  if [[ -n "$DIFY_CONTAINERS" ]]; then
    record_pass "dify_containers" "core containers are visible"
    if [[ "$VERBOSE" == "1" ]]; then
      echo "$DIFY_CONTAINERS"
    fi
  else
    record_fail "dify_containers" "core containers not found in docker ps"
  fi
else
  record_fail "docker_binary" "docker command not found"
fi

if [[ "$VERBOSE" == "1" ]]; then
  echo "[smoke] process snapshot:"
  ps -ef | grep -E 'uvicorn|web_demo.app|docker|gunicorn' | grep -v grep || true
fi

mkdir -p "$REPO_ROOT/artifacts/ops"
REPORT_PATH="$REPO_ROOT/artifacts/ops/server_smoke_check_latest.txt"
{
  echo "generated_at=$(date '+%Y-%m-%d %H:%M:%S %z')"
  echo "repo_root=$REPO_ROOT"
  echo "web_base_url=$WEB_BASE_URL"
  echo "dify_base_url=$DIFY_BASE_URL"
  echo "pass_count=$PASS_COUNT"
  echo "fail_count=$FAIL_COUNT"
  printf '%s\n' "${REPORT_LINES[@]}"
} > "$REPORT_PATH"

echo "[smoke] report: $REPORT_PATH"
echo "[smoke] pass=${PASS_COUNT} fail=${FAIL_COUNT}"

if [[ "$FAIL_COUNT" -gt 0 ]]; then
  exit 1
fi

exit 0
