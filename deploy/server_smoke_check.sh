#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIFY_BASE_URL="http://127.0.0.1:8080"
WEB_BASE_URL=""
TIMEOUT_SEC=12
VERBOSE=0
DIFY_APP_TOKEN=""
DIFY_SMOKE_QUERY="实验室发生化学品泄漏时，第一步应该做什么？"
SKIP_DIFY_BUSINESS_SMOKE=0

usage() {
  cat <<'EOF'
Usage: deploy/server_smoke_check.sh [options]

Options:
  --repo-root PATH        Repo root on the server.
  --dify-base-url URL     Dify base URL. Default: http://127.0.0.1:8080
  --web-base-url URL      Web demo base URL. Default: infer from .env.web_demo or 8088
  --dify-app-token TOKEN  Dify app token. Default: env DIFY_APP_TOKEN or auto-resolve from DB.
  --dify-smoke-query TXT  Query used for real Dify business smoke.
  --skip-dify-business-smoke
                          Skip the real /v1/chat-messages workflow smoke.
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
    --dify-app-token)
      DIFY_APP_TOKEN="$2"
      shift 2
      ;;
    --dify-smoke-query)
      DIFY_SMOKE_QUERY="$2"
      shift 2
      ;;
    --skip-dify-business-smoke)
      SKIP_DIFY_BUSINESS_SMOKE=1
      shift
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

resolve_dify_app_token() {
  if [[ -n "$DIFY_APP_TOKEN" ]]; then
    printf '%s' "$DIFY_APP_TOKEN"
    return 0
  fi
  if [[ -n "${DIFY_APP_TOKEN:-}" ]]; then
    printf '%s' "$DIFY_APP_TOKEN"
    return 0
  fi
  if ! command -v docker >/dev/null 2>&1; then
    return 1
  fi
  local db_container
  db_container="$(docker ps --format '{{.Names}}' | grep -E 'db_postgres-1$' | head -n 1 || true)"
  if [[ -z "$db_container" ]]; then
    return 1
  fi
  docker exec -i "$db_container" psql -U postgres -d dify -At -F '|' -c \
    "select token from api_tokens where type='app' order by created_at desc limit 1;" 2>/dev/null | head -n 1 | tr -d '\r'
}

if [[ "$SKIP_DIFY_BUSINESS_SMOKE" != "1" ]]; then
  RESOLVED_DIFY_APP_TOKEN="$(resolve_dify_app_token || true)"
  if [[ -z "$RESOLVED_DIFY_APP_TOKEN" ]]; then
    record_fail "dify_business_smoke" "unable to resolve Dify app token"
  else
    PYTHON_BIN="python3"
    if [[ -x "$REPO_ROOT/.venv/bin/python" ]]; then
      PYTHON_BIN="$REPO_ROOT/.venv/bin/python"
    fi
    BUSINESS_SMOKE_JSON="$REPO_ROOT/artifacts/ops/dify_business_smoke_latest.json"
    if "$PYTHON_BIN" "$REPO_ROOT/scripts/release/dify_business_smoke.py" \
      --api-base "$DIFY_BASE_URL" \
      --app-token "$RESOLVED_DIFY_APP_TOKEN" \
      --query "$DIFY_SMOKE_QUERY" \
      --user "server-smoke-check" \
      --timeout-sec "$(( TIMEOUT_SEC > 30 ? TIMEOUT_SEC * 10 : 120 ))" \
      --output-json "$BUSINESS_SMOKE_JSON" >/tmp/dify_business_smoke_stdout.log 2>/tmp/dify_business_smoke_stderr.log; then
      record_pass "dify_business_smoke" "$BUSINESS_SMOKE_JSON"
      if [[ "$VERBOSE" == "1" ]]; then
        cat /tmp/dify_business_smoke_stdout.log
      fi
    else
      detail="$(tr '\n' ' ' </tmp/dify_business_smoke_stderr.log | cut -c1-220)"
      if [[ -z "$detail" ]]; then
        detail="$(tr '\n' ' ' </tmp/dify_business_smoke_stdout.log | cut -c1-220)"
      fi
      record_fail "dify_business_smoke" "${detail:-business smoke failed}"
    fi
  fi
fi

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
  echo "skip_dify_business_smoke=$SKIP_DIFY_BUSINESS_SMOKE"
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
