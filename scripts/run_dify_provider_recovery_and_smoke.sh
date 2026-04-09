#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PY_SCRIPT="${REPO_ROOT}/scripts/release/recover_dify_provider_and_smoke.py"
ENV_FILE_DEFAULT="${REPO_ROOT}/deploy/env/dify_provider_recovery.example.env"
ENV_FILE="${1:-${ENV_FILE_DEFAULT}}"

if [[ ! -f "${PY_SCRIPT}" ]]; then
  echo "[ERROR] python script not found: ${PY_SCRIPT}" >&2
  exit 2
fi

if [[ -f "${ENV_FILE}" ]]; then
  echo "[INFO] loading env file: ${ENV_FILE}"
  # shellcheck disable=SC1090
  set -a && source "${ENV_FILE}" && set +a
else
  echo "[WARN] env file not found: ${ENV_FILE}; fallback to current shell env"
fi

strip_cr_var() {
  local name="$1"
  local value="${!name-}"
  value="${value//$'\r'/}"
  printf -v "$name" "%s" "$value"
}

for var in \
  DIFY_TENANT_ID \
  DIFY_ENDPOINT_URL \
  DIFY_ENDPOINT_MODEL_NAME \
  OPENAI_COMPAT_API_KEY \
  DIFY_APP_TOKEN \
  DIFY_API_BASE \
  DIFY_PROVIDER_NAME \
  DIFY_MODEL_NAME \
  DIFY_MODEL_TYPE \
  DIFY_SMOKE_QUERY \
  DIFY_SMOKE_USER \
  DIFY_SMOKE_TIMEOUT_SEC \
  DIFY_API_CONTAINER; do
  strip_cr_var "$var"
done

python3 "${PY_SCRIPT}" \
  --tenant-id "${DIFY_TENANT_ID:?DIFY_TENANT_ID is required}" \
  --endpoint-url "${DIFY_ENDPOINT_URL:?DIFY_ENDPOINT_URL is required}" \
  --endpoint-model-name "${DIFY_ENDPOINT_MODEL_NAME:-${DIFY_MODEL_NAME:-gpt-5.2-codex}}" \
  --api-key "${OPENAI_COMPAT_API_KEY:?OPENAI_COMPAT_API_KEY is required}" \
  --app-token "${DIFY_APP_TOKEN:?DIFY_APP_TOKEN is required}" \
  --api-base "${DIFY_API_BASE:-http://127.0.0.1:8080}" \
  --provider-name "${DIFY_PROVIDER_NAME:-langgenius/openai_api_compatible/openai_api_compatible}" \
  --model-name "${DIFY_MODEL_NAME:-gpt-5.2-codex}" \
  --model-type "${DIFY_MODEL_TYPE:-llm}" \
  --query "${DIFY_SMOKE_QUERY:-实验室发生化学品泄漏时，第一步怎么做？}" \
  --user "${DIFY_SMOKE_USER:-recovery-smoke}" \
  --timeout-sec "${DIFY_SMOKE_TIMEOUT_SEC:-240}" \
  ${DIFY_API_CONTAINER:+--api-container "${DIFY_API_CONTAINER}"}
