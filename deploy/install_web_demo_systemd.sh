#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_DIR="${REPO_DIR:-$ROOT_DIR}"
SERVICE_NAME="${SERVICE_NAME:-lab-safe-assistant-web-demo}"
ENV_FILE="${ENV_FILE:-$REPO_DIR/.env.web_demo}"
SERVICE_DIR="${HOME}/.config/systemd/user"
SERVICE_FILE="${SERVICE_DIR}/${SERVICE_NAME}.service"
TEMPLATE_FILE="${REPO_DIR}/deploy/systemd/web_demo.service.template"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "[error] missing env file: ${ENV_FILE}"
  echo "hint: cp deploy/.env.web_demo.server.example .env.web_demo && vi .env.web_demo"
  exit 1
fi

if [[ ! -f "${TEMPLATE_FILE}" ]]; then
  echo "[error] missing template: ${TEMPLATE_FILE}"
  exit 1
fi

if ! command -v systemctl >/dev/null 2>&1; then
  echo "[error] systemctl not found."
  exit 1
fi

if ! systemctl --user --version >/dev/null 2>&1; then
  echo "[error] user systemd unavailable."
  exit 1
fi

DEMO_PORT="$(grep -E '^DEMO_PORT=' "${ENV_FILE}" | tail -n 1 | cut -d'=' -f2- | tr -d '\r' || true)"
if [[ -z "${DEMO_PORT}" ]]; then
  DEMO_PORT="8088"
fi

PYTHON_BIN="${REPO_DIR}/.venv/bin/python"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="$(command -v python3 || true)"
fi
if [[ -z "${PYTHON_BIN}" ]]; then
  echo "[error] python3 not found."
  exit 1
fi

mkdir -p "${SERVICE_DIR}"

escaped_repo="$(printf '%s' "${REPO_DIR}" | sed 's/[\/&]/\\&/g')"
escaped_env="$(printf '%s' "${ENV_FILE}" | sed 's/[\/&]/\\&/g')"
escaped_py="$(printf '%s' "${PYTHON_BIN}" | sed 's/[\/&]/\\&/g')"
escaped_port="$(printf '%s' "${DEMO_PORT}" | sed 's/[\/&]/\\&/g')"

sed \
  -e "s/__REPO_DIR__/${escaped_repo}/g" \
  -e "s/__ENV_FILE__/${escaped_env}/g" \
  -e "s/__PYTHON_BIN__/${escaped_py}/g" \
  -e "s/__DEMO_PORT__/${escaped_port}/g" \
  "${TEMPLATE_FILE}" > "${SERVICE_FILE}"

echo "[info] service file written: ${SERVICE_FILE}"

systemctl --user daemon-reload
systemctl --user enable --now "${SERVICE_NAME}.service"

echo "[ok] ${SERVICE_NAME} enabled and started."
systemctl --user --no-pager --full status "${SERVICE_NAME}.service" | head -n 25 || true

echo ""
echo "Useful commands:"
echo "  systemctl --user status ${SERVICE_NAME}.service"
echo "  systemctl --user restart ${SERVICE_NAME}.service"
echo "  journalctl --user -u ${SERVICE_NAME}.service -f"
